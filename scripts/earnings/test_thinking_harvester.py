"""Tests for thinking_harvester + pipeline_contracts (registry portion).

Phase 1 tests (this file is extended through Phases 2/4). All 3 registry
assertions here were absorbed from the dropped config/test_pipeline_contracts.py
per the plan's file-consolidation decision.
"""
from __future__ import annotations
import sys
from pathlib import Path

# scripts/earnings is NOT a package (no __init__.py). Keep imports top-level.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest


# ── Phase 1: config/pipeline_contracts.py registry tests ──────────────────

def test_registry_has_three_types():
    from config.pipeline_contracts import KNOWN_TYPES
    assert KNOWN_TYPES == frozenset({"guidance", "prediction", "learning"})


def test_experiment_name_requires_prefix_accepts():
    from config.pipeline_contracts import validate_experiment_name
    # Must not raise — "prediction_no_lessons" starts with "prediction_"
    validate_experiment_name("prediction", "prediction_no_lessons")


def test_experiment_name_requires_prefix_rejects_wrong_parent():
    from config.pipeline_contracts import validate_experiment_name
    with pytest.raises(ValueError):
        validate_experiment_name("prediction", "learning_variant")


def test_experiment_name_rejects_unknown_type():
    from config.pipeline_contracts import validate_experiment_name
    with pytest.raises(ValueError):
        validate_experiment_name("unknown_type", "unknown_type_tag")


def test_experiment_name_rejects_no_prefix():
    from config.pipeline_contracts import validate_experiment_name
    with pytest.raises(ValueError):
        validate_experiment_name("prediction", "no_lessons")


def test_experiment_name_rejects_empty_tag():
    from config.pipeline_contracts import validate_experiment_name
    with pytest.raises(ValueError):
        validate_experiment_name("prediction", "prediction_")


def test_experiment_name_rejects_case_mismatch():
    from config.pipeline_contracts import validate_experiment_name
    with pytest.raises(ValueError):
        # KNOWN_TYPES is lowercase; "Prediction" is not in the set
        validate_experiment_name("Prediction", "Prediction_tag")


# ── Phase 4: thinking_harvester tests ──────────────────────────────────────

import json
import shutil

REPO_ROOT_H = Path(__file__).resolve().parents[2]
if str(REPO_ROOT_H / "scripts" / "earnings") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_H / "scripts" / "earnings"))

FIXTURES = Path(__file__).parent / "tests" / "fixtures"
PROJECTS_DIR = Path.home() / ".claude" / "projects" / "-home-faisal-EventMarketDB"

LEARNER_SID = "98984e15-2570-425a-9429-dec0c3dbf7ff"
GUIDANCE_SID = "235cf379-282f-4637-9c30-7cf19c43a85d"
PREDICTOR_SID = "374b1345-411b-46cc-a363-3cce54db33a6"


# ── Helpers for synthetic SDK-project layouts ────────────────────────────

def _stage_fixture_session(tmp_path: Path, fixture_name: str, sid: str) -> Path:
    """Copy a fixture session JSONL + its subagents into a fresh SDK-projects layout.

    Returns the SDK-projects dir path (passed to the harvester as ``projects_root``).
    """
    projects_root = tmp_path / "projects"
    projects_root.mkdir(parents=True)
    # Primary JSONL
    shutil.copy(FIXTURES / f"{fixture_name}.jsonl", projects_root / f"{sid}.jsonl")
    # Subagent tree
    src_subagents = FIXTURES / fixture_name / "subagents"
    dst_subagents = projects_root / sid / "subagents"
    dst_subagents.mkdir(parents=True)
    for f in src_subagents.iterdir():
        shutil.copy(f, dst_subagents / f.name)
    return projects_root


# ── (a) EMBED-visible: learner ────────────────────────────────────────────

