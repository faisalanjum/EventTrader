"""Locate: verbatim span extraction, the ``"locate"`` question type of ``Decider.decide``.

The first Locate request loads this adapter (span head plus an unmerged LoRA) from ``locate-span/``:

    >>> decider = Decider.from_pretrained("perplexity-ai/<repo>", device="cuda")
    >>> decider.decide({"state": "...", "questions": {"people": {"type": "locate", "instructions": "Person names"}}})
    {"answers": {"people": {"type": "locate", "spans": [{"start": 0, "end": 5, "text": "...", "score": 0.9}]}},
     "usage": {...}}

A request may mix Locate and decision questions. Locate questions run in their own forward pass with the adapter
enabled; it is disabled otherwise, so decision answers and ``logits`` are exactly those of a plain Decider.

Prompt, as trained (``joint-v4-locate``): the Decider's chunked protocol-v4 context (system prompt, ``"State:\\n"``
and the state, then ``<|fim_middle|>``), then one chunk per question, ``"Question:\\nLocate verbatim spans:\\n"``
plus its instructions and the ``<|locate|>`` marker. The questions are isolated, as in ``mode="isolated"``. The span
head reads the hidden states of the state tokens and of each marker. The state attends to all questions, so
answers can depend on the other questions. Questions are split only when they exceed the Decider
``max_length`` together; every group retains the full state. An oversized singleton raises ``LengthError``.

Arithmetic, as evaluated: BF16 autocast on CUDA; the adapter and head tensors are FP32.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from safetensors.torch import load_file
from torch import nn

from .model import Decider, question_layout
from .protocol import Encoded, Encoder, LengthError, RequestError, left_pad

LOCATE_MARKER = "<|locate|>"
FORMAT = "pplx-decider-locate-span-v1"
PROMPT = "Locate verbatim spans:\n"
MAX_QUESTIONS = 128


class LocateLengthError(LengthError):
    """The full state and question group exceed the Decider's ``max_length``."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class LoRALinear(nn.Module):
    """``base(x) + B(A(x)) * alpha / rank``, with the update only while ``enabled`` (off by default)."""

    def __init__(self, base: nn.Linear, rank: int, alpha: float) -> None:
        super().__init__()
        self.base = base
        self.scale = alpha / rank
        device = base.weight.device
        self.lora_a = nn.Parameter(torch.zeros(rank, base.in_features, device=device), requires_grad=False)
        self.lora_b = nn.Parameter(torch.zeros(base.out_features, rank, device=device), requires_grad=False)
        self.enabled = False

    @property
    def weight(self) -> torch.Tensor:
        return self.base.weight

    @property
    def bias(self) -> torch.Tensor | None:
        return self.base.bias

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        result = self.base(inputs)
        if self.enabled:
            # Autocast chooses the compute dtype, as in training; otherwise the update is FP32.
            values = inputs if torch.is_autocast_enabled(inputs.device.type) else inputs.float()
            update = F.linear(F.linear(values, self.lora_a), self.lora_b) * self.scale
            result = result + update.to(result.dtype)
        return result


class MarkerEmbedding(nn.Embedding):
    """The base input embedding; while ``enabled``, ``<|locate|>`` reads its own trained FP32 vector."""

    def __init__(self, base: nn.Embedding, token_id: int) -> None:
        super().__init__(
            base.num_embeddings,
            base.embedding_dim,
            padding_idx=base.padding_idx,
            max_norm=base.max_norm,
            norm_type=base.norm_type,
            scale_grad_by_freq=base.scale_grad_by_freq,
            sparse=base.sparse,
            _weight=base.weight.detach(),
            _freeze=True,
        )
        if not 0 <= token_id < base.num_embeddings:
            raise ValueError("The Locate marker has no embedding row")
        self.token_id = token_id
        self.locate = nn.Parameter(torch.zeros(base.embedding_dim, device=base.weight.device), requires_grad=False)
        self.enabled = False

    def forward(self, input: torch.Tensor) -> torch.Tensor:
        values = super().forward(input)
        if not self.enabled:
            return values
        return torch.where((input == self.token_id)[..., None], self.locate.to(values.dtype), values)


