"""Vocabulary seed banks + VocabSnapshot assembly  (PROD-CORE, pure).

Transcribes DriverOntology_Implementation.md sections F.1-F.9 (RULES ONLY) plus
the section G thresholds. Mirrors the production ``load_vocab_snapshot`` MINUS the
Neo4j PIT read (no Neo4j at all — offline harness per Harness_BuilderPrompt.md
sections 0a / 8). NO LLM, NO network, stdlib only.

Sources cited per declaration:
  - F.1  THEMES/OBJECTS/CUSTOMERS/GEOGRAPHIES/INSTITUTIONS/METRICS/SHORTCUTS_VOCAB
  - F.2  SYNONYM_MAP (single-token) + MULTI_TOKEN_SUBS
  - F.3  PLURAL_MAP
  - F.4  ACRONYM_MAP
  - F.5  STATES_VOCAB (by class) -> STATES (union) + STATE_CLASSES
  - F.6  COMPOUND_METRICS + CANONICAL_BASE_LABELS
  - F.7  BANNED_CONTENT (static category sets + period/numeric/verb_form predicates)
  - F.8  STOPWORDS
  - F.9  ALLOWED_VERBAL_FORMS
  - G    MAX_EFFECTIVE_SLOTS / STATES_MIN / STATES_MAX / EVIDENCE_MIN_PER_TAG

Authorised seed additions beyond verbatim F.1-F.9 (Harness_BuilderPrompt.md section 4):
  - ``forward_guidance`` appended to SHORTCUTS_VOCAB (seed-completeness, doubt #11 / F13).
  - ``BANNED_TICKERS`` static seed (F.7 tickers are DB-sourced; offline harness needs a
    static representative seed so ``aapl_iphone_sales -> REJECT ticker`` works).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# ─────────────────────────────────────────────────────────────────────────────
# §F.1  Slot vocab seeds + SHORTCUTS_VOCAB  (transcribed verbatim)
# ─────────────────────────────────────────────────────────────────────────────

THEMES = {
    "ai", "ev", "ip", "semiconductor", "cloud", "autonomous",
    "cybersecurity", "biotech",
}

OBJECTS = {
    "iphone", "mac", "ipad", "vision_pro", "datacenter", "gpu", "cpu",
    "cloud_service", "advertising",
}

CUSTOMERS = {
    "hyperscaler", "enterprise", "consumer", "government", "smb",
}

GEOGRAPHIES = {
    "china", "us", "japan", "india", "eu", "emea", "apac", "latam",
    "mexico", "canada",
}

INSTITUTIONS = {
    "fed", "ecb", "boj", "opec", "fda", "sec", "doj", "ftc",
}

METRICS = {
    "revenue", "sales", "units", "deliveries", "capex", "opex", "supply",
    "price", "rate", "demand", "inventory", "backlog", "bookings",
    "subscribers", "arpu", "churn",
}

# Authorised seed addition (NOT verbatim F.1). ``eps`` is required as a bare
# valid metric driver by Harness_BuilderPrompt.md section 4 (COLD_START_SEED_DRIVERS:
# "revenue, sales, eps ... Every name here MUST canonicalize to ITSELF") AND by the
# section-5 self-check ("round-trip to ITSELF: ... eps") AND by section-6 bucket E
# ("bare valid metric ... ACCEPTS"). But F.1 METRICS verbatim does NOT list ``eps`` —
# it only appears in F.4 ACRONYM_MAP (eps -> eps, "short form wins") and F.6
# CANONICAL_BASE_LABELS (EPS). Without a metric-slot membership ``eps`` classifies
# UNKNOWN -> slot_anchor_unavailable, contradicting the brief. F.1 METRICS is kept
# verbatim; ``eps`` is added to the metric SLOT VOCAB only (same precedent as
# ``forward_guidance`` in SHORTCUTS_VOCAB). See seed_additions in the return report.
# SURFACED: F.1-vs-brief tension on ``eps``.
METRIC_SLOT_SEED_ADDITIONS = {"eps"}

# F.1 SHORTCUTS_VOCAB verbatim, PLUS authorised seed addition ``forward_guidance``
# (Harness_BuilderPrompt.md section 4 vocab_seed seed-completeness / doubt #11 / F13).
SHORTCUTS_VOCAB = {
    "yield_curve", "fed_rate", "ecb_rate", "boj_rate", "usd_index", "vix",
    "credit_spread", "oil_price", "oil_supply", "opec_supply", "fda_approval",
    "sec_enforcement", "treasury_yield", "ig_spread", "junk_spread",
    "inflation_rate", "tariffs", "sanctions", "export_restriction",
    "trade_policy", "share_buyback",
    # ── authorised seed addition (NOT verbatim F.1) ──
    "forward_guidance",
}


# ─────────────────────────────────────────────────────────────────────────────
# §F.2  SYNONYM_MAP  (single-token + multi-token)  (transcribed verbatim)
# ─────────────────────────────────────────────────────────────────────────────

# Single-token (applied at canonicalize step 5).
SYNONYM_MAP = {
    "topline": "revenue",
    "turnover": "revenue",
    "margin": "gross_margin",   # only when not paired with another metric token
}

# Multi-token (substring at canonicalize step 2, longest-match first).
MULTI_TOKEN_SUBS = {
    "data_center": "datacenter",
    "gross_profit": "gross_margin",
}


# ─────────────────────────────────────────────────────────────────────────────
# §F.3  PLURAL_MAP  (transcribed verbatim, both directions)
# ─────────────────────────────────────────────────────────────────────────────

PLURAL_MAP = {
    # metric/event singular → plural canonical
    "sale": "sales",
    "tariff": "tariffs",
    "order": "orders",
    "ruling": "rulings",
    "approval": "approvals",
    "delivery": "deliveries",
    "unit": "units",
    "booking": "bookings",
    # object/customer plural → singular canonical
    "iphones": "iphone",
    "macs": "mac",
    "ipads": "ipad",
    "vision_pros": "vision_pro",
    "datacenters": "datacenter",
    "hyperscalers": "hyperscaler",
    "gpus": "gpu",
    "cpus": "cpu",
}


# ─────────────────────────────────────────────────────────────────────────────
# §F.4  ACRONYM_MAP  (transcribed verbatim)
# ─────────────────────────────────────────────────────────────────────────────

ACRONYM_MAP = {
    "gm": "gross_margin",
    "om": "operating_margin",
    "nm": "net_margin",
    "fcf": "free_cash_flow",
    "ocf": "operating_cash_flow",
    "eps": "eps",       # short form wins
    "capex": "capex",
    "opex": "opex",
    "arpu": "arpu",
}


# ─────────────────────────────────────────────────────────────────────────────
# §F.5  STATES_VOCAB  (by class)  (transcribed verbatim)
# ─────────────────────────────────────────────────────────────────────────────

STATE_CLASSES = {
    "financial_outcome": {"beat", "missed", "inline", "raised", "lowered",
                          "reaffirmed", "withdrawn"},
    "quantity_move": {"cut", "expanded", "contracted", "exhausted", "built",
                      "cleared", "accumulated"},
    "policy_action": {"imposed", "eased", "lifted", "restricted", "approved",
                      "denied", "lapsed"},
    "rate_curve": {"steepened", "flattened", "inverted", "normalized"},
    "event_lifecycle": {"announced", "initiated", "completed", "cancelled",
                        "delayed"},
    "trend_motion": {"accelerated", "decelerated", "stable", "declined",
                     "compressed"},
    "sentiment_motion": {"improved", "deteriorated"},
}

# Union of all classes (for V6 + canonicalize step 7 state check).
STATES = set()
for _cls_tokens in STATE_CLASSES.values():
    STATES |= _cls_tokens


# ─────────────────────────────────────────────────────────────────────────────
# §F.6  COMPOUND_METRICS + CANONICAL_BASE_LABELS  (transcribed verbatim)
# ─────────────────────────────────────────────────────────────────────────────

COMPOUND_METRICS = {
    "gross_margin", "operating_margin", "net_margin",
    "free_cash_flow", "operating_cash_flow",
    "cost_of_revenue", "cost_of_goods_sold",
    "effective_tax_rate",
    "capital_expenditure",
    # Legit multi-token METRICS that contain a bare-banned direction word (short/long,
    # §F.7 `direction`). Seeded here (mirror §F.6, owner-approved 2026-05-29) so §C step-3.5
    # freeze keeps each WHOLE → the bare-`short`/`long` ban can't break them. Pattern =
    # "strict ban on loose words, explicit allow for real terms."
    "short_interest", "long_term_debt", "short_term_debt",
}

CANONICAL_BASE_LABELS = {
    "Sales", "Revenue", "GrossMargin", "OperatingMargin", "NetMargin",
    "EPS", "CapEx", "OpEx", "FreeCashFlow", "OperatingCashFlow",
    "CostOfRevenue", "EffectiveTaxRate",
}


# ─────────────────────────────────────────────────────────────────────────────
# §F.7  BANNED_CONTENT  (static category sets + pattern predicates)
# ─────────────────────────────────────────────────────────────────────────────

# Static company legal names (F.7 identity examples, slugified + representative).
_BANNED_COMPANY = {
    "apple", "tesla", "samsung", "nvidia", "microsoft", "google",
    "amazon", "meta", "alphabet", "intel", "qualcomm", "broadcom",
}

# Static well-known executive/political person names (F.7 identity examples).
_BANNED_PERSON = {
    "elon_musk", "tim_cook", "jensen_huang", "satya_nadella",
    "jerome_powell", "warren_buffett",
}

_BANNED_SOURCE_TYPE = {
    "8k", "10k", "10q", "transcript", "news", "report", "filing",
    "ex_99", "item",
}

_BANNED_PROVIDER = {
    "fiscalai", "bloomberg", "refinitiv", "factset", "benzinga", "polygon",
}

_BANNED_XBRL_PREFIX = {
    "us_gaap", "ifrs", "dei",
}

_BANNED_METAPHOR = {
    "headwind", "tailwind", "kitchen_sink", "sell_the_news", "ankle_biter",
}

_BANNED_SENTIMENT = {
    "strong", "weak", "bullish", "bearish", "positive", "negative",
    "upside", "downside", "rising", "falling", "concerning", "exciting",
    "disappointing",
}

_BANNED_EFFECT = {
    "selloff", "rally", "reaction", "disappointment", "surprise_factor",
}

# §F.7/R7 names "motion or change nouns" as a banned category but the spec text
# (§F.7 token-level block) never enumerated a token set for it — it was UNSEEDED
# (per the line-21 conformance rule, an empty category is a config error). K26
# fix (owner-approved seed addition, Pass-1 corrective round 2026-05-29): seed it
# with judgment-noun movement words that describe a PRICE/QUANTITY MOVEMENT, not a
# reusable causal driver (e.g. ``revenue_collapse`` smuggles the move into the
# name; the real driver is ``revenue`` + the move is the OUTCOME). ``rally`` is
# omitted here because it is ALREADY banned under ``effect`` (a token in exactly
# one banned category keeps banned_category() deterministic); it stays banned.
# Verified: NONE of these collide with a real THEMES/OBJECTS/CUSTOMERS/GEOGRAPHIES/
# INSTITUTIONS/METRICS/COMPOUND_METRICS/STATES/SHORTCUTS/ALLOWED_VERBAL_FORMS entry.
# Surfaced in README authorized-additions list.
_BANNED_MOTION_CHANGE = {
    "collapse", "surge", "rebound", "plunge", "recovery", "slump",
    "spike", "drop", "jump", "decline",
}

# §F.7 direction/polarity (K8 seed, owner-approved 2026-05-29 v11-3) — trade
# direction (long/short) belongs in the `direction` FIELD; which-way (up/down)
# describes movement, not a reusable cause; NEVER a NAME token. `gpu_short_us_revenue`
# MUST reject. NOTE: banning long/short as NAME tokens does NOT conflict with V9's
# direction-FIELD enum {long, short} — different context (a name token vs a companion
# field value). V9 stays as-is. (`rising`/`falling` are already under sentiment.)
# Verified: none of {long, short, up, down} collide with a real THEMES/OBJECTS/
# CUSTOMERS/GEOGRAPHIES/INSTITUTIONS/METRICS/COMPOUND_METRICS/STATES/SHORTCUTS/
# ALLOWED_VERBAL_FORMS entry.
_BANNED_DIRECTION = {
    "long", "short", "up", "down",
}

# §F.7 magnitude_word (owner-approved 2026-05-29 v11-3) — qualitative magnitudes
# describe SIZE, not a reusable cause; banned from a NAME. `gpu_large_us_revenue`
# MUST reject. Verified: none of these collide with a real vocab entry.
_BANNED_MAGNITUDE_WORD = {
    "large", "small", "big", "huge", "tiny", "minor", "major", "modest",
    "slight", "significant", "substantial",
}

_BANNED_CATEGORY = {
    "macro", "sector", "sentiment", "positioning", "theme_only",
}

_BANNED_VAGUE_DESCRIPTOR = {
    "update", "performance", "quality", "situation", "environment",
    "outlook", "story", "narrative", "momentum", "dynamics", "picture",
}

# Period tokens (the non-pattern part of F.7 period).
_BANNED_PERIOD_TOKENS = {"quarter", "year", "fiscal"}

# Numeric unit-suffix tokens (the non-^\d part of F.7 numeric).
_BANNED_UNIT_SUFFIX = {"pct", "bps", "x", "percent", "basis_points"}

# BANNED_TICKERS — static representative seed (authorised seed addition,
# Harness_BuilderPrompt.md section 4). F.7 sources tickers from Neo4j
# Company.ticker (DB-only); the offline harness needs a static seed so
# ``aapl_iphone_sales -> REJECT ticker`` works. Category = identity_ticker.
BANNED_TICKERS = {
    "aapl", "nvda", "tsla", "msft", "googl", "amzn", "meta",
    "intc", "qcom", "avgo", "amd",
}

# BANNED_CATEGORIES — structured map category -> static token set. Used by
# validators + ``banned_category``. Note: tickers handled separately via
# BANNED_TICKERS; period/numeric/verb_form are PATTERN bans (see banned_category).
BANNED_CATEGORIES = {
    "identity_ticker": set(BANNED_TICKERS),
    "identity_company": set(_BANNED_COMPANY),
    "identity_person": set(_BANNED_PERSON),
    "source_type": set(_BANNED_SOURCE_TYPE),
    "provider": set(_BANNED_PROVIDER),
    "xbrl_prefix": set(_BANNED_XBRL_PREFIX),
    "metaphor": set(_BANNED_METAPHOR),
    "sentiment": set(_BANNED_SENTIMENT),
    "effect": set(_BANNED_EFFECT),
    "motion_change": set(_BANNED_MOTION_CHANGE),   # §F.7/R7 motion-or-change nouns (K26 seed)
    "direction": set(_BANNED_DIRECTION),           # §F.7 direction/polarity (v11-3 seed)
    "magnitude_word": set(_BANNED_MAGNITUDE_WORD), # §F.7 qualitative magnitudes (v11-3 seed)
    "category": set(_BANNED_CATEGORY),
    "vague_descriptor": set(_BANNED_VAGUE_DESCRIPTOR),
    "period": set(_BANNED_PERIOD_TOKENS),
    "numeric": set(_BANNED_UNIT_SUFFIX),
}

# Flat BANNED set = union of ALL static-token categories (+ tickers).
# This is what VocabSnapshot.banned carries (canonicalize step 7 static lookup).
BANNED = set()
for _cat_tokens in BANNED_CATEGORIES.values():
    BANNED |= _cat_tokens


# ─────────────────────────────────────────────────────────────────────────────
# §F.8  STOPWORDS  (transcribed verbatim)
# ─────────────────────────────────────────────────────────────────────────────

STOPWORDS = {
    "the", "of", "in", "and", "or", "on", "at", "for", "with", "to",
    "a", "an", "by", "from", "into",
}


# ─────────────────────────────────────────────────────────────────────────────
# §F.9  ALLOWED_VERBAL_FORMS  (transcribed verbatim, post-2026-05-29 F5/F9 fix)
# ─────────────────────────────────────────────────────────────────────────────

# ``restricted`` + ``accumulated`` REMOVED per the 2026-05-29 F5/F9 fix (both are
# §F.5 STATES → belong in driver_state, banned from names by canonicalize step 7).
ALLOWED_VERBAL_FORMS = {
    "consolidated", "diluted", "weighted", "deferred", "accrued",
    "retained", "underwriting", "lending",
}


# ─────────────────────────────────────────────────────────────────────────────
# §G  Numerical thresholds  (transcribed verbatim)
# ─────────────────────────────────────────────────────────────────────────────

MAX_EFFECTIVE_SLOTS = 4
STATES_MIN = 2
STATES_MAX = 8
EVIDENCE_MIN_PER_TAG = 1


# ─────────────────────────────────────────────────────────────────────────────
# §F.7 pattern predicates (compiled once)
# ─────────────────────────────────────────────────────────────────────────────

# period pattern: ^(q\d|fy\d{2,4}|h\d|\d{4})$
_PERIOD_RE = re.compile(r"^(q\d|fy\d{2,4}|h\d|\d{4})$")
# numeric pattern: ^\d  (token begins with a digit)
_NUMERIC_RE = re.compile(r"^\d")
# verb_form pattern: ^[a-z]+(ed|ing)$
_VERB_FORM_RE = re.compile(r"^[a-z]+(ed|ing)$")


# ─────────────────────────────────────────────────────────────────────────────
# VocabSnapshot — frozen snapshot consumed by canonicalize + validators
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class VocabSnapshot:
    """Immutable snapshot of the vocab banks canonicalize/validators read.

    Field NAMES are load-bearing — canonicalize reads them by name. Mirrors the
    production VocabSnapshot (Implementation §C) plus the extra carry fields the
    harness validators / banned predicate need.
    """
    # ── canonicalize reads these ──
    synonym_map: dict          # §F.2 single-token
    plural_map: dict           # §F.3
    acronym_map: dict          # §F.4
    shortcuts: frozenset       # §F.1 SHORTCUTS_VOCAB (+ forward_guidance)
    slot_vocabs: dict          # 6 SLOT_ORDER keys; metric = METRICS ∪ COMPOUND_METRICS
    banned: frozenset          # §F.7 flat static union (step-7 lookup)
    stopwords: frozenset       # §F.8
    states: frozenset          # §F.5 union
    multi_token_subs: dict     # §F.2 multi-token
    compound_metrics: frozenset  # §F.6 COMPOUND_METRICS
    # v11-2 (2026-05-29) — DERIVED at build time: every MULTI-token known atom
    # (contains "_") across shortcuts §F.1 ∪ compound_metrics §F.6 ∪ slot_vocabs
    # §F.1 ∪ banned §F.7. §C step 4.5 freeze_known_atoms freezes these so a known
    # multi-token OBJECT (vision_pro / cloud_service) and a multi-token BANNED
    # phrase (us_gaap / person names / basis_points) survive the tokenize-split
    # intact. SINGLE-token entries are EXCLUDED by construction — they need no
    # freezing, and excluding them guarantees no single-token fold is suppressed.
    frozen_atoms: frozenset    # v11-2 derived multi-token atom set
    # ── validators / banned predicate also need these ──
    banned_categories: dict    # category -> frozenset (static sets)
    banned_tickers: frozenset  # §F.7 ticker seed
    allowed_verbal_forms: frozenset  # §F.9
    canonical_base_labels: frozenset  # §F.6 (for V5)
    state_classes: dict        # class -> frozenset (for V6)


def banned_category(token: str, vocab: "VocabSnapshot") -> str | None:
    """Return the §F.7 ban category for ``token`` or ``None`` if not banned.

    Faithful §F.7 implementation (the brief's step-7 STEP 7 BANNED requirement):
    the canonicalize pseudocode ``t in vocab.banned`` is a simplification — the
    real §F.7 also includes PATTERN bans (period / numeric / verb_form).

    A token is banned if (checked in this order, returning the category):
      1. identity_ticker  — token in BANNED_TICKERS
      2. any static category set in banned_categories (company/person/source_type/
         provider/xbrl_prefix/metaphor/sentiment/effect/category/vague_descriptor/
         period-tokens/numeric-unit-suffixes)
      3. period pattern   ^(q\\d|fy\\d{2,4}|h\\d|\\d{4})$
      4. numeric pattern  ^\\d  (begins with a digit)
      5. verb_form        ^[a-z]+(ed|ing)$  AND token NOT in the allowlist union
         OBJECTS ∪ METRICS ∪ COMPOUND_METRICS ∪ GEOGRAPHIES ∪ INSTITUTIONS ∪
         THEMES ∪ CUSTOMERS ∪ ALLOWED_VERBAL_FORMS ∪ STATES.

    # TODO(harden-in-test): the verb_form allowlist DELIBERATELY includes STATES
    # so that a state verb (lowered/accelerated/cut) is NOT classified banned here
    # and instead falls through to the SEPARATE states check in canonicalize step 7
    # -> REJECTION_STATE_IN_NAME. This is the brief's CRITICAL verb_form-excludes-
    # states decision; revisit if a real state token is wrongly let through.
    """
    # 1. ticker
    if token in vocab.banned_tickers:
        return "identity_ticker"

    # 2. static category sets (deterministic order over a sorted category list)
    for category in sorted(vocab.banned_categories):
        if token in vocab.banned_categories[category]:
            return category

    # 3. period pattern
    if _PERIOD_RE.match(token):
        return "period"

    # 4. numeric pattern
    if _NUMERIC_RE.match(token):
        return "numeric"

    # 5. verb_form pattern with allowlist (STATES included — see docstring TODO)
    if _VERB_FORM_RE.match(token):
        allow = (OBJECTS | METRICS | COMPOUND_METRICS | GEOGRAPHIES
                 | INSTITUTIONS | THEMES | CUSTOMERS | ALLOWED_VERBAL_FORMS
                 | STATES)
        if token not in allow:
            return "verb_form"

    return None


def build_vocab_snapshot(promoted_synonyms: dict | None = None) -> VocabSnapshot:
    """Assemble the frozen VocabSnapshot from the static seeds.

    Mirrors prod ``load_vocab_snapshot`` MINUS the Neo4j PIT read (no Neo4j at
    all in the harness). slot_vocabs are keyed by the 6 SLOT_ORDER names;
    ``slot_vocabs['metric'] = METRICS ∪ COMPOUND_METRICS`` per the §D BNF.

    Pass-2 wiring point (Harness_BuilderPrompt.md §11B "the one wiring point";
    DriverOntology_Implementation.md §C ``load_vocab_snapshot``):
    ``promoted_synonyms`` is the OPTIONAL, BACKWARD-COMPATIBLE seam where promoted
    single-token synonyms arrive. In production §C this dict is the PIT-filtered
    promoted ``:EquivalenceToken{kind:synonym}`` rows read from Neo4j; in the
    offline harness it is ``SynonymFoldEngine.promoted_synonyms()``. Either way it
    merges into ``synonym_map`` EXACTLY as prod merges
    ``merge(seed.synonym, {e.from_token: e.to_token for e in promoted_eq if
    e.kind == 'synonym'})`` (§C:265): ``synonym_map = {**SYNONYM_MAP,
    **promoted_synonyms}`` so promoted entries ADD TO / TAKE PRECEDENCE OVER the
    static §F.2 seed. ``canonicalize`` step 5 then folds them automatically on the
    next run.

    BACKWARD COMPATIBILITY: ``promoted_synonyms`` defaults to ``None`` and
    ``build_vocab_snapshot()`` with NO argument behaves EXACTLY as before — the
    ``None`` case produces ``dict(SYNONYM_MAP)``, byte-identical to the pre-Pass-2
    behavior, so every existing Pass-1 call is unchanged.

    PURITY: this module does NOT import ``synonym_fold`` — the promoted dict is
    PASSED IN (the prod seam where Neo4j rows arrive), keeping ``vocab_seed``
    PROD-CORE pure (Harness_BuilderPrompt.md §9; verified by
    tests/test_prod_core_purity.py).
    """
    slot_vocabs = {
        "theme": frozenset(THEMES),
        "object": frozenset(OBJECTS),
        "customer": frozenset(CUSTOMERS),
        "geography": frozenset(GEOGRAPHIES),
        "institution": frozenset(INSTITUTIONS),
        # METRICS ∪ COMPOUND_METRICS (§D BNF) ∪ the eps seed-addition (see
        # METRIC_SLOT_SEED_ADDITIONS — F.1-vs-brief tension on ``eps``).
        "metric": frozenset(METRICS | COMPOUND_METRICS | METRIC_SLOT_SEED_ADDITIONS),
    }
    # v11-2 (2026-05-29) — derive frozen_atoms ONCE: every "_"-containing (MULTI-
    # token) entry across shortcuts §F.1 ∪ compound_metrics §F.6 ∪ ALL slot_vocabs
    # values §F.1 ∪ the flat banned set §F.7. Single-token entries are EXCLUDED by
    # the ``"_" in e`` guard (they need no freezing — see VocabSnapshot.frozen_atoms).
    # §C step 4.5 freeze_known_atoms uses this so multi-token OBJECTS (vision_pro,
    # cloud_service) classify whole and multi-token BANNED phrases (us_gaap,
    # elon_musk/tim_cook, basis_points) are caught by the per-token step-7 ban.
    frozen_atoms = set()
    frozen_atoms |= {e for e in SHORTCUTS_VOCAB if "_" in e}
    frozen_atoms |= {e for e in COMPOUND_METRICS if "_" in e}
    for _slot_set in slot_vocabs.values():
        frozen_atoms |= {e for e in _slot_set if "_" in e}
    frozen_atoms |= {e for e in BANNED if "_" in e}
    # §11B wiring: merge promoted synonyms into the §F.2 static seed. The
    # ``or {}`` keeps the no-arg path byte-identical to ``dict(SYNONYM_MAP)``;
    # promoted entries take precedence over (override) the seed on key collision,
    # mirroring prod ``merge(seed.synonym, {promoted rows})`` (§C:265).
    synonym_map = {**SYNONYM_MAP, **(promoted_synonyms or {})}
    return VocabSnapshot(
        synonym_map=synonym_map,
        plural_map=dict(PLURAL_MAP),
        acronym_map=dict(ACRONYM_MAP),
        shortcuts=frozenset(SHORTCUTS_VOCAB),
        slot_vocabs=slot_vocabs,
        banned=frozenset(BANNED),
        stopwords=frozenset(STOPWORDS),
        states=frozenset(STATES),
        multi_token_subs=dict(MULTI_TOKEN_SUBS),
        compound_metrics=frozenset(COMPOUND_METRICS),
        frozen_atoms=frozenset(frozen_atoms),
        banned_categories={k: frozenset(v) for k, v in BANNED_CATEGORIES.items()},
        banned_tickers=frozenset(BANNED_TICKERS),
        allowed_verbal_forms=frozenset(ALLOWED_VERBAL_FORMS),
        canonical_base_labels=frozenset(CANONICAL_BASE_LABELS),
        state_classes={k: frozenset(v) for k, v in STATE_CLASSES.items()},
    )


# ─────────────────────────────────────────────────────────────────────────────
# New-token gate helper (CON-2)  —  KNOWN set = §F.1 slot vocabs ∪ §F.6 compounds
# ─────────────────────────────────────────────────────────────────────────────

def is_known_token(token: str, vocab: "VocabSnapshot") -> bool:
    """Return True if ``token`` is a KNOWN slot token for the new-token gate.

    CON-2 (Harness_BuilderPrompt.md section 4): KNOWN = §F.1 slot vocabs UNION
    §F.6 COMPOUND_METRICS — NOT CANONICAL_BASE_LABELS (those are capitalized
    base-label values for V5, e.g. ``Sales``, not lowercase name tokens). The
    metric slot vocab already carries METRICS ∪ COMPOUND_METRICS, so iterating
    slot_vocabs covers compounds too; the explicit union below is belt-and-braces.

    # TODO(harden-in-test): the new-token gate's full §D(c) positional slot
    # inference is implemented in canonicalize via resolve_unknown_slots; this
    # helper only answers membership for the V14 / B-R11 known-token range.
    """
    for slot_set in vocab.slot_vocabs.values():
        if token in slot_set:
            return True
    return token in vocab.compound_metrics


# ─────────────────────────────────────────────────────────────────────────────
# COLD_START_SEED_DRIVERS — Tier-1 TIMELESS, VALID driver names ONLY
# ─────────────────────────────────────────────────────────────────────────────
#
# PROD-CORE: copies to production UNCHANGED. Every name here MUST canonicalize to
# ITSELF. Per the PIT policy: NO modern/era-bound names (iphone_china_sales,
# gpu_*) — a leak here is a real production PIT bug. NO bare china/fed (they'd
# reject no_metric). Row schema:
#   {name, aliases[], allowed_states[], segment, definition, base_label?, is_shortcut?}

COLD_START_SEED_DRIVERS = [
    {
        "name": "oil_price",
        # crude_price / brent_price are SYNONYMS (different words, same meaning), NOT
        # aliases: an alias must canonicalize TO the parent (V1), but these reject
        # slot_ambiguous. Synonyms are the Pass-2 synonym-learner's job, never seeded.
        # (owner decision 2026-05-29; guarded by test_every_seeded_alias_canonicalizes_to_its_parent)
        "aliases": [],
        "allowed_states": ["accelerated", "decelerated", "stable", "declined"],
        "segment": "Total",
        "definition": "The benchmark market price of crude oil.",
        "is_shortcut": True,
    },
    {
        "name": "oil_supply",
        "aliases": [],
        "allowed_states": ["cut", "expanded", "contracted", "exhausted"],
        "segment": "Total",
        "definition": "The available global supply of crude oil.",
        "is_shortcut": True,
    },
    {
        "name": "fed_rate",
        "aliases": [],
        "allowed_states": ["raised", "lowered", "reaffirmed", "stable"],
        "segment": "Total",
        "definition": "The U.S. Federal Reserve policy interest rate.",
        "is_shortcut": True,
    },
    {
        "name": "yield_curve",
        "aliases": [],
        "allowed_states": ["steepened", "flattened", "inverted", "normalized"],
        "segment": "Total",
        "definition": "The term structure of government bond yields.",
        "is_shortcut": True,
    },
    {
        "name": "fda_approval",
        "aliases": [],
        "allowed_states": ["approved", "denied", "delayed", "announced"],
        "segment": "Total",
        "definition": "A regulatory approval decision by the U.S. FDA.",
        "is_shortcut": True,
    },
    {
        "name": "gross_margin",
        "aliases": [],
        "allowed_states": ["expanded", "contracted", "compressed", "stable"],
        "segment": "Total",
        "definition": "Revenue less cost of goods sold, as a share of revenue.",
        "base_label": "GrossMargin",
    },
    {
        "name": "revenue",
        "aliases": [],
        "allowed_states": ["beat", "missed", "accelerated", "decelerated"],
        "segment": "Total",
        "definition": "Total top-line sales recognized in the period.",
        "base_label": "Revenue",
    },
    {
        "name": "sales",
        "aliases": [],
        "allowed_states": ["accelerated", "decelerated", "stable", "declined"],
        "segment": "Total",
        "definition": "Units or value of product sold in the period.",
        "base_label": "Sales",
    },
    {
        "name": "eps",
        "aliases": [],
        "allowed_states": ["beat", "missed", "raised", "lowered"],
        "segment": "Total",
        "definition": "Earnings per share for the reporting period.",
        "base_label": "EPS",
    },
    {
        "name": "forward_guidance",
        "aliases": [],
        "allowed_states": ["raised", "lowered", "reaffirmed", "withdrawn"],
        "segment": "Total",
        "definition": "Management's forward-looking outlook for future periods.",
        "is_shortcut": True,
    },
]