def test_harvest_learner_embed_visible(tmp_path):
    from thinking_harvester import harvest
    projects_root = _stage_fixture_session(tmp_path, "learner_session", LEARNER_SID)
    vault_root = tmp_path / "vault"

    harvest(
        thinking_type="learning",
        ticker="BURL",
        quarter="Q4_FY2025",
        session_id=LEARNER_SID,
        vault_root=vault_root,
        projects_root=projects_root,
    )

    comp_dir = vault_root / "BURL" / "events" / "Q4_FY2025" / "learning"
    thinking_md = comp_dir / "thinking.md"
    subagents_dir = comp_dir / "subagents"
    assert thinking_md.exists(), "learning/thinking.md must exist"
    assert subagents_dir.is_dir(), "learning/subagents/ must exist for EMBED pattern"

    subagent_files = sorted(subagents_dir.glob("*.md"))
    assert len(subagent_files) == 6, f"expected 6 subagent files, got {len(subagent_files)}"

    content = thinking_md.read_text()
    assert "session_pattern: EMBED-visible" in content
    assert "thinking_blocks: 6" in content
    assert "thinking_chars: 17682" in content
    assert "subagents_count: 6" in content


def test_harvest_learner_subagent_filenames_match_subagent_type_and_agent_id_prefix(tmp_path):
    from thinking_harvester import harvest
    projects_root = _stage_fixture_session(tmp_path, "learner_session", LEARNER_SID)
    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="learning", ticker="BURL", quarter="Q4_FY2025",
        session_id=LEARNER_SID, vault_root=vault_root, projects_root=projects_root,
    )
    subagents_dir = vault_root / "BURL" / "events" / "Q4_FY2025" / "learning" / "subagents"
    filenames = sorted(p.name for p in subagents_dir.iterdir())
    # Agent types present: neo4j-transcript, neo4j-xbrl, neo4j-news (×2), alphavantage-earnings, neo4j-entity
    # Expected agent_ids (first 8 chars each from fixture inspection):
    expected_prefixes = {"aac55e09", "a03664cc", "a55e04c8", "a5a93ae1", "a57bd37f", "a4af78e0"}
    found_prefixes = set()
    for fn in filenames:
        # filename = {subagent_type}_{agent_id[:8]}.md
        assert fn.endswith(".md")
        stem = fn[:-3]
        prefix = stem.rsplit("_", 1)[-1]
        found_prefixes.add(prefix)
    assert found_prefixes == expected_prefixes


# ── (b) EMBED-redacted: guidance ──────────────────────────────────────────

def test_harvest_guidance_embed_redacted(tmp_path):
    from thinking_harvester import harvest
    projects_root = _stage_fixture_session(tmp_path, "guidance_session", GUIDANCE_SID)
    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="guidance", ticker="BURL", quarter="Q4_FY2025",
        session_id=GUIDANCE_SID, vault_root=vault_root, projects_root=projects_root,
    )
    comp_dir = vault_root / "BURL" / "events" / "Q4_FY2025" / "guidance"
    thinking_md = comp_dir / "thinking.md"
    assert thinking_md.exists()
    content = thinking_md.read_text()
    assert "session_pattern: EMBED-redacted" in content
    assert "redacted_thinking_blocks: 4" in content
    assert "content redacted (signed)" in content
    # 2 Agent-spawned extraction subagents
    subagents_dir = comp_dir / "subagents"
    assert len(list(subagents_dir.glob("*.md"))) == 2


# ── (c) FORK: predictor ───────────────────────────────────────────────────

def test_harvest_predictor_fork_no_subagents_dir(tmp_path):
    from thinking_harvester import harvest
    projects_root = _stage_fixture_session(tmp_path, "predictor_session", PREDICTOR_SID)
    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="prediction", ticker="BURL", quarter="Q4_FY2025",
        session_id=PREDICTOR_SID, vault_root=vault_root, projects_root=projects_root,
    )
    comp_dir = vault_root / "BURL" / "events" / "Q4_FY2025" / "prediction"
    thinking_md = comp_dir / "thinking.md"
    subagents_dir = comp_dir / "subagents"
    assert thinking_md.exists(), "prediction/thinking.md must exist"
    assert not subagents_dir.exists(), "FORK pattern must NOT emit subagents/ dir"

    content = thinking_md.read_text()
    assert "session_pattern: FORK" in content
    # Skill-fork content is the thinking source; largest text block is 1,926 chars
    assert "1926" in content or "1,926" in content or "Bundle analysis" in content.lower() \
           or "earnings-prediction" in content