class SpanHead(nn.Module):
    """Query-conditioned start/end scores and a top-k span grid with a per-question threshold (recipe v3)."""

    def __init__(self, hidden: int, width: int, max_span: int) -> None:
        super().__init__()
        self.max_span = max_span
        self.ts = nn.Linear(hidden, width)
        self.te = nn.Linear(hidden, width)
        self.qs = nn.Linear(hidden, width)
        self.qe = nn.Linear(hidden, width)
        self.qp = nn.Linear(hidden, width)
        self.width_bias = nn.Embedding(32, 1)
        self.thresholds = nn.Linear(hidden, 3)
        self.start_bias = nn.Parameter(torch.tensor(0.0))
        self.end_bias = nn.Parameter(torch.tensor(0.0))
        self.scale = math.sqrt(width)

    def project(self, document: torch.Tensor, labels: torch.Tensor) -> tuple[torch.Tensor, ...]:
        if not torch.is_autocast_enabled(document.device.type):
            document, labels = document.float(), labels.float()
        ts, te = self.ts(document), self.te(document)
        qs, qe, qp = self.qs(labels), self.qe(labels), self.qp(labels)
        start = qs @ ts.T / self.scale + self.start_bias
        end = qe @ te.T / self.scale + self.end_bias
        return ts, te, qp, start, end, self.thresholds(labels)

    def predict(
        self, document: torch.Tensor, labels: torch.Tensor, threshold: float, proposals: int
    ) -> list[list[tuple[int, int, float]]]:
        """Inclusive token spans whose probability reaches ``threshold``, per label."""
        ts, te, qp, start, finish, thresholds = self.project(document, labels)
        k = min(proposals, start.shape[1])
        result = []
        for i in range(len(labels)):
            start_values, si = start[i : i + 1].topk(k, dim=-1)
            end_values, ei = finish[i : i + 1].topk(k, dim=-1)
            scores = (ts[si] * qp[i : i + 1].tanh()[:, None, :]) @ te[ei].transpose(-1, -2) / self.scale
            widths = ei[:, None, :] - si[:, :, None] + 1
            buckets = torch.floor(torch.log2(widths.clamp_min(1).float())).long().clamp(0, 31)
            scores = scores + start_values[:, :, None] + end_values[:, None, :] + self.width_bias(buckets).squeeze(-1)
            scores = scores.masked_fill((widths <= 0) | (widths > self.max_span), -torch.inf)
            probabilities = (scores[0] - thresholds[i, 2]).sigmoid()
            rows, cols = (probabilities >= threshold).nonzero(as_tuple=True)
            selected = torch.stack((si[0, rows], ei[0, cols], probabilities[rows, cols].float()), dim=1).tolist()
            result.append([(int(a), int(b), score) for a, b, score in selected])
        return result


