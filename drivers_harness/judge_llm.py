"""Real LLM judge for the synonym seam — OUTSIDE the pure engine.

Builds an injectable ``judge_fn(packet) -> verdict`` for
``SynonymFoldEngine(judge_fn=...)``. Loads a LOCKED prompt file
(``judge_prompts/<name>.md``), calls OpenAI **Structured Outputs**
(``text.format.type="json_schema"``, ``strict:true``), POST-VALIDATES the
business rules the schema cannot express, FAILS SAFE to ``defer``, and caches by
``(packet + prompt_version + model_policy)``.

Binding rules: ``judge_prompts/INTEGRATION_CONTRACT.md`` (LOCKED 2026-05-29).

PURITY: ``synonym_fold.py`` never imports this; it only receives the produced
``judge_fn``. The OpenAI client + ``import openai`` are LAZY (only on a real
call) so unit tests (fake transport) need no key/network. stdlib at import time.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Callable

PROMPTS_DIR = Path(__file__).parent / "judge_prompts"

# ── model policy (tiered) — INTEGRATION_CONTRACT.md §5 ────────────────────────
DEFAULT_MODEL = "gpt-5.4-mini"        # every call
ESCALATION_MODEL = "gpt-5.4"          # "hard case" = default returned defer
# gpt-5-mini = documented alt if quality matches; gpt-5.5 / gpt-4o* excluded.
TEMPERATURE = 0.0
DECISIONS = ("promote", "no_global_rule", "defer")

_SYSTEM_RE = re.compile(
    r"<!--\s*JUDGE:SYSTEM:BEGIN\s*-->(.*?)<!--\s*JUDGE:SYSTEM:END\s*-->", re.S)
_SCHEMA_RE = re.compile(
    r"<!--\s*JUDGE:SCHEMA:BEGIN\s*-->\s*```json(.*?)```\s*<!--\s*JUDGE:SCHEMA:END\s*-->",
    re.S)


def _defer(reason: str) -> dict:
    return {"decision": "defer", "to_token": None, "reason": reason}


def _content_hash(system: str, schema: dict) -> str:
    """sha256 (first 16 hex) of the EXACT (system prompt + schema) sent to the
    model. Part of the cache key, so editing `synonym_judge.v1.md` WITHOUT
    renaming auto-invalidates cached verdicts — no silent stale replay."""
    blob = system + "\x1f" + json.dumps(schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def load_prompt(name: str) -> tuple[str, dict, str, str]:
    """Return ``(system_text, schema_dict, prompt_version, content_hash)`` from
    ``judge_prompts/<name>.md``. ``prompt_version == name`` (human label);
    ``content_hash`` makes the cache key reflect the ACTUAL prompt content, so an
    edit without a version bump cannot replay stale verdicts."""
    path = PROMPTS_DIR / f"{name}.md"
    text = path.read_text(encoding="utf-8")
    sm = _SYSTEM_RE.search(text)
    cm = _SCHEMA_RE.search(text)
    if not sm or not cm:
        raise ValueError(f"prompt {name!r}: missing JUDGE:SYSTEM or JUDGE:SCHEMA block")
    system = sm.group(1).strip()
    schema = json.loads(cm.group(1))
    return system, schema, name, _content_hash(system, schema)


# ── the REAL transport (lazy OpenAI client) — injectable for tests ───────────
_CLIENT = None


def _client():
    global _CLIENT
    if _CLIENT is None:
        from dotenv import load_dotenv
        from openai import OpenAI
        load_dotenv()
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set")
        _CLIENT = OpenAI(api_key=key)
    return _CLIENT


def openai_transport(
    system: str, user: str, schema: dict, schema_name: str, model: str,
) -> dict | None:
    """One OpenAI Structured-Outputs call. Returns the parsed JSON dict, or None
    on an empty/refusal output. Raises on network/API/JSON errors (the judge
    catches -> defer). Retries without ``temperature`` if a model rejects it."""
    client = _client()

    def _call(temp):
        kw = dict(
            model=model,
            input=[{"role": "system", "content": system},
                   {"role": "user", "content": user}],
            text={"format": {"type": "json_schema", "name": schema_name,
                             "strict": True, "schema": schema}},
        )
        if temp is not None:
            kw["temperature"] = temp
        return client.responses.create(**kw)

    try:
        resp = _call(TEMPERATURE)
    except Exception as e:                       # noqa: BLE001
        if "temperature" in str(e).lower():
            resp = _call(None)
        else:
            raise
    txt = getattr(resp, "output_text", None)
    if not txt:
        return None
    return json.loads(txt)                        # may raise -> caught upstream


# ── persistent cache — simple JSONL file under .judge_cache/ (harness-grade) ──
class FileCache:
    """Tiny persistent verdict cache: one append-only JSONL file, one
    ``{"k": key, "v": verdict}`` record per line, loaded into a dict on first
    use (last write wins on reload). Dict-like (`in` / `[]` / `[]=`). Enough for
    the harness (decide-once ACROSS runs); a shared/Neo4j backend is
    integration-phase. INTEGRATION_CONTRACT.md §7."""

    def __init__(self, path=None) -> None:
        self.path = Path(path) if path else (
            Path(__file__).parent / ".judge_cache" / "synonym_judge.jsonl")
        self._mem: dict | None = None

    def _load(self) -> dict:
        if self._mem is None:
            self._mem = {}
            if self.path.exists():
                for line in self.path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        self._mem[rec["k"]] = rec["v"]
                    except Exception:               # noqa: BLE001 — skip corrupt line
                        continue
        return self._mem

    def __contains__(self, key: str) -> bool:
        return key in self._load()

    def __getitem__(self, key: str) -> dict:
        return self._load()[key]

    def __setitem__(self, key: str, value: dict) -> None:
        self._load()[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"k": key, "v": value}, separators=(",", ":")) + "\n")

    def __len__(self) -> int:
        return len(self._load())


# ── the judge factory ────────────────────────────────────────────────────────
def make_synonym_judge_fn(
    *,
    prompt_name: str = "synonym_judge.v1",
    default_model: str = DEFAULT_MODEL,
    escalation_model: str | None = ESCALATION_MODEL,
    transport: Callable = openai_transport,
    cache: dict | None = None,
) -> Callable[[dict], dict]:
    """Build an injectable ``judge_fn(packet) -> verdict`` to the locked contract.

    - Structured Outputs via ``transport`` (default real OpenAI; inject a fake in
      unit tests).
    - POST-VALIDATE (§4): decision in enum; ``to_token`` non-null IFF promote and
      a real candidate; else coerce/defer.
    - FAIL SAFE (§6): any error/None/invalid -> ``defer`` (never guess).
    - ESCALATE (§5): if the default model returns ``defer`` (hard case), ask
      ``escalation_model`` once; its verdict is final.
    - CACHE (§7): key = sha256(canonical packet + prompt_version + model_policy);
      the FINAL (post-escalation) verdict is replayed, no second API call.
    """
    system, schema, prompt_version, content_hash = load_prompt(prompt_name)
    schema_name = "synonym_judge_verdict"
    model_policy = (f"{default_model}>[defer,promote]>{escalation_model}"
                    if escalation_model else default_model)
    if cache is None:
        cache = FileCache()      # persistent JSONL under .judge_cache/ for real runs

    def _cache_key(packet: dict) -> str:
        canon = json.dumps(packet, sort_keys=True, separators=(",", ":"))
        raw = "\x1f".join([canon, prompt_version, content_hash, model_policy])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _validate(packet: dict, verdict) -> tuple[dict, bool]:
        # Returns (verdict, is_semantic). is_semantic=False marks a FAILURE-defer
        # (malformed / invalid decision / post-validation) -> must NOT be cached.
        if not isinstance(verdict, dict):
            return _defer("non-dict verdict"), False
        decision = verdict.get("decision")
        to_token = verdict.get("to_token")
        reason = verdict.get("reason")
        reason = reason if isinstance(reason, str) else ""
        if decision not in DECISIONS:
            return _defer(f"invalid decision: {decision!r}"), False
        cand_tokens = {c.get("to_token") for c in packet.get("candidates", [])}
        if decision == "promote":
            if to_token is None or to_token not in cand_tokens:
                return _defer(f"promote to_token not a candidate: {to_token!r}"), False
            return {"decision": "promote", "to_token": to_token, "reason": reason}, True
        # semantic no_global_rule / defer (to_token coerced null) -> cacheable
        return {"decision": decision, "to_token": None, "reason": reason}, True

    def _one_call(packet: dict, model: str) -> tuple[dict, bool]:
        # Returns (verdict, is_semantic). is_semantic=False on ANY failure path
        # (exception / None / refusal / invalid / post-validation) -> a TRANSIENT
        # defer that must NOT be cached (retry next run), not a real verdict.
        try:
            user = json.dumps(packet, sort_keys=True, separators=(",", ":"))
            raw = transport(system, user, schema, schema_name, model)
            if raw is None:
                return _defer(f"empty/refusal from {model}"), False
            return _validate(packet, raw)
        except Exception as e:                    # noqa: BLE001 — fail safe
            return _defer(f"judge error from {model}: {type(e).__name__}"), False

    def judge_fn(packet: dict) -> dict:
        key = _cache_key(packet)
        if key in cache:
            return dict(cache[key])
        verdict, ok = _one_call(packet, default_model)
        cacheable = ok                                      # never cache a failure
        if escalation_model and ok and verdict["decision"] == "defer":
            # HARD CASE: cheap model semantically unsure -> stronger model decides.
            verdict, cacheable = _one_call(packet, escalation_model)
        elif escalation_model and ok and verdict["decision"] == "promote":
            # RISKY MERGE: confirm with the stronger model (promote is irreversible-ish).
            confirm, ok2 = _one_call(packet, escalation_model)
            if not ok2:
                # the CONFIRM call FAILED transiently -> defer THIS run, do NOT cache.
                verdict = _defer(f"promote unconfirmed (confirm call failed): {confirm['reason']}")
                cacheable = False
            elif (confirm["decision"] == "promote"
                    and confirm["to_token"] == verdict["to_token"]):
                verdict, cacheable = confirm, True          # both agree -> confirmed
            elif confirm["decision"] == "no_global_rule":
                verdict, cacheable = confirm, True          # stronger model: no fold
            else:
                # genuine semantic disagreement (confirm deferred / different token).
                verdict = _defer(
                    f"promote unconfirmed by {escalation_model}: "
                    f"{confirm['decision']}/{confirm.get('to_token')}")
                cacheable = True                            # a real no-consensus verdict
        # Persist ONLY genuine semantic verdicts. A failure-path defer (outage /
        # refusal / invalid / post-validation / failed confirm) returns for THIS
        # run and retries next — a transient outage never becomes a permanent verdict.
        if cacheable:
            cache[key] = dict(verdict)
        return dict(verdict)

    judge_fn.model_policy = model_policy           # type: ignore[attr-defined]
    judge_fn.prompt_version = prompt_version       # type: ignore[attr-defined]
    return judge_fn
