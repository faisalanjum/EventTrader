"""The ``Decider``: checkpoint loading, the exact (padded) reference path, and dispatch to the optional fast path."""

from __future__ import annotations

import functools
import math
import string
import threading
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, overload

import torch
from safetensors.torch import load_file
from transformers import AutoProcessor
from transformers.masking_utils import create_recurrent_attention_mask

from .protocol import (
    LEGACY_MAX_PIXELS,
    MAX_OPTIONS,
    MIN_PIXELS,
    MODES,
    PROTOCOL,
    Encoded,
    Encoder,
    RequestError,
    answer,
    left_pad,
    load_json,
)
from .types import Request, Response

if TYPE_CHECKING:
    from .fast import FastPath
    from .locate import LocateAdapter

#: Default per-sequence token limit. Over-length questions raise ``LengthError``; nothing is truncated.
DEFAULT_MAX_LENGTH = 32_768
BACKBONES = {"qwen3_5": "Qwen3_5Model", "qwen3_5_moe": "Qwen3_5MoeModel"}


@dataclass(frozen=True)
class FastOptions:
    """Settings of the packed fast path (requires CUDA and ``flash-linear-attention``; both modes; CUDA graphs: separate only).

    compile:      ``None`` (eager), ``"sub"`` (norms, MLPs and convolution) or ``"layer"`` (whole decoder layers).
    cuda_graphs:  pad every pack to one of ``buckets`` tokens with filler sequences and replay CUDA graphs. Needs
                  ``compile="layer"``. Compiles once per bucket (a few minutes in total, see ``Decider.warmup``).
    buckets:      static pack sizes for ``cuda_graphs``; the largest is also the packing budget.
    token_budget: tokens per packed forward pass without ``cuda_graphs``.
    prune_last:   compute the last layer's attention output and MLP only at the readout markers.
    fp8:          rowwise-scaled FP8 matmuls in the decoder layers. Faster but changes probabilities slightly.
                  Applies to every path of this ``Decider`` instance.
    prefetch:     tokenize in a background thread while the GPU runs.
    """

    compile: Literal["sub", "layer"] | None = "layer"
    cuda_graphs: bool = True
    buckets: tuple[int, ...] = (2048, 4096, 8192, 16384, 32768)
    token_budget: int = 32768
    prune_last: bool = True
    fp8: bool = False
    prefetch: bool = True

    def budget(self) -> int:
        return max(self.buckets) if self.cuda_graphs else self.token_budget


# ---------------------------------------------------------------------- attention

