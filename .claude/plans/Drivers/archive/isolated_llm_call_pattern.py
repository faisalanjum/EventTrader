"""
ISOLATED OpenAI STRUCTURED-CALL PATTERN  —  for driver identification (reference)
=================================================================================
Purpose: capture EXACTLY how this repo makes a structured LLM API call, so we can
reuse the SAME call style for isolated driver-identification calls. The transcript
code was only WHERE this pattern happens to live — none of the speaker/Q&A logic
is relevant here and it is intentionally NOT copied.

DISTILLED FROM (the one structured OpenAI call in the repo):
  transcripts/EarningsCallTranscripts.py :: classify_speakers()   (lines 534-605)

────────────────────────────────────────────────────────────────────────────────
THE PATTERN (this is the part that matters — "how we call the model")
────────────────────────────────────────────────────────────────────────────────
  client : OpenAI(api_key=OPENAI_API_KEY)        # from eventtrader.keys
  model  : "gpt-4o"                              # config/feature_flags.py:140
                                                 #   (SPEAKER_CLASSIFICATION_MODEL)
  API    : client.responses.create(...)          # OpenAI *Responses* API (not chat)
  shape  : input=[{role:"system",...},{role:"user",...}]
  output : text={"format":{"type":"json_schema","name":...,"strict":True,
                           "schema":{...}}}       # strict schema → guaranteed JSON
  temp   : 0.0                                    # as deterministic as the API allows
  parse  : response.output[0].content → the item with .type=="output_text"
                           → json.loads(item.text)   (and bail on a refusal item)

────────────────────────────────────────────────────────────────────────────────
BILLING  (read before adopting)
────────────────────────────────────────────────────────────────────────────────
This is the DIRECT OpenAI API (metered, billed to OPENAI_API_KEY) — a SEPARATE
budget from the Anthropic Claude subscription. So an "isolated driver-id call" via
this path is a *metered OpenAI* call, not a subscription call.
  - The harness's Pass-4 producer runs IN-SESSION on the Anthropic subscription.
  - THIS pattern is a different, metered path — appropriate for small isolated
    semantic-judge calls if we accept the OpenAI cost. Confirm that's intended.
See: feedback_llm_vs_code_boundary.md (LLM = semantic judgment, code = mechanics),
     project_openai_key_rotation.md (OpenAI billing watch).

────────────────────────────────────────────────────────────────────────────────
WHERE driver-id would use this (the "optional isolated LLM judge" in the
LLM-vs-code architecture) — each is one isolated structured call:
  - semantic reuse:   "does <proposed> mean an EXISTING driver?"        (K47/K52)
  - synonym discovery: "is <token_a> ≈ <token_b>?"  (caller supplies to_token)
  - slot declaration: "which slot does novel token <x> belong to?"      (watch-spot #1)
  - evidence support: "does the cited SRC actually JUSTIFY this driver?"
  - scope/granularity: "too narrow / too generic / wrong scope?"        (R9/K52)
The DECISION/FOLD that follows each stays deterministic CODE.
"""

from __future__ import annotations

import json
from openai import OpenAI
from eventtrader.keys import OPENAI_API_KEY

# Mirror of SPEAKER_CLASSIFICATION_MODEL (config/feature_flags.py:140). Kept as its
# own const so the driver path can diverge from the transcript path if we want.
DRIVER_LLM_MODEL = "gpt-4o"

_client = OpenAI(api_key=OPENAI_API_KEY)


def isolated_llm_json_call(
    system_instruction: str,
    user_payload: str,
    json_schema: dict,
    *,
    schema_name: str = "driver_call",
    model: str = DRIVER_LLM_MODEL,
    temperature: float = 0.0,
) -> dict | None:
    """One isolated, structured OpenAI call — same mechanics as classify_speakers().

    Generic on purpose: the SCHEMA and the two prompts are what change per
    driver-id task (reuse / synonym / slot / evidence-support / scope). Returns the
    parsed JSON object, or None on a refusal / empty output.

    NOTE: no rate limiting here for clarity. The source wraps calls with
    ModelRateLimiter.wait_if_needed(model) (EarningsCallTranscripts.py:877) — add it
    back if we batch these at volume.
    """
    response = _client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_payload},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": json_schema,
            }
        },
        temperature=temperature,
    )

    if not response.output:
        return None

    content = response.output[0].content
    # Bail on a model refusal rather than trying to parse it as JSON.
    for item in content:
        if getattr(item, "type", "") in ("refusal", "response.refusal.done"):
            return None
    for item in content:
        if getattr(item, "type", "") == "output_text":
            return json.loads(item.text)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# EXAMPLE adaptation (illustrative only — real schema/prompts come later)
# ─────────────────────────────────────────────────────────────────────────────
# Semantic reuse judge: does a proposed driver mean one we already have?
#
#   REUSE_SCHEMA = {
#       "type": "object",
#       "properties": {
#           "reuse_existing": {"type": "boolean"},
#           "existing_name":  {"type": ["string", "null"]},
#           "reason":         {"type": "string"},
#       },
#       "required": ["reuse_existing", "existing_name", "reason"],
#       "additionalProperties": False,
#   }
#
#   decision = isolated_llm_json_call(
#       "You decide if a PROPOSED driver name means an EXISTING one. Reuse-first: "
#       "prefer an existing canonical name over creating a near-duplicate.",
#       "Proposed: iphone_china_demand\n"
#       "Existing catalog: [iphone_china_sales, iphone_sales, services_revenue]",
#       REUSE_SCHEMA,
#       schema_name="reuse_decision",
#   )
#   # → {"reuse_existing": True, "existing_name": "iphone_china_sales", "reason": ...}
#   # Then CODE applies the fold deterministically (exact / alias / sorted-token).
