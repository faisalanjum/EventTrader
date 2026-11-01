# ARCHIVED 2026-07-15 — legacy `drivers/` folder (moved from repo root)

**What this was:** the ORIGINAL driver exploration era (2025→early 2026): `drivers_graph/` + `agenticDrivers/`
(LangGraph/MCP agents using the direct Anthropic SDK), `8K_XBRL_Linking/`, `langExtract/`, docs. Superseded by
the channel-based Driver system being built at repo-root **`driver/`** (design law: `.claude/plans/Drivers/FinalDesign/`).

**Why archived:** dormant; the root name was needed free so old path references can never collide with the new
`driver/` tree. Nothing outside this folder referenced it at archive time (grep-verified; no cron, no k8s).

**If you resurrect anything here, know:**
- These scripts use the **direct Anthropic SDK and need the raw API key**: `source ~/.anthropic_drivers_key`
  first (see CLAUDE.md "Anthropic API Key Handling" — the key is deliberately NOT in `.env`).
- Internal paths broke by the move and need fixing: `drivers_graph/studio.sh` (`cd drivers/drivers_graph`) ·
  `8K_XBRL_Linking/FinalScripts/test_pipeline.py:380` (absolute `/home/faisal/EventMarketDB/drivers/...`).
- `8K_XBRL_Linking/FinalScripts/xbrl_catalog.py` contains an inline `fiscal_to_calendar` copy — the canonical
  fiscal math now lives in `.claude/skills/earnings-orchestrator/scripts/fiscal_math.py`; do not copy from here.