def enable_noncausal_full_attention(text_model: torch.nn.Module) -> None:
    """Full-attention layers attend to the whole (non-padding) sequence; linear-attention layers stay causal."""

    def mask_inputs(module: torch.nn.Module, args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[Any, Any]:
        if args:
            raise ValueError("The noncausal mask hook requires keyword inputs")
        if kwargs.get("past_key_values") is not None or kwargs.get("use_cache"):
            raise ValueError("Noncausal classification does not support a KV cache")
        embeddings = kwargs.get("inputs_embeds")
        if embeddings is None:
            embeddings = module.embed_tokens(kwargs["input_ids"])
        padding = kwargs.get("attention_mask")
        if padding is None:
            padding = torch.ones(embeddings.shape[:2], device=embeddings.device, dtype=torch.bool)
        if isinstance(padding, dict):  # already converted
            return args, kwargs
        kwargs["attention_mask"] = {
            "full_attention": padding[:, None, None, :].bool(),
            "linear_attention": create_recurrent_attention_mask(
                config=module.config, inputs_embeds=embeddings, attention_mask=padding
            ),
        }
        return args, kwargs

    text_model.register_forward_pre_hook(mask_inputs, with_kwargs=True)


# Token segments of an isolated-question batch; question blocks are numbered from zero.
STATE_SEGMENT = -1
PADDING_SEGMENT = -3


@dataclass(frozen=True)
class QuestionLayout:
    """Where each question block of a left-padded batch lies (``mode="isolated"``).

    ``segments`` labels every token: the context (state), a question block (its text and readout marker), or padding.
    Linear-attention layers rerun every later block after its row's context (``restarts``: row, block start, block
    end), so each block starts from the context's final recurrent memory; block positions continue from the
    context's last position (``offsets``).
    """

    segments: torch.Tensor
    boundaries: torch.Tensor
    offsets: torch.Tensor
    restarts: tuple[tuple[int, int, int], ...]
    mask: torch.Tensor  # SDPA boolean mask (batch, 1, length, length)


def question_layout(chunks: Sequence[Encoded], padding: torch.Tensor) -> QuestionLayout:
    """The isolated-question layout of a left-padded batch, and its full-attention mask.

    The context attends everything (itself and every question); each question block attends the context and itself.
    Padding queries attend every valid key so SDPA never sees an empty row; their outputs are unused.
    """
    valid = padding.bool().cpu()
    length = valid.shape[1]
    segments = torch.full(valid.shape, PADDING_SEGMENT, dtype=torch.long)
    offsets = torch.zeros(valid.shape, dtype=torch.long)
    boundaries: list[int] = []
    restarts: list[tuple[int, int, int]] = []
    for row, chunk in enumerate(chunks):
        start = length - chunk.length
        if int(valid[row].sum()) != chunk.length:
            raise ValueError("Chunk lengths do not match the padded row")
        bounds = [start]
        for size in chunk.segments:
            bounds.append(bounds[-1] + size)
        boundary = bounds[1]
        boundaries.append(boundary)
        segments[row, start:boundary] = STATE_SEGMENT
        for index, (begin, end) in enumerate(zip(bounds[1:-1], bounds[2:], strict=True)):
            segments[row, begin:end] = index
            offsets[row, begin:end] = torch.arange(end - begin)
            if index:
                restarts.append((row, begin, end))
    query, key = segments[:, :, None], segments[:, None, :]
    allowed = (key == STATE_SEGMENT) | (query == key) | (query == STATE_SEGMENT)
    allowed = (allowed | ~valid[:, :, None]) & valid[:, None, :]
    device = padding.device
    return QuestionLayout(
        segments.to(device), torch.tensor(boundaries, device=device), offsets.to(device), tuple(restarts),
        allowed[:, None].to(device),
    )


class IsolatedQuestions:
    """Hooks that run a backbone with isolated questions while ``layout`` is set (no effect otherwise).

    - every full-attention layer gets the block mask of ``QuestionLayout``;
    - every linear-attention (gated delta net) layer restarts each later question block from the context's final
      recurrent memory;
    - question positions restart after the context's last position in every block.
    """

    def __init__(self, text_model: torch.nn.Module) -> None:
        self.layout: QuestionLayout | None = None
        config = text_model.config
        for layer, kind in zip(text_model.layers, config.layer_types, strict=True):
            if kind == "full_attention":
                layer.register_forward_pre_hook(self._mask, with_kwargs=True)
            elif kind == "linear_attention":
                attention = layer.linear_attn
                attention.forward = functools.partial(self._restarted, attention.forward, attention)
            else:
                raise ValueError(f"Unexpected layer type {kind!r}")
        # Registered after the noncausal hook, so it sees the positions the backbone passes to the text model.
        text_model.register_forward_pre_hook(self._positions, with_kwargs=True)

    def _mask(self, module: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[Any, Any]:
        if self.layout is None:
            return args, kwargs
        mask = kwargs.get("attention_mask")
        if not isinstance(mask, torch.Tensor) or mask.ndim != 4 or mask.shape[2] != 1:
            raise ValueError("Expected the noncausal padding mask")
        kwargs["attention_mask"] = self.layout.mask
        return args, kwargs

    def _positions(self, module: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[Any, Any]:
        layout = self.layout
        if layout is None:
            return args, kwargs
        embeddings = kwargs.get("inputs_embeds")
        if embeddings is None:
            embeddings = module.embed_tokens(kwargs["input_ids"])
        positions = kwargs.get("position_ids")
        if positions is None:
            # The text model's own default: the same positions in its text and three rotary rows.
            batch, length = embeddings.shape[:2]
            positions = torch.arange(length, device=embeddings.device).view(1, 1, -1).expand(4, batch, -1)
        last = positions.gather(-1, (layout.boundaries - 1).view(1, -1, 1).expand(positions.shape[0], -1, 1))
        kwargs["position_ids"] = torch.where(layout.segments >= 0, last + 1 + layout.offsets, positions)
        return args, kwargs

    def _restarted(
        self,
        forward: Callable[..., torch.Tensor],
        attention: torch.nn.Module,
        hidden_states: torch.Tensor,
        *args: Any,
        attention_mask: torch.Tensor | None = None,
        **kwargs: Any,
    ) -> torch.Tensor:
        output = forward(hidden_states, *args, attention_mask=attention_mask, **kwargs)
        layout = self.layout
        if layout is None or not layout.restarts:
            return output
        batch, length, width = hidden_states.shape
        pads = (layout.segments == PADDING_SEGMENT).sum(-1).tolist()
        boundaries = layout.boundaries.tolist()
        sources: list[list[int]] = []
        targets: list[int] = []
        for row, start, end in layout.restarts:
            state = range(row * length + pads[row], row * length + boundaries[row])
            sources.append([*state, *range(row * length + start, row * length + end)])
            targets.extend(range(row * length + start, row * length + end))
        longest = max(map(len, sources))
        # Left-pad the restarted sequences, as the processor pads rows.
        device = hidden_states.device
        index = torch.tensor([[0] * (longest - len(row)) + row for row in sources], device=device)
        valid = torch.tensor([[0] * (longest - len(row)) + [1] * len(row) for row in sources], device=device)
        flat = hidden_states.reshape(batch * length, width)
        # One call over all restarted blocks, as evaluated, unless it would pass 2**31 elements in its widest
        # activation, the padded causal convolution (blocks x conv_dim x (longest + kernel - 1)); 32-bit indexing
        # then fails or returns non-finite values (large padded batches of many-question requests). The blocks then
        # run in sub-batches (each block is its own sequence either way).
        widest = max(attention.conv_dim, width) * (longest + attention.conv_kernel_size - 1)
        rows = max(1, (2**31 - 1) // widest)
        restarted = torch.cat([
            forward(flat[index[i : i + rows]] * valid[i : i + rows, :, None].to(flat.dtype), *args,
                    attention_mask=valid[i : i + rows], **kwargs)
            for i in range(0, len(sources), rows)
        ])
        kept = torch.cat(
            [restarted[row, longest - (end - start) :] for row, (_, start, end) in enumerate(layout.restarts)]
        )
        result = output.reshape(batch * length, -1).index_put((torch.tensor(targets, device=output.device),), kept)
        return result.view(batch, length, -1)


# ---------------------------------------------------------------------- loading

def _located(request: Any) -> dict[str, Any]:
    """The request's ``"locate"`` questions (none for a malformed request, which the decision path rejects)."""
    questions = request.get("questions") if isinstance(request, dict) else None
    if not isinstance(questions, dict):
        return {}
    return {k: q for k, q in questions.items() if isinstance(q, dict) and q.get("type") == "locate"}


def _resolve(path_or_repo: str | Path, revision: str | None, token: str | bool | None) -> Path:
    path = Path(path_or_repo)
    if path.is_dir():
        return path
    from huggingface_hub import snapshot_download

    return Path(snapshot_download(str(path_or_repo), revision=revision, token=token))


def _backbone(checkpoint: Path, config: dict[str, Any], dtype: torch.dtype) -> torch.nn.Module:
    model_type = load_json(checkpoint / "config.json").get("model_type")
    if model_type not in BACKBONES or config.get("model_type", model_type) != model_type:
        raise ValueError(f"Unsupported or inconsistent backbone type {model_type!r}")
    if model_type == "qwen3_5_moe":
        from transformers.models.qwen3_5_moe.modeling_qwen3_5_moe import Qwen3_5MoeModel

        return Qwen3_5MoeModel.from_pretrained(
            str(checkpoint), dtype=dtype, attn_implementation="sdpa",
            experts_implementation=config.get("experts_implementation") or "grouped_mm",
        )
    from transformers.models.qwen3_5.modeling_qwen3_5 import Qwen3_5Model

    return Qwen3_5Model.from_pretrained(str(checkpoint), dtype=dtype, attn_implementation="sdpa")


class Decider:
    """Answers multi-question decision requests with a protocol-v4 (chunked readout) checkpoint.

    >>> decider = Decider.from_pretrained("perplexity-ai/<repo>", device="cuda")
    >>> decider.decide({"state": "...", "questions": {"route": {"type": "choice", "criteria": {...}}}})
    """

    def __init__(
        self,
        checkpoint: Path,
        *,
        device: str = "cuda",
        fast: bool | FastOptions = False,
        mode: str = "separate",
        max_length: int | None = DEFAULT_MAX_LENGTH,
        max_pixels: int | None = None,
        batch_tokens: int = 32768,
        cpu_threads: int = 8,
        locate: bool | None = None,
    ) -> None:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self._inference_lock = threading.RLock()
        self.checkpoint = checkpoint
        self.device = torch.device(device)
        self.mode = mode
        protocol = load_json(checkpoint / "joint_config.json") if (checkpoint / "joint_config.json").exists() else {}
        if protocol != PROTOCOL:
            raise ValueError("This checkpoint does not declare the chunked joint protocol (version 4)")
        config = load_json(checkpoint / "decision_config.json")
        if config.get("attention_mode") != "noncausal_full_attention" or config.get("pooling", "last") != "last":
            raise ValueError("Expected a noncausal checkpoint with per-position readouts")
        self.temperature = float(config["temperature"])
        if not math.isfinite(self.temperature) or self.temperature <= 0:
            raise ValueError("Saved temperature must be positive and finite")
        self.codes: list[str] = list(config["codes"])
        self.max_length = max_length
        self.batch_tokens = batch_tokens
        self.max_pixels = int(max_pixels or config.get("max_pixels") or LEGACY_MAX_PIXELS)

        torch.set_num_threads(cpu_threads)
        torch.backends.cuda.enable_cudnn_sdp(False)  # the evaluated SDPA kernel choice
        self.processor = AutoProcessor.from_pretrained(str(checkpoint))
        self.processor.tokenizer.padding_side = "left"
        self.processor.image_processor.size = {"shortest_edge": MIN_PIXELS, "longest_edge": self.max_pixels}
        tokenizer = self.processor.tokenizer
        if len(self.codes) != MAX_OPTIONS or any(
            tokenizer.encode(code, add_special_tokens=False) != [token_id]
            for code, token_id in zip(self.codes, config["token_ids"], strict=True)
        ):
            raise ValueError("Checkpoint answer codes differ from its tokenizer")
        if any(not set(code) <= set(string.ascii_uppercase) for code in self.codes):
            raise ValueError("Unexpected answer codes")
        self.encoder = Encoder(self.processor, self.codes)

        dtype = torch.bfloat16 if self.device.type == "cuda" else torch.float32
        self.backbone = _backbone(checkpoint, config, dtype)
        self.is_moe = self.backbone.config.model_type == "qwen3_5_moe"
        hidden = self.backbone.config.text_config.hidden_size
        self.readout = torch.nn.Linear(hidden, MAX_OPTIONS, bias=False, dtype=dtype)
        self.readout.load_state_dict(load_file(str(checkpoint / "readout.safetensors")))
        text_model = self.backbone.language_model
        enable_noncausal_full_attention(text_model)
        self.isolation = IsolatedQuestions(text_model)
        self.backbone.requires_grad_(False).eval().to(self.device)
        self.readout.requires_grad_(False).eval().to(self.device)

        self.fast: FastPath | None = None
        if fast:
            from .fast import FastPath

            self.fast = FastPath(self, fast if isinstance(fast, FastOptions) else FastOptions())

        # Keep decision-only instances unchanged; attach Locate on its first request.
        self.locate: LocateAdapter | None = None
        self._locate_enabled = locate is not False and self.fast is None

    @classmethod
    def from_pretrained(
        cls,
        path_or_repo: str | Path,
        *,
        device: str = "cuda",
        fast: bool | FastOptions = False,
        mode: str = "separate",
        max_length: int | None = DEFAULT_MAX_LENGTH,
        max_pixels: int | None = None,
        revision: str | None = None,
        token: str | bool | None = None,
        locate: bool | None = None,
        **kwargs: Any,
    ) -> Decider:
        """Load a local checkpoint directory or a Hugging Face repository.

        fast:       ``False`` for the reference path (padded batches through the Transformers backbone); ``True`` or a
                    ``FastOptions`` for the packed path (``mode="separate"`` only).
        mode:       ``"separate"`` (default; one sequence per question, the evaluated computation) or ``"isolated"``
                    (one sequence per request with isolated questions, the training layout).
        max_length: per-sequence token limit, see the README.
        max_pixels: image pixel cap (default: the checkpoint's ``max_pixels``, else 262,144).
        locate:     enable ``"locate"`` questions (default: enabled with ``fast=False``). The adapter is loaded
                    on the first Locate request; ``False`` disables it.
        """
        return cls(_resolve(path_or_repo, revision, token), device=device, fast=fast, mode=mode,
                   max_length=max_length, max_pixels=max_pixels, locate=locate, **kwargs)

    # ------------------------------------------------------------------ public API

    @overload
    def decide(self, requests: Request, *, temperature: float | None = None) -> Response: ...
    @overload
    def decide(self, requests: Sequence[Request], *, temperature: float | None = None) -> list[Response]: ...

    def decide(
        self, requests: Request | Sequence[Request], *, temperature: float | None = None
    ) -> Response | list[Response]:
        """Answer one request (returns a ``Response``) or a list of requests (returns a list, same order).

        Each response holds one answer per question and the token usage. ``temperature`` overrides the calibrated
        temperature saved with the checkpoint (leave it unset for calibrated probabilities). ``"locate"`` questions
        are answered by the Locate adapter in their own forward pass; the other questions as without it.
        """
        with self._inference_lock:
            single = isinstance(requests, dict)
            batch: list[Request] = [requests] if single else list(requests)  # type: ignore[list-item]
            scale = self.temperature if temperature is None else float(temperature)
            if not math.isfinite(scale) or scale <= 0:
                raise ValueError("Temperature must be positive and finite")
            located = [_located(request) for request in batch]
            if not any(located):
                responses = [self._respond(request, logits, chunks, scale) for request, logits, chunks in self._run(batch)]
                return responses[0] if single else responses
            if self.locate is None:
                if not self._locate_enabled or not (self.checkpoint / "locate-span").is_dir():
                    raise RequestError("'locate' questions need a checkpoint with locate-span/, loaded with fast=False")
                from .locate import LocateAdapter

                self.locate = LocateAdapter(self, self.checkpoint / "locate-span")
            for request, questions in zip(batch, located, strict=True):
                if questions:
                    self.locate.validate(request, questions)
            # Decision questions keep the plain path (and its validation); Locate-only requests skip it.
            decisions = [
                {**request, "questions": {k: q for k, q in request["questions"].items() if k not in questions}}
                if questions else request
                for request, questions in zip(batch, located, strict=True)
            ]
            pending = [i for i, request in enumerate(decisions) if not located[i] or request["questions"]]
            responses: dict[int, Response] = {
                i: self._respond(request, logits, chunks, scale)
                for i, (request, logits, chunks) in zip(pending, self._run([decisions[i] for i in pending]), strict=True)
            }
            results = []
            for i, (request, questions) in enumerate(zip(batch, located, strict=True)):
                empty: Response = {"answers": {}, "usage": {"input_tokens": 0, "output_tokens": 0, "sequences": 0}}
                response = responses.get(i, empty)
                if questions:
                    assert self.locate is not None
                    spans = self.locate.answer(request, questions)
                    answers = {**response["answers"], **spans["answers"]}
                    usage = {key: response["usage"][key] + spans["usage"][key] for key in response["usage"]}
                    response = {"answers": {key: answers[key] for key in request["questions"]}, "usage": usage}
                results.append(response)
            return results[0] if single else results

    def logits(self, requests: Sequence[Request]) -> list[dict[str, list[float]]]:
        """Raw readout logits per question (valid options only, before temperature). Useful for ranking."""
        with self._inference_lock:
            return [dict(logits) for _, logits, _ in self._run(list(requests))]

    def warmup(self) -> None:
        """Compile the fast path for every bucket now instead of on first use (no-op for the reference path)."""
        with self._inference_lock:
            if self.fast is not None:
                self.fast.warmup()

    # ------------------------------------------------------------------ internals

    def _respond(
        self, request: Request, logits: dict[str, list[float]], chunks: list[Encoded], scale: float
    ) -> Response:
        answers = {}
        for key, question in request["questions"].items():
            values = torch.tensor(logits[key], dtype=torch.float32)
            answers[key] = answer(question, (values / scale).softmax(-1).tolist())
        return {
            "answers": answers,
            "usage": {"input_tokens": sum(c.length for c in chunks), "output_tokens": 0, "sequences": len(chunks)},
        }

    def _run(self, requests: list[Request]) -> Iterator[tuple[Request, dict[str, list[float]], list[Encoded]]]:
        if self.fast is not None:
            yield from self.fast.run(requests)
            return
        plans = [self.encoder.plan(request, self.max_length, self.mode) for request in requests]
        flat = [(index, chunk) for index, plan in enumerate(plans) for chunk in plan]
        results: dict[tuple[int, str], list[float]] = {}
        for group in self._batches(flat):
            for (index, chunk), rows in zip(group, self.reference_logits([c for _, c in group]), strict=True):
                for key, values in zip(chunk.keys, rows, strict=True):
                    results[index, key] = values
        for index, (request, plan) in enumerate(zip(requests, plans, strict=True)):
            yield request, {key: results[index, key] for key in request["questions"]}, plan

    def _batches(self, flat: list[tuple[int, Encoded]]) -> Iterable[list[tuple[int, Encoded]]]:
        """Length-sorted batches whose padded size stays within ``batch_tokens`` (always at least one sequence)."""
        order = sorted(flat, key=lambda item: item[1].length)
        group: list[tuple[int, Encoded]] = []
        for item in order:
            if group and (len(group) + 1) * item[1].length > self.batch_tokens:
                yield group
                group = []
            group.append(item)
        if group:
            yield group

    @torch.inference_mode()
    def reference_logits(self, chunks: Sequence[Encoded]) -> list[list[list[float]]]:
        """One left-padded batch through the Transformers backbone (noncausal; isolated questions if needed)."""
        with self._inference_lock:
            inputs = {key: value.to(self.device) for key, value in left_pad(chunks, self.encoder.pad_id).items()}
            isolated = any(len(chunk.keys) > 1 for chunk in chunks)
            self.isolation.layout = question_layout(chunks, inputs["attention_mask"]) if isolated else None
            try:
                hidden = self.backbone(**inputs, use_cache=False).last_hidden_state
            finally:
                self.isolation.layout = None
            offsets = [inputs["input_ids"].shape[1] - chunk.length for chunk in chunks]
            rows = torch.cat([torch.full((len(c.keys),), i) for i, c in enumerate(chunks)]).to(self.device)
            cols = torch.cat([c.markers + offsets[i] for i, c in enumerate(chunks)]).to(self.device)
            logits = self.readout(hidden[rows, cols]).float().cpu()
            out, cursor = [], 0
            for chunk in chunks:
                out.append([logits[cursor + j, :count].tolist() for j, count in enumerate(chunk.counts)])
                cursor += len(chunk.keys)
            return out