# ── (d) agentId linkage is load-bearing (synthetic out-of-order fixture) ──

def test_harvest_agent_id_linkage_survives_completion_order_skew(tmp_path):
    """Build a synthetic session where tool_results complete in REVERSE spawn order.

    agentId-based linkage should still label each subagent correctly.
    Order-based (positional) matching would mislabel them.
    """
    from thinking_harvester import harvest
    projects_root = tmp_path / "projects"
    sid = "synthetic-order-skew-session"
    (projects_root / sid / "subagents").mkdir(parents=True)

    # Primary session: 3 Agent spawns in order A, B, C; tool_results in order C, B, A
    primary = projects_root / f"{sid}.jsonl"
    lines = []
    # Spawn A
    lines.append(json.dumps({
        "type": "assistant", "timestamp": "2026-01-01T00:00:01Z",
        "message": {"content": [
            {"type": "tool_use", "id": "tu-A", "name": "Agent",
             "input": {"subagent_type": "agent-A"}}
        ]}
    }))
    # Spawn B
    lines.append(json.dumps({
        "type": "assistant", "timestamp": "2026-01-01T00:00:02Z",
        "message": {"content": [
            {"type": "tool_use", "id": "tu-B", "name": "Agent",
             "input": {"subagent_type": "agent-B"}}
        ]}
    }))
    # Spawn C
    lines.append(json.dumps({
        "type": "assistant", "timestamp": "2026-01-01T00:00:03Z",
        "message": {"content": [
            {"type": "tool_use", "id": "tu-C", "name": "Agent",
             "input": {"subagent_type": "agent-C"}}
        ]}
    }))
    # Results in REVERSE order (C finishes first, A last) — simulates alphavantage rate-limit fast-fail
    lines.append(json.dumps({
        "type": "user", "timestamp": "2026-01-01T00:00:10Z",
        "message": {"content": [
            {"type": "tool_result", "tool_use_id": "tu-C",
             "content": [{"type": "text", "text": "C done"}]}
        ]},
        "toolUseResult": {"agentId": "cccccccccccccccc", "agentType": "agent-C"},
    }))
    lines.append(json.dumps({
        "type": "user", "timestamp": "2026-01-01T00:00:11Z",
        "message": {"content": [
            {"type": "tool_result", "tool_use_id": "tu-B",
             "content": [{"type": "text", "text": "B done"}]}
        ]},
        "toolUseResult": {"agentId": "bbbbbbbbbbbbbbbb", "agentType": "agent-B"},
    }))
    lines.append(json.dumps({
        "type": "user", "timestamp": "2026-01-01T00:00:12Z",
        "message": {"content": [
            {"type": "tool_result", "tool_use_id": "tu-A",
             "content": [{"type": "text", "text": "A done"}]}
        ]},
        "toolUseResult": {"agentId": "aaaaaaaaaaaaaaaa", "agentType": "agent-A"},
    }))
    primary.write_text("\n".join(lines) + "\n")

    # Subagent JSONLs (minimal) with matching agentIds + meta.json
    for letter, agent_id in [("A", "aaaaaaaaaaaaaaaa"),
                              ("B", "bbbbbbbbbbbbbbbb"),
                              ("C", "cccccccccccccccc")]:
        sub_jsonl = projects_root / sid / "subagents" / f"agent-{agent_id}.jsonl"
        sub_jsonl.write_text(json.dumps({
            "type": "user", "timestamp": f"2026-01-01T00:00:0{letter}0Z",
            "message": {"content": f"Prompt for agent-{letter}"},
        }) + "\n")
        meta = projects_root / sid / "subagents" / f"agent-{agent_id}.meta.json"
        meta.write_text(json.dumps({"agentType": f"agent-{letter}", "description": f"Agent {letter}"}))

    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="learning", ticker="TST", quarter="QX",
        session_id=sid, vault_root=vault_root, projects_root=projects_root,
    )

    subagents_dir = vault_root / "TST" / "events" / "QX" / "learning" / "subagents"
    filenames = sorted(p.name for p in subagents_dir.iterdir())
    # Each subagent file should be named {agent_type}_{agent_id[:8]}.md
    # Correct labeling requires agentId-based linkage, not positional.
    assert "agent-A_aaaaaaaa.md" in filenames, f"got: {filenames}"
    assert "agent-B_bbbbbbbb.md" in filenames
    assert "agent-C_cccccccc.md" in filenames