class LocateAdapter:
    """The Locate adapter of a loaded Decider, used by ``Decider.decide`` for ``"locate"`` questions."""

    def __init__(self, decider: Decider, adapter: str | Path, *, verify_base: bool = True) -> None:
        if decider.fast is not None:
            raise NotImplementedError("Locate runs on the reference path; load the Decider with fast=False")
        directory = Path(adapter)
        config = json.loads((directory / "locate_config.json").read_text())
        if config.get("format") != FORMAT:
            raise ValueError(f"Expected a {FORMAT} adapter")
        if verify_base:
            for name, expected in config["base"]["sha256"].items():
                if _sha256(decider.checkpoint / name) != expected:
                    raise ValueError(f"Adapter was trained on another base: {name} differs")
        self.decider = decider
        self.config = config
        self.proposals = int(config["head"]["proposals"])
        self.cutoff = float(config.get("thresholds", {}).get("default", 0.5))

        # A private tokenizer with the marker; the Decider's own tokenizer and encoder stay untouched.
        processor = copy.deepcopy(decider.processor)
        tokenizer = processor.tokenizer
        if LOCATE_MARKER not in tokenizer.get_vocab():
            tokenizer.add_special_tokens({"extra_special_tokens": [LOCATE_MARKER]}, replace_extra_special_tokens=False)
        self.tokenizer = tokenizer
        self.encoder = Encoder(processor, decider.codes)
        self.marker_id = self.encoder._single_token(LOCATE_MARKER)
        if self.marker_id != int(config["marker_id"]):
            raise ValueError("The Locate marker id differs from training")
        if LOCATE_MARKER not in self.encoder._escapes:
            raise ValueError("User text must not be able to produce the Locate marker")

        state = load_file(str(directory / "adapter.safetensors"))
        head_state = load_file(str(directory / "head.safetensors"))
        text_model = decider.backbone.language_model
        device = decider.device
        lora = config["lora"]
        if lora.get("layers", 0) != 0:
            raise ValueError("Only all-layer adapters are supported")
        self.adapters: list[LoRALinear] = []
        embedding = text_model.get_input_embeddings()
        originals: list[tuple[nn.Module, str, nn.Module]] = []
        try:
            for name, child in list(text_model.named_modules()):
                if isinstance(child, nn.Linear):
                    parent, _, leaf = name.rpartition(".")
                    module = text_model.get_submodule(parent) if parent else text_model
                    wrapped = LoRALinear(child, int(lora["rank"]), float(lora["alpha"]))
                    originals.append((module, leaf, child))
                    setattr(module, leaf, wrapped)
                    self.adapters.append(wrapped)
            self.embedding = MarkerEmbedding(embedding, self.marker_id).to(device)
            text_model.set_input_embeddings(self.embedding)
            parameters = {
                f"language_model.{name}": parameter
                for name, parameter in text_model.named_parameters()
                if name.endswith((".lora_a", ".lora_b", ".locate"))
            }
            if parameters.keys() != state.keys():
                missing, extra = sorted(parameters.keys() - state.keys()), sorted(state.keys() - parameters.keys())
                raise ValueError(f"Adapter does not match the backbone (missing {missing[:3]}, unexpected {extra[:3]})")
            with torch.no_grad():
                for name, parameter in parameters.items():
                    if parameter.shape != state[name].shape:
                        raise ValueError(f"Adapter shape mismatch: {name}")
                    parameter.copy_(state[name])
            head = config["head"]
            hidden = decider.backbone.config.text_config.hidden_size
            self.head = SpanHead(hidden, int(head["width"]), int(head["max_span"]))
            self.head.load_state_dict(head_state)
            self.head.requires_grad_(False).eval().to(device)
        except BaseException:
            # A failed lazy load must leave the backbone ready for a clean retry.
            text_model.set_input_embeddings(embedding)
            for module, leaf, original in reversed(originals):
                setattr(module, leaf, original)
            raise

    def validate(self, request: Mapping[str, Any], questions: Mapping[str, Any]) -> list[str]:
        """Instructions of a request's Locate ``questions``; ``RequestError`` if invalid (the ``/v1/decisions`` rules)."""
        state = request.get("state")
        if request.get("images") or not isinstance(state, str) or len(request.get("questions", {})) > MAX_QUESTIONS:
            raise RequestError(f"Locate requires text state, no images, and at most {MAX_QUESTIONS} questions")
        if not state:
            raise RequestError("Locate state must contain text")
        instructions = []
        for key, question in questions.items():
            if not isinstance(key, str) or not key:
                raise RequestError("Question IDs must be nonempty strings")
            text = question.get("instructions")
            if text is not None and not isinstance(text, str):
                raise RequestError(f"Question {key!r}: Locate instructions must be text or null")
            instructions.append(text if text is not None and text.strip() else key)
        return instructions

    def answer(self, request: Mapping[str, Any], questions: Mapping[str, Any]) -> dict[str, Any]:
        """Answers for the Locate ``questions``: Unicode character offsets into ``state`` (end exclusive), text and
        score, sorted by position. A span is kept when its probability reaches the saved cutoff (0.5)."""
        instructions = self.validate(request, questions)
        state = request["state"]
        plans = self._plan(state, instructions)
        spans = []
        tokens = 0
        for plan in plans:
            found, length = self._forward(state, plan)
            spans.extend([((a, b), score) for a, b, score in field] for field in found)
            tokens += length
        usage = {"input_tokens": tokens, "output_tokens": 0, "sequences": len(plans)}
        answers = {
            key: {
                "type": "locate",
                "spans": [{"start": a, "end": b, "text": state[a:b], "score": score} for (a, b), score in found],
            }
            for key, found in zip(questions, spans, strict=True)
        }
        return {"answers": answers, "usage": usage}

    # ------------------------------------------------------------------ internals

    def _plan(
        self, text: str, instructions: list[str]
    ) -> list[tuple[Encoded, list[int], list[tuple[int, int]]]]:
        """Prepare all groups before inference; preserve the full state and question order."""
        try:
            return [self._encode(text, instructions)]
        except LocateLengthError:
            if len(instructions) <= 1:
                raise
            middle = len(instructions) // 2
            return self._plan(text, instructions[:middle]) + self._plan(text, instructions[middle:])

    def _encode(self, text: str, instructions: list[str]) -> tuple[Encoded, list[int], list[tuple[int, int]]]:
        encoder, tokenizer = self.encoder, self.tokenizer
        context = encoder.context_text({"state": text, "questions": {}})
        escaped = encoder._text(text)  # length-preserving, so offsets map back to ``text``
        begin = len(context) - len(escaped)
        tokens = tokenizer(context, add_special_tokens=False, return_offsets_mapping=True)
        prefix = [*tokens["input_ids"], encoder.separator_id]
        chunks = [
            [*tokenizer("Question:\n" + PROMPT + encoder._text(value), add_special_tokens=False)["input_ids"],
             self.marker_id]
            for value in instructions
        ]
        ids = prefix + [token for chunk in chunks for token in chunk]
        maximum = self.decider.max_length
        if maximum is not None and len(ids) > maximum:
            raise LocateLengthError(f"Locate input exceeds max_length ({len(ids)} > {maximum})")
        markers, cursor = [], len(prefix)
        for chunk in chunks:
            cursor += len(chunk)
            markers.append(cursor - 1)
        mapping = tokens["offset_mapping"]
        positions = [i for i, (a, b) in enumerate(mapping) if a < len(context) and b > begin and a < b]
        offsets = [(max(0, mapping[i][0] - begin), min(len(escaped), mapping[i][1] - begin)) for i in positions]
        encoded = Encoded(
            keys=tuple(str(i) for i in range(len(chunks))),
            counts=(0,) * len(chunks),
            input_ids=torch.tensor(ids, dtype=torch.long),
            markers=torch.tensor(markers, dtype=torch.long),
            segments=(len(prefix), *map(len, chunks)),
            mm_token_type_ids=torch.zeros(len(ids), dtype=torch.long),
        )
        return encoded, positions, offsets

    @torch.inference_mode()
    def _forward(
        self, text: str, plan: tuple[Encoded, list[int], list[tuple[int, int]]]
    ) -> tuple[list[list[tuple[int, int, float]]], int]:
        encoded, positions, offsets = plan
        if not positions:
            return [[] for _ in encoded.keys], encoded.length
        decider = self.decider
        inputs = {key: value.to(decider.device) for key, value in left_pad([encoded], self.encoder.pad_id).items()}
        cuda = decider.device.type == "cuda"
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=cuda):
            decider.isolation.layout = question_layout([encoded], inputs["attention_mask"])
            self._enable(True)
            try:
                hidden = decider.backbone(**inputs, use_cache=False).last_hidden_state[0]
            finally:
                self._enable(False)
                decider.isolation.layout = None
            document = hidden[positions]
            fields = hidden[encoded.markers.to(decider.device)]
            raw = self.head.predict(document, fields, self.cutoff, self.proposals)
        result = []
        for spans in raw:
            unique: dict[tuple[int, int], float] = {}
            for first, last, score in spans:
                a, b = offsets[first][0], offsets[last][1]
                while a < b and text[a].isspace():
                    a += 1
                while b > a and text[b - 1].isspace():
                    b -= 1
                if a < b:
                    unique[a, b] = max(score, unique.get((a, b), 0.0))
            result.append([(a, b, score) for (a, b), score in sorted(unique.items())])
        return result, encoded.length

    def _enable(self, enabled: bool) -> None:
        self.embedding.enabled = enabled
        for adapter in self.adapters:
            adapter.enabled = enabled