# ── (e) experiment routing ────────────────────────────────────────────────

def test_harvest_experiment_routes_to_experiments_subtree(tmp_path):
    from thinking_harvester import harvest
    projects_root = _stage_fixture_session(tmp_path, "predictor_session", PREDICTOR_SID)
    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="prediction",
        experiment_name="prediction_no_lessons",
        ticker="BURL", quarter="Q4_FY2025",
        session_id=PREDICTOR_SID,
        vault_root=vault_root, projects_root=projects_root,
    )
    exp_dir = vault_root / "BURL" / "events" / "Q4_FY2025" / "experiments" / "prediction_no_lessons"
    assert (exp_dir / "thinking.md").exists(), "experiment thinking.md must route under experiments/"
    # FORK pattern — no subagents/ dir
    assert not (exp_dir / "subagents").exists()
    # Component-level prediction/thinking.md must NOT be created by an experiment call
    assert not (vault_root / "BURL" / "events" / "Q4_FY2025" / "prediction" / "thinking.md").exists()

    content = (exp_dir / "thinking.md").read_text()
    assert "component: prediction" in content
    assert "experiment_name: prediction_no_lessons" in content


# ── (f) idempotency ───────────────────────────────────────────────────────

def test_harvest_idempotent_reharvest(tmp_path):
    from thinking_harvester import harvest
    projects_root = _stage_fixture_session(tmp_path, "learner_session", LEARNER_SID)
    vault_root = tmp_path / "vault"

    harvest(
        thinking_type="learning", ticker="BURL", quarter="Q4_FY2025",
        session_id=LEARNER_SID, vault_root=vault_root, projects_root=projects_root,
    )
    comp_dir = vault_root / "BURL" / "events" / "Q4_FY2025" / "learning"
    first_content = (comp_dir / "thinking.md").read_text()
    first_subagents = sorted(p.name for p in (comp_dir / "subagents").iterdir())

    # Add a stale file that must be cleared on re-harvest
    stale = comp_dir / "subagents" / "stale-file-must-be-cleaned.md"
    stale.write_text("stale")
    assert stale.exists()

    harvest(
        thinking_type="learning", ticker="BURL", quarter="Q4_FY2025",
        session_id=LEARNER_SID, vault_root=vault_root, projects_root=projects_root,
    )
    second_content = (comp_dir / "thinking.md").read_text()
    second_subagents = sorted(p.name for p in (comp_dir / "subagents").iterdir())

    # Idempotency: content is identical MODULO the generated_at timestamp
    # (which is intentionally in frontmatter per plan — wall-clock, per-run).
    import re
    def _strip_generated_at(s: str) -> str:
        return re.sub(r"generated_at: [^\n]+", "generated_at: <stripped>", s)
    assert _strip_generated_at(first_content) == _strip_generated_at(second_content)
    assert first_subagents == second_subagents
    assert not stale.exists(), "re-harvest must clear stale subagent files"


# ── (g) missing session_id → WARNING, no crash, no write ──────────────────

def test_harvest_with_none_session_id_is_warning_not_crash(tmp_path, caplog):
    import logging
    from thinking_harvester import harvest
    vault_root = tmp_path / "vault"
    with caplog.at_level(logging.WARNING):
        harvest(
            thinking_type="prediction", ticker="BURL", quarter="Q4_FY2025",
            session_id=None,  # type: ignore[arg-type]
            vault_root=vault_root, projects_root=tmp_path / "projects",
        )
    assert not (vault_root / "BURL" / "events" / "Q4_FY2025" / "prediction" / "thinking.md").exists()
    assert any("session_id" in rec.message for rec in caplog.records)


# ── (h) predictor FORK produces NO subagents/ dir (explicit negative test) ─

def test_harvest_predictor_fork_no_subagents_dir_explicit(tmp_path):
    from thinking_harvester import harvest
    projects_root = _stage_fixture_session(tmp_path, "predictor_session", PREDICTOR_SID)
    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="prediction", ticker="BURL", quarter="Q4_FY2025",
        session_id=PREDICTOR_SID, vault_root=vault_root, projects_root=projects_root,
    )
    subagents_dir = vault_root / "BURL" / "events" / "Q4_FY2025" / "prediction" / "subagents"
    assert not subagents_dir.exists()


# ── (i) skill-fork dual-signal agreement — no WARNING ─────────────────────

def test_harvest_predictor_skill_fork_dual_signal_no_warning(tmp_path, caplog):
    import logging
    from thinking_harvester import harvest
    projects_root = _stage_fixture_session(tmp_path, "predictor_session", PREDICTOR_SID)
    vault_root = tmp_path / "vault"
    with caplog.at_level(logging.WARNING):
        harvest(
            thinking_type="prediction", ticker="BURL", quarter="Q4_FY2025",
            session_id=PREDICTOR_SID, vault_root=vault_root, projects_root=projects_root,
        )
    mismatch_warnings = [r for r in caplog.records if "skill-fork" in r.message.lower() and "mismatch" in r.message.lower()]
    assert not mismatch_warnings, "real fixture has both signals — no mismatch WARNING expected"


# ── (j) skill-fork dual-signal MISMATCH → WARNING, still proceed ──────────

def test_harvest_skill_fork_dual_signal_mismatch_logs_warning(tmp_path, caplog):
    """Synthetic: meta.json says general-purpose but first-user does NOT say 'Base directory'."""
    import logging
    from thinking_harvester import harvest
    projects_root = tmp_path / "projects"
    sid = "synthetic-mismatch"
    (projects_root / sid / "subagents").mkdir(parents=True)

    # Primary with a Skill tool_use → triggers fork pattern path
    primary = projects_root / f"{sid}.jsonl"
    primary.write_text(json.dumps({
        "type": "assistant", "timestamp": "2026-01-01T00:00:01Z",
        "message": {"content": [
            {"type": "tool_use", "id": "tu-S", "name": "Skill",
             "input": {"skill": "earnings-prediction", "args": ""}}
        ]}
    }) + "\n" + json.dumps({
        "type": "user", "timestamp": "2026-01-01T00:00:02Z",
        "message": {"content": [
            {"type": "tool_result", "tool_use_id": "tu-S",
             "content": [{"type": "text", "text": "done"}]}
        ]},
        "toolUseResult": {"agentId": "ffffffffffffff00", "agentType": None},
    }) + "\n")

    # Subagent: meta.json says general-purpose (signal A = True)
    # but first-user does NOT start with "Base directory for this skill:" (signal B = False)
    sub_jsonl = projects_root / sid / "subagents" / "agent-ffffffffffffff00.jsonl"
    sub_jsonl.write_text(json.dumps({
        "type": "user", "timestamp": "2026-01-01T00:00:03Z",
        "message": {"content": "Some other prompt not starting with the skill marker"},
    }) + "\n")
    meta = projects_root / sid / "subagents" / "agent-ffffffffffffff00.meta.json"
    meta.write_text(json.dumps({"agentType": "general-purpose"}))

    vault_root = tmp_path / "vault"
    with caplog.at_level(logging.WARNING):
        harvest(
            thinking_type="prediction", ticker="TST", quarter="QX",
            session_id=sid, vault_root=vault_root, projects_root=projects_root,
        )
    mismatch_warnings = [r for r in caplog.records if "skill-fork" in r.message.lower()]
    assert mismatch_warnings, "expected a skill-fork signal-mismatch WARNING"
    # Harvest still proceeded (thinking.md exists)
    assert (vault_root / "TST" / "events" / "QX" / "prediction" / "thinking.md").exists()


# ── (k) missing meta.json → fall back to first-user scan, log WARNING ────

def test_harvest_missing_meta_falls_back_to_first_user(tmp_path, caplog):
    import logging
    from thinking_harvester import harvest
    projects_root = _stage_fixture_session(tmp_path, "predictor_session", PREDICTOR_SID)
    # Delete the meta.json to force fallback
    meta_path = projects_root / PREDICTOR_SID / "subagents" / "agent-a9f59960218dbbe88.meta.json"
    assert meta_path.exists()
    meta_path.unlink()
    vault_root = tmp_path / "vault"
    with caplog.at_level(logging.WARNING):
        harvest(
            thinking_type="prediction", ticker="BURL", quarter="Q4_FY2025",
            session_id=PREDICTOR_SID, vault_root=vault_root, projects_root=projects_root,
        )
    # Did not crash — thinking.md written
    assert (vault_root / "BURL" / "events" / "Q4_FY2025" / "prediction" / "thinking.md").exists()
    missing_meta_warnings = [r for r in caplog.records if "meta.json" in r.message.lower()]
    assert missing_meta_warnings


# ── (l) orphan Agent tool_use → WARNING in thinking.md, no subagent file ──

def test_harvest_orphan_agent_tool_use_logs_warning(tmp_path):
    from thinking_harvester import harvest
    projects_root = tmp_path / "projects"
    sid = "synthetic-orphan"
    (projects_root / sid / "subagents").mkdir(parents=True)

    # Primary with 2 Agent calls — only 1 has a matching tool_result
    primary = projects_root / f"{sid}.jsonl"
    primary.write_text("\n".join([
        json.dumps({
            "type": "assistant", "timestamp": "2026-01-01T00:00:01Z",
            "message": {"content": [
                {"type": "tool_use", "id": "tu-1", "name": "Agent",
                 "input": {"subagent_type": "agent-1"}}
            ]}
        }),
        json.dumps({
            "type": "assistant", "timestamp": "2026-01-01T00:00:02Z",
            "message": {"content": [
                {"type": "tool_use", "id": "tu-2-orphan", "name": "Agent",
                 "input": {"subagent_type": "agent-orphan"}}
            ]}
        }),
        json.dumps({
            "type": "user", "timestamp": "2026-01-01T00:00:03Z",
            "message": {"content": [
                {"type": "tool_result", "tool_use_id": "tu-1",
                 "content": [{"type": "text", "text": "ok"}]}
            ]},
            "toolUseResult": {"agentId": "1111111111111111", "agentType": "agent-1"},
        }),
    ]) + "\n")

    # Only 1 subagent file (for tu-1)
    sub = projects_root / sid / "subagents" / "agent-1111111111111111.jsonl"
    sub.write_text(json.dumps({"type": "user", "message": {"content": "hi"}, "timestamp": "2026-01-01T00:00:03Z"}) + "\n")
    meta = projects_root / sid / "subagents" / "agent-1111111111111111.meta.json"
    meta.write_text(json.dumps({"agentType": "agent-1"}))

    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="learning", ticker="TST", quarter="QX",
        session_id=sid, vault_root=vault_root, projects_root=projects_root,
    )
    comp_dir = vault_root / "TST" / "events" / "QX" / "learning"
    thinking_md = comp_dir / "thinking.md"
    content = thinking_md.read_text()
    assert "agent-orphan" in content, "orphan WARNING must be in thinking.md"
    assert "no tool_result" in content or "orphan" in content.lower()

    # Only the 1 non-orphan subagent file should exist
    subagent_files = list((comp_dir / "subagents").iterdir())
    assert len(subagent_files) == 1


# ── (m) fixture-completeness invariant ────────────────────────────────────

def test_fixture_completeness_invariant_jsonl_has_sibling_meta():
    """For every agent-<id>.jsonl in each fixture subagents/ dir,
    a sibling agent-<id>.meta.json must exist.
    """
    for fixture in ("learner_session", "guidance_session", "predictor_session"):
        subagents = FIXTURES / fixture / "subagents"
        assert subagents.is_dir(), f"fixture subagents dir missing: {subagents}"
        for jsonl in subagents.glob("*.jsonl"):
            meta = jsonl.with_suffix(".meta.json")
            assert meta.exists(), f"fixture drift: {jsonl.name} has no sibling .meta.json in {fixture}"
