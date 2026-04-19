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


# ── FORK-with-nested-Agents (latent-bug regression tests) ────────────────

def _make_fork_with_nested_agents(tmp_path: Path, *, flat_layout: bool):
    """Build a synthetic session: worker's primary has Skill tool_use →
    skill-fork → skill-fork spawns 2 Agent subagents.

    ``flat_layout=True`` places nested children as siblings to the skill-fork
    at ``{session}/subagents/agent-{id}.jsonl``. ``flat_layout=False`` nests
    them one level deeper: ``{session}/subagents/{skill_fork_id}/subagents/...``.

    Returns the projects_root path.
    """
    projects_root = tmp_path / "projects"
    sid = "worker-fork-nested"
    sub_dir = projects_root / sid / "subagents"
    sub_dir.mkdir(parents=True)

    SKILL_FORK_ID = "f0" * 8
    AGENT_PRIMARY_ID = "a1" * 8
    AGENT_ENRICH_ID = "a2" * 8

    # Worker primary session: 1 Skill tool_use + matching tool_result
    primary = projects_root / f"{sid}.jsonl"
    primary.write_text("\n".join([
        json.dumps({
            "type": "assistant", "timestamp": "2026-01-01T00:00:01Z",
            "message": {"content": [
                {"type": "tool_use", "id": "tu-S", "name": "Skill",
                 "input": {"skill": "extract", "args": "BURL 8k 0001..."}}
            ]}
        }),
        json.dumps({
            "type": "user", "timestamp": "2026-01-01T00:00:10Z",
            "message": {"content": [
                {"type": "tool_result", "tool_use_id": "tu-S",
                 "content": [{"type": "text", "text": "done"}]}
            ]},
            "toolUseResult": {"agentId": SKILL_FORK_ID, "agentType": None},
        }),
    ]) + "\n")

    # Skill-fork session: first-user Base-directory marker + Agent tool_uses
    # to extraction-primary + extraction-enrichment.
    skill_fork_jsonl = sub_dir / f"agent-{SKILL_FORK_ID}.jsonl"
    skill_fork_jsonl.write_text("\n".join([
        json.dumps({
            "type": "user", "timestamp": "2026-01-01T00:00:02Z",
            "message": {"content": "Base directory for this skill: /home/x/.claude/skills/extract\n..."},
        }),
        json.dumps({
            "type": "assistant", "timestamp": "2026-01-01T00:00:03Z",
            "message": {"content": [
                {"type": "tool_use", "id": "tu-P", "name": "Agent",
                 "input": {"subagent_type": "extraction-primary-agent"}}
            ]}
        }),
        json.dumps({
            "type": "assistant", "timestamp": "2026-01-01T00:00:04Z",
            "message": {"content": [
                {"type": "tool_use", "id": "tu-E", "name": "Agent",
                 "input": {"subagent_type": "extraction-enrichment-agent"}}
            ]}
        }),
        json.dumps({
            "type": "user", "timestamp": "2026-01-01T00:00:06Z",
            "message": {"content": [
                {"type": "tool_result", "tool_use_id": "tu-P",
                 "content": [{"type": "text", "text": "primary done"}]}
            ]},
            "toolUseResult": {"agentId": AGENT_PRIMARY_ID, "agentType": "extraction-primary-agent"},
        }),
        json.dumps({
            "type": "user", "timestamp": "2026-01-01T00:00:07Z",
            "message": {"content": [
                {"type": "tool_result", "tool_use_id": "tu-E",
                 "content": [{"type": "text", "text": "enrich done"}]}
            ]},
            "toolUseResult": {"agentId": AGENT_ENRICH_ID, "agentType": "extraction-enrichment-agent"},
        }),
    ]) + "\n")
    # Skill-fork meta.json → general-purpose (dual-signal detection)
    (sub_dir / f"agent-{SKILL_FORK_ID}.meta.json").write_text(
        json.dumps({"agentType": "general-purpose"})
    )

    # Nested subagent JSONLs — flat or nested layout
    if flat_layout:
        nested_dir = sub_dir
    else:
        nested_dir = sub_dir / SKILL_FORK_ID / "subagents"
        nested_dir.mkdir(parents=True)
    for aid, atype in [(AGENT_PRIMARY_ID, "extraction-primary-agent"),
                        (AGENT_ENRICH_ID, "extraction-enrichment-agent")]:
        (nested_dir / f"agent-{aid}.jsonl").write_text(
            json.dumps({
                "type": "user", "timestamp": "2026-01-01T00:00:05Z",
                "message": {"content": f"Extraction pass for {atype}"},
            }) + "\n"
        )
        (nested_dir / f"agent-{aid}.meta.json").write_text(
            json.dumps({"agentType": atype, "description": f"{atype} pass"})
        )

    return projects_root, sid


def test_fork_with_nested_agents_flat_layout_emits_subagent_files(tmp_path):
    """FORK pattern where primary has Skill tool_use → skill-fork spawns
    Agent subagents at FLAT layout. Harvester must emit subagent files for
    the Agent children even though they're nested inside skill-fork's
    session, not the primary's.
    """
    from thinking_harvester import harvest
    projects_root, sid = _make_fork_with_nested_agents(tmp_path, flat_layout=True)
    vault_root = tmp_path / "vault"

    harvest(
        thinking_type="guidance", ticker="BURL", quarter="Q4_FY2025",
        session_id=sid, vault_root=vault_root, projects_root=projects_root,
    )

    comp_dir = vault_root / "BURL" / "events" / "Q4_FY2025" / "guidance"
    thinking_md = comp_dir / "thinking.md"
    subagents_dir = comp_dir / "subagents"

    assert thinking_md.exists(), "thinking.md must exist for FORK-with-nested-Agents"
    assert subagents_dir.exists(), \
        "FORK-with-nested-Agents MUST emit subagents/ (extraction-primary + enrichment)"
    subagent_files = sorted(p.name for p in subagents_dir.iterdir())
    assert len(subagent_files) == 2, f"expected 2 subagent files, got {subagent_files}"
    assert any("extraction-primary-agent" in n for n in subagent_files)
    assert any("extraction-enrichment-agent" in n for n in subagent_files)


def test_fork_with_nested_agents_nested_layout_recursive_fallback(tmp_path):
    """Same as above but nested children live one level deeper. Harvester
    recursive fallback must locate them via glob.
    """
    from thinking_harvester import harvest
    projects_root, sid = _make_fork_with_nested_agents(tmp_path, flat_layout=False)
    vault_root = tmp_path / "vault"

    harvest(
        thinking_type="guidance", ticker="BURL", quarter="Q4_FY2025",
        session_id=sid, vault_root=vault_root, projects_root=projects_root,
    )

    comp_dir = vault_root / "BURL" / "events" / "Q4_FY2025" / "guidance"
    subagents_dir = comp_dir / "subagents"
    assert subagents_dir.exists(), \
        "FORK-with-nested-Agents (nested layout) must still emit subagents/ via recursive glob"
    assert len(list(subagents_dir.iterdir())) == 2


# ── source_asset / source_id guidance-only params (strict validation) ────

def test_source_asset_requires_thinking_type_guidance(tmp_path):
    from thinking_harvester import harvest
    with pytest.raises(ValueError, match="guidance"):
        harvest(
            thinking_type="prediction", ticker="X", quarter="Q",
            session_id="sid", source_asset="8k",
            vault_root=tmp_path / "v", projects_root=tmp_path / "p",
        )


def test_source_id_requires_thinking_type_guidance(tmp_path):
    from thinking_harvester import harvest
    with pytest.raises(ValueError, match="guidance"):
        harvest(
            thinking_type="learning", ticker="X", quarter="Q",
            session_id="sid", source_id="some-id",
            vault_root=tmp_path / "v", projects_root=tmp_path / "p",
        )


def test_source_asset_whitelist_rejects_unknown(tmp_path):
    from thinking_harvester import harvest
    with pytest.raises(ValueError, match="one of"):
        harvest(
            thinking_type="guidance", ticker="X", quarter="Q",
            session_id="sid", source_asset="9k",
            vault_root=tmp_path / "v", projects_root=tmp_path / "p",
        )


def test_source_id_without_source_asset_rejected(tmp_path):
    from thinking_harvester import harvest
    with pytest.raises(ValueError, match="both-or-neither|complete provenance|requires"):
        harvest(
            thinking_type="guidance", ticker="X", quarter="Q",
            session_id="sid",
            source_id="0001234-56-789",   # source_asset missing
            vault_root=tmp_path / "v", projects_root=tmp_path / "p",
        )


def test_source_asset_whitelist_accepts_all_five(tmp_path):
    """All 5 valid assets must pass validation (even if harvest is skipped for
    missing session)."""
    from thinking_harvester import harvest
    for valid in ("8k", "10q", "10k", "transcript", "news"):
        # No session so harvest returns early — but validation must not raise.
        harvest(
            thinking_type="guidance", ticker="X", quarter="Q",
            session_id="does-not-exist",
            source_asset=valid,
            vault_root=tmp_path / f"v-{valid}",
            projects_root=tmp_path / f"p-{valid}",
        )  # must not raise


def test_guidance_per_asset_shards_filename_to_thinking_suffix(tmp_path):
    """When source_asset is set on guidance, thinking.md becomes thinking_{asset}.md
    and subagents/ becomes subagents_{asset}/.
    """
    from thinking_harvester import harvest
    projects_root, sid = _make_fork_with_nested_agents(tmp_path, flat_layout=True)
    vault_root = tmp_path / "vault"

    harvest(
        thinking_type="guidance", ticker="BURL", quarter="Q4_FY2025",
        session_id=sid,
        source_asset="8k",
        source_id="0001193125-26-092488",
        vault_root=vault_root, projects_root=projects_root,
    )
    comp_dir = vault_root / "BURL" / "events" / "Q4_FY2025" / "guidance"
    # Sharded names
    assert (comp_dir / "thinking_8k.md").exists()
    assert (comp_dir / "subagents_8k").is_dir()
    # Default names must NOT exist
    assert not (comp_dir / "thinking.md").exists()
    assert not (comp_dir / "subagents").exists()
    # Subagent files under the sharded dir
    subagent_files = list((comp_dir / "subagents_8k").iterdir())
    assert len(subagent_files) == 2


def test_guidance_frontmatter_includes_source_asset_and_source_id(tmp_path):
    from thinking_harvester import harvest
    projects_root, sid = _make_fork_with_nested_agents(tmp_path, flat_layout=True)
    vault_root = tmp_path / "vault"

    harvest(
        thinking_type="guidance", ticker="BURL", quarter="Q4_FY2025",
        session_id=sid,
        source_asset="8k",
        source_id="0001193125-26-092488",
        vault_root=vault_root, projects_root=projects_root,
    )
    md = (vault_root / "BURL" / "events" / "Q4_FY2025" / "guidance" / "thinking_8k.md").read_text()
    assert "source_asset: 8k" in md
    assert "source_id: 0001193125-26-092488" in md


def test_guidance_per_asset_coexist_on_same_quarter(tmp_path):
    """Two guidance extractions on the same quarter with different source_assets
    should coexist as separate files (Option B — per-asset subfiles)."""
    from thinking_harvester import harvest
    projects_root, sid = _make_fork_with_nested_agents(tmp_path, flat_layout=True)
    vault_root = tmp_path / "vault"

    # First extraction: 8-K
    harvest(
        thinking_type="guidance", ticker="BURL", quarter="Q4_FY2025",
        session_id=sid,
        source_asset="8k", source_id="0001193125-26-092488",
        vault_root=vault_root, projects_root=projects_root,
    )
    # Second extraction: transcript (same quarter, different source)
    # We reuse the fixture but with different asset — no overwrite expected.
    harvest(
        thinking_type="guidance", ticker="BURL", quarter="Q4_FY2025",
        session_id=sid,
        source_asset="transcript", source_id="BURL_2026-03-05T09.00",
        vault_root=vault_root, projects_root=projects_root,
    )
    comp_dir = vault_root / "BURL" / "events" / "Q4_FY2025" / "guidance"
    # Both files exist, no overwrite
    assert (comp_dir / "thinking_8k.md").exists()
    assert (comp_dir / "thinking_transcript.md").exists()
    assert (comp_dir / "subagents_8k").is_dir()
    assert (comp_dir / "subagents_transcript").is_dir()


def test_guidance_without_source_asset_still_uses_default_shape(tmp_path):
    """Backward-compat: guidance call without source_asset produces default
    thinking.md + subagents/ (matches CLI-harvest invocation like our earlier
    BURL fixture demo)."""
    from thinking_harvester import harvest
    projects_root, sid = _make_fork_with_nested_agents(tmp_path, flat_layout=True)
    vault_root = tmp_path / "vault"

    harvest(
        thinking_type="guidance", ticker="BURL", quarter="Q4_FY2025",
        session_id=sid,
        vault_root=vault_root, projects_root=projects_root,
    )
    comp_dir = vault_root / "BURL" / "events" / "Q4_FY2025" / "guidance"
    assert (comp_dir / "thinking.md").exists()
    assert (comp_dir / "subagents").is_dir()


def test_prediction_and_learning_unchanged_by_source_asset_addition(tmp_path):
    """Changing harvester signature must not affect prediction/learning shape."""
    from thinking_harvester import harvest
    projects_root = _stage_fixture_session(tmp_path, "learner_session", LEARNER_SID)
    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="learning", ticker="BURL", quarter="Q4_FY2025",
        session_id=LEARNER_SID,
        vault_root=vault_root, projects_root=projects_root,
    )
    comp = vault_root / "BURL" / "events" / "Q4_FY2025" / "learning"
    assert (comp / "thinking.md").exists()
    assert (comp / "subagents").is_dir()
    # No sharded files
    assert not list(comp.glob("thinking_*.md"))
    assert not list(comp.glob("subagents_*"))


# ── Heading-downgrade (content-authored markdown must not pollute outline) ──

def test_downgrade_headings_shifts_h1_h2_h3_by_three(tmp_path):
    """Content-authored H1/H2/H3 collides with the harvester's structural
    outline in Obsidian. The harvester must shift them down by 3 (matching
    .claude/hooks/obsidian_capture.py::_downgrade_headings) so structural
    H1-H3 remain unambiguous."""
    from thinking_harvester import _downgrade_headings
    src = "# Top\n## Sub\n### Deep\nplain\n#### Already4\n##### Already5"
    out = _downgrade_headings(src)
    assert out == "#### Top\n##### Sub\n###### Deep\nplain\n#### Already4\n##### Already5"


def test_harvested_thinking_md_no_content_authored_h1_h2_h3_headings(tmp_path):
    """End-to-end regression: construct a minimal fixture where the assistant's
    text block contains an H2 heading. After harvest, thinking.md must not
    contain any H1/H2/H3 headings BEYOND the harvester's own structural ones.

    Structural H1-H3 the harvester emits: H1 title, H2 section (1-2),
    H3 block labels (💭/📝). Any additional top-level (<=H3) heading in the
    final file indicates pollution from content — the downgrade failed.
    """
    import json
    from thinking_harvester import harvest

    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    session_id = "11111111-2222-3333-4444-555555555555"
    jsonl = projects_root / f"{session_id}.jsonl"

    # Minimal session: one assistant text block whose content contains an H2.
    # Plus a second assistant turn with stop_reason=end_turn so the session
    # is "complete" shape-wise (harvester itself doesn't check this, but good hygiene).
    jsonl.write_text("\n".join([
        json.dumps({
            "type": "assistant",
            "message": {"content": [{
                "type": "text",
                "text": "## Step 1: Do the thing\nparagraph under it\n### Sub-step\nmore text",
            }], "stop_reason": "end_turn"},
            "timestamp": "2026-01-01T00:00:00Z",
        }),
    ]) + "\n")

    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="guidance", ticker="TEST", quarter="Q1_FY2025",
        session_id=session_id, source_asset="transcript",
        source_id="TEST_src",
        vault_root=vault_root, projects_root=projects_root,
    )
    out = (vault_root / "TEST" / "events" / "Q1_FY2025" / "guidance"
           / "thinking_transcript.md").read_text(encoding="utf-8")

    # Post-fix: content-authored H2/H3 must be downgraded → become H5/H6.
    # Use line-anchored regex — plain "in" substring-matches "##### X" for "## X".
    import re as _re
    assert _re.search(r"^## Step 1: Do the thing$", out, _re.MULTILINE) is None, (
        "content-authored H2 leaked into the harvester outline"
    )
    assert _re.search(r"^### Sub-step$", out, _re.MULTILINE) is None, (
        "content-authored H3 leaked into the harvester outline"
    )
    # Must still be rendered — just at a deeper level (shifted +3)
    assert _re.search(r"^##### Step 1: Do the thing$", out, _re.MULTILINE)
    assert _re.search(r"^###### Sub-step$", out, _re.MULTILINE)

    # Structural headings must still be intact
    assert _re.search(r"^## Primary session reasoning$", out, _re.MULTILINE)
    assert "### 📝 Text" in out


def test_subagent_trace_text_headings_downgraded(tmp_path):
    """Subagent trace must also downgrade content headings in both the prompt
    and the transcript text blocks."""
    import json
    from thinking_harvester import harvest

    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    session_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    # Primary session: one assistant with Agent spawn
    primary = projects_root / f"{session_id}.jsonl"
    primary.write_text(
        json.dumps({
            "type": "assistant",
            "message": {"content": [{
                "type": "tool_use", "id": "tu_sub", "name": "Agent",
                "input": {"subagent_type": "test-sub", "description": "x",
                          "prompt": "## Heading in prompt"},
            }], "stop_reason": "tool_use"},
            "timestamp": "2026-01-01T00:00:00Z",
        }) + "\n"
        + json.dumps({
            "type": "user",
            "message": {"content": [{"type": "tool_result", "tool_use_id": "tu_sub", "content": "ok"}]},
            "timestamp": "2026-01-01T00:00:01Z",
            "toolUseResult": {"agentId": "a1b2c3d4e5f67890a"},
        }) + "\n"
    )

    # Subagent session: prompt + text with headings
    sub_dir = projects_root / session_id / "subagents"
    sub_dir.mkdir(parents=True)
    sub_jsonl = sub_dir / "agent-a1b2c3d4e5f67890a.jsonl"
    sub_jsonl.write_text(
        json.dumps({
            "type": "user",
            "message": {"content": "## Prompt heading\nsome text\n### Sub"},
            "timestamp": "2026-01-01T00:00:00.100Z",
        }) + "\n"
        + json.dumps({
            "type": "assistant",
            "message": {"content": [{
                "type": "text", "text": "## Result heading\nfinal",
            }], "stop_reason": "end_turn"},
            "timestamp": "2026-01-01T00:00:00.200Z",
        }) + "\n"
    )

    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="guidance", ticker="TEST", quarter="Q1_FY2025",
        session_id=session_id, source_asset="transcript",
        source_id="TEST_src2",
        vault_root=vault_root, projects_root=projects_root,
    )
    subs_dir = vault_root / "TEST" / "events" / "Q1_FY2025" / "guidance" / "subagents_transcript"
    files = list(subs_dir.glob("*.md"))
    assert len(files) == 1
    out = files[0].read_text(encoding="utf-8")

    # Content headings must be downgraded (line-anchored to avoid substring match)
    import re as _re
    assert _re.search(r"^## Prompt heading$", out, _re.MULTILINE) is None
    assert _re.search(r"^## Result heading$", out, _re.MULTILINE) is None
    assert _re.search(r"^##### Prompt heading$", out, _re.MULTILINE)
    assert _re.search(r"^##### Result heading$", out, _re.MULTILINE)
    # Structural headings intact
    assert _re.search(r"^## Prompt$", out, _re.MULTILINE)
    assert _re.search(r"^## Transcript$", out, _re.MULTILINE)


# ── Safe truncation — closing an open ``` fence at the cut point ──────────

def test_truncate_safe_fence_closes_unbalanced_fence():
    from thinking_harvester import _truncate_safe_fence
    # Text opens a fence, contains content, but the cut happens before close
    src = "before\n```python\nx = 1\n" + "y" * 5000 + "\n```\nafter"
    out = _truncate_safe_fence(src, 100)
    assert len(out) == 100 + len("\n```"), (
        f"expected limit+4 bytes, got {len(out)}; out={out!r}"
    )
    assert out.count("```") % 2 == 0, f"fence still unbalanced: {out!r}"
    assert out.endswith("\n```"), f"missing trailing close: {out[-10:]!r}"


def test_truncate_safe_fence_leaves_balanced_text_alone():
    from thinking_harvester import _truncate_safe_fence
    src = "hello\n```\nx\n```\nworld"
    # Truncate to a length that keeps both fences paired
    out = _truncate_safe_fence(src, len(src))
    assert out == src  # no truncation needed
    out_short = _truncate_safe_fence(src, 17)  # cuts at 'world' line area
    assert out_short.count("```") % 2 == 0


def test_truncate_safe_fence_short_text_untouched():
    from thinking_harvester import _truncate_safe_fence
    assert _truncate_safe_fence("short", 1000) == "short"
    assert _truncate_safe_fence("", 1000) == ""


def test_subagent_trace_truncation_preserves_fence_balance(tmp_path):
    """End-to-end: a subagent text that opens a code fence near the 4000-char
    truncation boundary must not leak an unclosed ``` into the rendered file.
    This was the AVGO primary subagent trace bug (line 98: ```cypher opened
    but truncation cut mid-block → rest of note rendered as code)."""
    import json
    from thinking_harvester import harvest

    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    session_id = "ffff1111-2222-3333-4444-555555555555"

    primary = projects_root / f"{session_id}.jsonl"
    primary.write_text(
        json.dumps({
            "type": "assistant",
            "message": {"content": [{
                "type": "tool_use", "id": "tu_fence", "name": "Agent",
                "input": {"subagent_type": "test-sub", "description": "x"},
            }], "stop_reason": "tool_use"},
            "timestamp": "2026-01-01T00:00:00Z",
        }) + "\n"
        + json.dumps({
            "type": "user",
            "message": {"content": [{"type": "tool_result", "tool_use_id": "tu_fence", "content": "ok"}]},
            "timestamp": "2026-01-01T00:00:01Z",
            "toolUseResult": {"agentId": "ab1234567890abcde"},
        }) + "\n"
    )

    sub_dir = projects_root / session_id / "subagents"
    sub_dir.mkdir(parents=True)
    sub_jsonl = sub_dir / "agent-ab1234567890abcde.jsonl"
    # Build a text > 4000 chars that opens ```cypher ~3000 in, never closes
    # within 4000 chars.
    padding = "prose " * 500  # ~3000 chars
    body = padding + "\n```cypher\nMATCH (n) RETURN n\n" + "x" * 5000 + "\n```\ntail"
    sub_jsonl.write_text(
        json.dumps({
            "type": "user",
            "message": {"content": "ignore"},
            "timestamp": "2026-01-01T00:00:00.100Z",
        }) + "\n"
        + json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": body}], "stop_reason": "end_turn"},
            "timestamp": "2026-01-01T00:00:00.200Z",
        }) + "\n"
    )

    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="guidance", ticker="TEST", quarter="Q1_FY2025",
        session_id=session_id, source_asset="transcript",
        source_id="TEST_fence",
        vault_root=vault_root, projects_root=projects_root,
    )
    files = list((vault_root / "TEST" / "events" / "Q1_FY2025" / "guidance"
                  / "subagents_transcript").glob("*.md"))
    assert len(files) == 1
    out = files[0].read_text(encoding="utf-8")
    assert out.count("```") % 2 == 0, (
        f"unbalanced fences after truncation — got count={out.count('```')}"
    )


def test_tool_result_preview_closes_unbalanced_fence(tmp_path):
    """Tool_result content is truncated at 300 chars in render_subagent_trace.
    If the preview opens a ``` code fence but is cut before close, the fix
    must append a trailing ```.
    Real bug case (AVGO primary subagent trace): a Read tool_result previewed
    file content that opened ```cypher at char ~100 and never closed within
    300 chars — broke all downstream rendering."""
    import json
    from thinking_harvester import harvest

    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    session_id = "cccc1111-2222-3333-4444-555555555555"

    primary = projects_root / f"{session_id}.jsonl"
    primary.write_text(
        json.dumps({
            "type": "assistant",
            "message": {"content": [{
                "type": "tool_use", "id": "tu_preview", "name": "Agent",
                "input": {"subagent_type": "test-sub", "description": "x"},
            }], "stop_reason": "tool_use"},
            "timestamp": "2026-01-01T00:00:00Z",
        }) + "\n"
        + json.dumps({
            "type": "user",
            "message": {"content": [{"type": "tool_result", "tool_use_id": "tu_preview", "content": "ok"}]},
            "timestamp": "2026-01-01T00:00:01Z",
            "toolUseResult": {"agentId": "cd9876543210cdefg"},
        }) + "\n"
    )

    sub_dir = projects_root / session_id / "subagents"
    sub_dir.mkdir(parents=True)
    sub_jsonl = sub_dir / "agent-cd9876543210cdefg.jsonl"
    # Tool_result content: opens ```cypher near char 100, never closes within 300
    fence_content = "header text here " * 5 + "\n```cypher\n" + "MATCH (n) RETURN n\n" * 50
    sub_jsonl.write_text(
        json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "id": "inner_tu", "name": "Read", "input": {}}], "stop_reason": "tool_use"},
            "timestamp": "2026-01-01T00:00:00.100Z",
        }) + "\n"
        + json.dumps({
            "type": "user",
            "message": {"content": [{"type": "tool_result", "tool_use_id": "inner_tu", "content": fence_content}]},
            "timestamp": "2026-01-01T00:00:00.200Z",
        }) + "\n"
        + json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "done"}], "stop_reason": "end_turn"},
            "timestamp": "2026-01-01T00:00:00.300Z",
        }) + "\n"
    )

    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="guidance", ticker="TEST", quarter="Q1_FY2025",
        session_id=session_id, source_asset="transcript",
        source_id="TEST_preview",
        vault_root=vault_root, projects_root=projects_root,
    )
    files = list((vault_root / "TEST" / "events" / "Q1_FY2025" / "guidance"
                  / "subagents_transcript").glob("*.md"))
    assert len(files) == 1
    out = files[0].read_text(encoding="utf-8")
    assert out.count("```") % 2 == 0, (
        f"tool_result preview leaked unclosed ``` — count={out.count('```')}"
    )


# ── Subagent trace thinking coverage (frontmatter + redacted rendering) ───

def test_subagent_trace_frontmatter_reports_thinking_metrics(tmp_path):
    """Subagent frontmatter must include thinking_blocks, thinking_chars, and
    redacted_thinking_blocks. Prior version only reported text_chars + tool_use_count
    even though ~51% of real subagent JSONLs contain thinking content
    (measured 2026-04-18 across 10k subagent sessions)."""
    import json
    from thinking_harvester import harvest

    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    session_id = "dddd1111-2222-3333-4444-555555555555"

    # Primary session: one Agent spawn
    primary = projects_root / f"{session_id}.jsonl"
    primary.write_text(
        json.dumps({
            "type": "assistant",
            "message": {"content": [{
                "type": "tool_use", "id": "tu1", "name": "Agent",
                "input": {"subagent_type": "test-sub", "description": "x"},
            }], "stop_reason": "tool_use"},
            "timestamp": "2026-01-01T00:00:00Z",
        }) + "\n"
        + json.dumps({
            "type": "user",
            "message": {"content": [{"type": "tool_result", "tool_use_id": "tu1", "content": "ok"}]},
            "timestamp": "2026-01-01T00:00:01Z",
            "toolUseResult": {"agentId": "e1234567890abcdef"},
        }) + "\n"
    )

    # Subagent session: 2 visible thinking blocks (total 123 chars) + 1 redacted
    sub_dir = projects_root / session_id / "subagents"
    sub_dir.mkdir(parents=True)
    sub_jsonl = sub_dir / "agent-e1234567890abcdef.jsonl"
    sub_jsonl.write_text(
        json.dumps({
            "type": "assistant",
            "message": {"content": [
                {"type": "thinking", "thinking": "first block " + "x" * 50},  # 62 chars
                {"type": "thinking", "thinking": "", "signature": "sig123"},   # redacted
                {"type": "thinking", "thinking": "second block " + "y" * 48}, # 61 chars
            ], "stop_reason": "end_turn"},
            "timestamp": "2026-01-01T00:00:00.100Z",
        }) + "\n"
    )

    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="guidance", ticker="TEST", quarter="Q1_FY2025",
        session_id=session_id, source_asset="transcript",
        source_id="TEST_thinking",
        vault_root=vault_root, projects_root=projects_root,
    )
    files = list((vault_root / "TEST" / "events" / "Q1_FY2025" / "guidance"
                  / "subagents_transcript").glob("*.md"))
    assert len(files) == 1
    out = files[0].read_text(encoding="utf-8")
    # Frontmatter must include thinking metrics
    assert "thinking_blocks: 2" in out, f"frontmatter missing/wrong: {out[:500]}"
    assert "thinking_chars: 123" in out
    assert "redacted_thinking_blocks: 1" in out
    # Body must include both visible thinking blocks and the redacted marker
    assert out.count("💭 Thinking") == 2
    assert "🔒" in out
    assert "content redacted (signed)" in out


def test_subagent_trace_zero_thinking_still_reports_counts(tmp_path):
    """Subagents with NO thinking (typical for data sub-agents) still get
    thinking_blocks: 0 / thinking_chars: 0 fields — never missing."""
    import json
    from thinking_harvester import harvest

    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    session_id = "eeee1111-2222-3333-4444-555555555555"

    primary = projects_root / f"{session_id}.jsonl"
    primary.write_text(
        json.dumps({
            "type": "assistant",
            "message": {"content": [{
                "type": "tool_use", "id": "tu1", "name": "Agent",
                "input": {"subagent_type": "tool-only", "description": "x"},
            }], "stop_reason": "tool_use"},
            "timestamp": "2026-01-01T00:00:00Z",
        }) + "\n"
        + json.dumps({
            "type": "user",
            "message": {"content": [{"type": "tool_result", "tool_use_id": "tu1", "content": "ok"}]},
            "timestamp": "2026-01-01T00:00:01Z",
            "toolUseResult": {"agentId": "ff111111111111111"},
        }) + "\n"
    )

    sub_dir = projects_root / session_id / "subagents"
    sub_dir.mkdir(parents=True)
    sub_jsonl = sub_dir / "agent-ff111111111111111.jsonl"
    sub_jsonl.write_text(
        json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "just text, no thinking"}], "stop_reason": "end_turn"},
            "timestamp": "2026-01-01T00:00:00.100Z",
        }) + "\n"
    )

    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="guidance", ticker="TEST", quarter="Q1_FY2025",
        session_id=session_id, source_asset="transcript",
        source_id="TEST_empty",
        vault_root=vault_root, projects_root=projects_root,
    )
    files = list((vault_root / "TEST" / "events" / "Q1_FY2025" / "guidance"
                  / "subagents_transcript").glob("*.md"))
    assert len(files) == 1
    out = files[0].read_text(encoding="utf-8")
    assert "thinking_blocks: 0" in out
    assert "thinking_chars: 0" in out
    assert "redacted_thinking_blocks: 0" in out


# ── First-user prompt rendering in primary thinking.md ─────────────────────

def test_primary_thinking_md_renders_first_user_prompt(tmp_path):
    """Primary thinking.md must include a '## Prompt' section containing the
    original user-invoked command (e.g., '/extract AVGO transcript ...') so
    reviewers can see what was asked. Prior behaviour dropped the prompt
    entirely from the thinking.md output."""
    import json
    from thinking_harvester import harvest

    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    session_id = "11112222-3333-4444-5555-666666666666"
    primary = projects_root / f"{session_id}.jsonl"
    prompt_text = "/extract AVGO transcript AVGO_2023-03-02T17.00 TYPE=guidance MODE=write"
    primary.write_text(
        json.dumps({
            "type": "user",
            "message": {"content": prompt_text},
            "timestamp": "2026-01-01T00:00:00Z",
        }) + "\n"
        + json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "done"}], "stop_reason": "end_turn"},
            "timestamp": "2026-01-01T00:00:01Z",
        }) + "\n"
    )

    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="guidance", ticker="AVGO", quarter="Q1_FY2023",
        session_id=session_id, source_asset="transcript",
        source_id="AVGO_2023-03-02T17.00",
        vault_root=vault_root, projects_root=projects_root,
    )
    out = (vault_root / "AVGO" / "events" / "Q1_FY2023" / "guidance"
           / "thinking_transcript.md").read_text(encoding="utf-8")
    import re as _re
    assert _re.search(r"^## Prompt$", out, _re.MULTILINE), (
        "primary thinking.md missing structural '## Prompt' section"
    )
    assert prompt_text in out, (
        "primary thinking.md did not render the original user command"
    )


def test_primary_thinking_md_list_form_user_content_rendered(tmp_path):
    """First-user message may be list-form with text blocks (some Agent tool
    inputs). Helper must extract the first text item as the prompt."""
    import json
    from thinking_harvester import harvest

    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    session_id = "22223333-4444-5555-6666-777777777777"
    primary = projects_root / f"{session_id}.jsonl"
    primary.write_text(
        json.dumps({
            "type": "user",
            "message": {"content": [
                {"type": "text", "text": "listform prompt inside"},
                {"type": "text", "text": "trailing ignored"},
            ]},
            "timestamp": "2026-01-01T00:00:00Z",
        }) + "\n"
        + json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "done"}], "stop_reason": "end_turn"},
            "timestamp": "2026-01-01T00:00:01Z",
        }) + "\n"
    )

    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="guidance", ticker="TEST", quarter="Q1_FY2025",
        session_id=session_id, source_asset="transcript",
        source_id="TEST_listform",
        vault_root=vault_root, projects_root=projects_root,
    )
    out = (vault_root / "TEST" / "events" / "Q1_FY2025" / "guidance"
           / "thinking_transcript.md").read_text(encoding="utf-8")
    assert "listform prompt inside" in out


def test_primary_thinking_md_no_user_prompt_section_omitted(tmp_path):
    """If the primary has no user entry (edge case), no Prompt section should
    be emitted — avoids printing an empty block."""
    import json
    from thinking_harvester import harvest

    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    session_id = "33334444-5555-6666-7777-888888888888"
    primary = projects_root / f"{session_id}.jsonl"
    primary.write_text(
        json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "solo assistant"}], "stop_reason": "end_turn"},
            "timestamp": "2026-01-01T00:00:00Z",
        }) + "\n"
    )

    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="guidance", ticker="TEST", quarter="Q1_FY2025",
        session_id=session_id, source_asset="transcript",
        source_id="TEST_nouser",
        vault_root=vault_root, projects_root=projects_root,
    )
    out = (vault_root / "TEST" / "events" / "Q1_FY2025" / "guidance"
           / "thinking_transcript.md").read_text(encoding="utf-8")
    import re as _re
    assert _re.search(r"^## Prompt$", out, _re.MULTILINE) is None


# ── FORK-aware summary + text_chars/text_blocks frontmatter (Apr 19) ──────
# Fixes the "Primary thinking: 0 blocks, 0 chars" top-line bug on FORK
# predictions where the skill-fork carries the actual reasoning (~9k chars
# of text in real BURL Q3/Q4 runs).
#
# Scope rules (locked):
#   * text_chars / text_blocks — additive frontmatter on ALL patterns, scoped
#     via the same content_blocks selector the harvester already uses for
#     thinking_chars (primary-only for EMBED; primary + skill_fork for FORK
#     when skill_fork_blocks was loaded).
#   * Body summary line — only FORK-with-skill-fork-loaded rewords to
#     "Reasoning (primary + skill-fork): …". EMBED and FORK-with-no-skill-
#     fork keep the existing "Primary thinking: …" wording verbatim.
#   * Redacted count semantics are UNCHANGED (primary-only). FORK summary
#     labels it "Primary redacted:" so the scope is explicit in the
#     otherwise merged-scope sentence.


def test_fork_summary_reports_combined_reasoning_and_primary_redacted(tmp_path):
    """FORK with skill-fork loaded: summary line uses
    'Reasoning (primary + skill-fork): N thinking (X chars), N text (Y chars).
    Primary redacted: Z. Data subagents: N.'"""
    from thinking_harvester import harvest
    projects_root = _stage_fixture_session(tmp_path, "predictor_session", PREDICTOR_SID)
    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="prediction", ticker="BURL", quarter="Q4_FY2025",
        session_id=PREDICTOR_SID, vault_root=vault_root, projects_root=projects_root,
    )
    out = (vault_root / "BURL" / "events" / "Q4_FY2025" / "prediction"
           / "thinking.md").read_text(encoding="utf-8")
    # New FORK wording present
    assert "Reasoning (primary + skill-fork):" in out, \
        "FORK summary must label scope as 'primary + skill-fork'"
    assert "Primary redacted:" in out, \
        "FORK summary must label redacted scope explicitly (still primary-only)"
    # Old wording must be gone for this pattern
    assert "Primary thinking:" not in out, \
        "FORK summary must no longer use the misleading 'Primary thinking:' label"


def test_embed_visible_summary_wording_unchanged(tmp_path):
    """EMBED-visible (learner) — summary line must keep the existing
    'Primary thinking: N blocks, N chars. Redacted: N. Data subagents: N.'
    wording. No churn on EMBED."""
    from thinking_harvester import harvest
    projects_root = _stage_fixture_session(tmp_path, "learner_session", LEARNER_SID)
    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="learning", ticker="BURL", quarter="Q4_FY2025",
        session_id=LEARNER_SID, vault_root=vault_root, projects_root=projects_root,
    )
    out = (vault_root / "BURL" / "events" / "Q4_FY2025" / "learning"
           / "thinking.md").read_text(encoding="utf-8")
    # Existing wording preserved (line-anchored substring)
    assert "Primary thinking: 6 blocks, 17,682 chars." in out
    assert "Redacted: 0." in out
    # Must NOT get the FORK wording
    assert "Reasoning (primary + skill-fork):" not in out
    assert "Primary redacted:" not in out


def test_embed_redacted_summary_wording_unchanged(tmp_path):
    """EMBED-redacted (guidance) — summary line must keep existing 'Primary
    thinking: …' wording. Thinking count is 0 here because all thinking was
    redacted; that's accurate, not a bug to rewrite."""
    from thinking_harvester import harvest
    projects_root = _stage_fixture_session(tmp_path, "guidance_session", GUIDANCE_SID)
    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="guidance", ticker="BURL", quarter="Q4_FY2025",
        session_id=GUIDANCE_SID, vault_root=vault_root, projects_root=projects_root,
    )
    out = (vault_root / "BURL" / "events" / "Q4_FY2025" / "guidance"
           / "thinking.md").read_text(encoding="utf-8")
    assert "Primary thinking:" in out
    assert "Redacted: 4." in out
    assert "Reasoning (primary + skill-fork):" not in out


def test_frontmatter_text_chars_and_text_blocks_present_all_patterns(tmp_path):
    """text_blocks + text_chars must appear in the frontmatter of all 3
    patterns — pure additive field, Dataview-queryable."""
    from thinking_harvester import harvest

    cases = [
        ("learner_session", LEARNER_SID, "learning", "thinking.md"),
        ("guidance_session", GUIDANCE_SID, "guidance", "thinking.md"),
        ("predictor_session", PREDICTOR_SID, "prediction", "thinking.md"),
    ]
    for fixture, sid, ttype, fname in cases:
        sub_tmp = tmp_path / ttype
        sub_tmp.mkdir()
        projects_root = _stage_fixture_session(sub_tmp, fixture, sid)
        vault_root = sub_tmp / "vault"
        harvest(
            thinking_type=ttype, ticker="BURL", quarter="Q4_FY2025",
            session_id=sid, vault_root=vault_root, projects_root=projects_root,
        )
        out = (vault_root / "BURL" / "events" / "Q4_FY2025" / ttype / fname).read_text()
        assert "\ntext_blocks: " in out, f"{ttype}: frontmatter missing text_blocks"
        assert "\ntext_chars: " in out, f"{ttype}: frontmatter missing text_chars"


def test_frontmatter_text_chars_equals_content_blocks_text_sum_fork(tmp_path):
    """text_chars for FORK equals sum of len(text) across primary + skill-fork
    (the same content_blocks merge rule thinking_chars uses)."""
    from thinking_harvester import harvest
    from thinking_blocks import parse_session_blocks

    projects_root = _stage_fixture_session(tmp_path, "predictor_session", PREDICTOR_SID)
    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="prediction", ticker="BURL", quarter="Q4_FY2025",
        session_id=PREDICTOR_SID, vault_root=vault_root, projects_root=projects_root,
    )
    out = (vault_root / "BURL" / "events" / "Q4_FY2025" / "prediction"
           / "thinking.md").read_text(encoding="utf-8")

    # Compute expected: primary text + skill-fork text (the skill-fork is
    # detected via dual-signal on the one subagent JSONL in this fixture).
    primary = parse_session_blocks(projects_root / f"{PREDICTOR_SID}.jsonl")
    sub_root = projects_root / PREDICTOR_SID / "subagents"
    skill_fork_jsonl = next(sub_root.glob("agent-*.jsonl"))
    fork = parse_session_blocks(skill_fork_jsonl)
    expected_text_chars = sum(len(b["content"]) for b in primary + fork if b["kind"] == "text")
    expected_text_blocks = sum(1 for b in primary + fork if b["kind"] == "text")

    import re as _re
    m_chars = _re.search(r"^text_chars: (\d+)$", out, _re.MULTILINE)
    m_blocks = _re.search(r"^text_blocks: (\d+)$", out, _re.MULTILINE)
    assert m_chars, f"text_chars frontmatter line missing: {out[:800]!r}"
    assert m_blocks, f"text_blocks frontmatter line missing: {out[:800]!r}"
    assert int(m_chars.group(1)) == expected_text_chars, (
        f"FORK text_chars expected {expected_text_chars}, got {m_chars.group(1)}"
    )
    assert int(m_blocks.group(1)) == expected_text_blocks


def test_frontmatter_text_chars_equals_primary_only_sum_embed(tmp_path):
    """text_chars for EMBED-visible equals sum of len(text) across primary
    only (no skill-fork to merge)."""
    from thinking_harvester import harvest
    from thinking_blocks import parse_session_blocks
    projects_root = _stage_fixture_session(tmp_path, "learner_session", LEARNER_SID)
    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="learning", ticker="BURL", quarter="Q4_FY2025",
        session_id=LEARNER_SID, vault_root=vault_root, projects_root=projects_root,
    )
    out = (vault_root / "BURL" / "events" / "Q4_FY2025" / "learning"
           / "thinking.md").read_text(encoding="utf-8")
    primary = parse_session_blocks(projects_root / f"{LEARNER_SID}.jsonl")
    expected = sum(len(b["content"]) for b in primary if b["kind"] == "text")
    import re as _re
    m = _re.search(r"^text_chars: (\d+)$", out, _re.MULTILINE)
    assert m and int(m.group(1)) == expected, f"expected {expected}, got {m and m.group(1)}"


def test_frontmatter_existing_values_unchanged_scope_lock(tmp_path):
    """REGRESSION LOCK: thinking_chars / thinking_blocks / redacted_thinking_blocks
    must keep their existing scope rules after the text_* addition.
      * thinking_chars uses content_blocks scope (same as before the change)
      * redacted_thinking_blocks stays primary-only scope (unchanged)
    Derives expected values by construction from the fixtures — no snapshot
    dependency."""
    from thinking_harvester import harvest
    from thinking_blocks import parse_session_blocks

    # EMBED-visible learner
    projects_root = _stage_fixture_session(tmp_path / "a", "learner_session", LEARNER_SID)
    vault_root = tmp_path / "a" / "v"
    harvest(thinking_type="learning", ticker="BURL", quarter="Q4_FY2025",
            session_id=LEARNER_SID, vault_root=vault_root, projects_root=projects_root)
    out_a = (vault_root / "BURL" / "events" / "Q4_FY2025" / "learning" / "thinking.md").read_text()
    primary_a = parse_session_blocks(projects_root / f"{LEARNER_SID}.jsonl")
    exp_thinking_chars = sum(len(b["content"]) for b in primary_a if b["kind"] == "thinking")
    exp_thinking_blocks = sum(1 for b in primary_a if b["kind"] == "thinking")
    exp_redacted = sum(1 for b in primary_a if b["kind"] == "thinking_redacted")
    assert f"thinking_chars: {exp_thinking_chars}" in out_a
    assert f"thinking_blocks: {exp_thinking_blocks}" in out_a
    assert f"redacted_thinking_blocks: {exp_redacted}" in out_a

    # EMBED-redacted guidance
    projects_root = _stage_fixture_session(tmp_path / "b", "guidance_session", GUIDANCE_SID)
    vault_root = tmp_path / "b" / "v"
    harvest(thinking_type="guidance", ticker="BURL", quarter="Q4_FY2025",
            session_id=GUIDANCE_SID, vault_root=vault_root, projects_root=projects_root)
    out_b = (vault_root / "BURL" / "events" / "Q4_FY2025" / "guidance" / "thinking.md").read_text()
    primary_b = parse_session_blocks(projects_root / f"{GUIDANCE_SID}.jsonl")
    exp_redacted_b = sum(1 for b in primary_b if b["kind"] == "thinking_redacted")
    assert f"redacted_thinking_blocks: {exp_redacted_b}" in out_b, \
        "EMBED-redacted scope-lock failed for redacted_thinking_blocks"

    # FORK predictor — thinking_chars scope merges skill-fork
    projects_root = _stage_fixture_session(tmp_path / "c", "predictor_session", PREDICTOR_SID)
    vault_root = tmp_path / "c" / "v"
    harvest(thinking_type="prediction", ticker="BURL", quarter="Q4_FY2025",
            session_id=PREDICTOR_SID, vault_root=vault_root, projects_root=projects_root)
    out_c = (vault_root / "BURL" / "events" / "Q4_FY2025" / "prediction" / "thinking.md").read_text()
    primary_c = parse_session_blocks(projects_root / f"{PREDICTOR_SID}.jsonl")
    sub_root = projects_root / PREDICTOR_SID / "subagents"
    fork_c = parse_session_blocks(next(sub_root.glob("agent-*.jsonl")))
    exp_thinking_chars_fork = sum(len(b["content"]) for b in primary_c + fork_c if b["kind"] == "thinking")
    exp_redacted_fork = sum(1 for b in primary_c if b["kind"] == "thinking_redacted")
    assert f"thinking_chars: {exp_thinking_chars_fork}" in out_c, \
        "FORK thinking_chars scope drifted (must stay content_blocks-merged)"
    assert f"redacted_thinking_blocks: {exp_redacted_fork}" in out_c, \
        "FORK redacted_thinking_blocks scope drifted (must stay primary-only)"


def test_fork_without_skill_fork_content_falls_back_to_embed_wording(tmp_path):
    """Edge case: primary has a Skill tool_use but the skill-fork JSONL is
    missing or has no content. session_pattern stays FORK (detected via
    tool_use) but skill_fork_blocks is empty, so the summary must NOT claim
    'primary + skill-fork' — it falls back to the existing EMBED-style
    wording, and text_* counts are primary-only."""
    import json
    from thinking_harvester import harvest

    projects_root = tmp_path / "projects"
    sid = "fork-no-skill-fork-jsonl"
    (projects_root / sid / "subagents").mkdir(parents=True)
    primary = projects_root / f"{sid}.jsonl"
    # Primary: Skill tool_use + matching tool_result with agentId that does
    # NOT correspond to any subagent JSONL on disk → skill_fork_blocks stays [].
    primary.write_text("\n".join([
        json.dumps({
            "type": "assistant", "timestamp": "2026-01-01T00:00:01Z",
            "message": {"content": [
                {"type": "text", "text": "some primary text 1234"},
                {"type": "tool_use", "id": "tu-S", "name": "Skill",
                 "input": {"skill": "earnings-prediction"}},
            ]}
        }),
        json.dumps({
            "type": "user", "timestamp": "2026-01-01T00:00:02Z",
            "message": {"content": [
                {"type": "tool_result", "tool_use_id": "tu-S",
                 "content": [{"type": "text", "text": "ok"}]}
            ]},
            "toolUseResult": {"agentId": "deadbeef00000000", "agentType": None},
        }),
    ]) + "\n")

    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="prediction", ticker="TST", quarter="QX",
        session_id=sid, vault_root=vault_root, projects_root=projects_root,
    )
    out = (vault_root / "TST" / "events" / "QX" / "prediction"
           / "thinking.md").read_text(encoding="utf-8")
    # session_pattern must still be FORK (pattern is tool-based)
    assert "session_pattern: FORK" in out
    # …but the body summary falls back to EMBED-style since no skill-fork content loaded
    assert "Primary thinking:" in out
    assert "Reasoning (primary + skill-fork):" not in out
    # text_chars / text_blocks reflect primary only
    # ("some primary text 1234" = 22 chars, 1 text block)
    assert "text_blocks: 1" in out
    assert "text_chars: 22" in out


# ── Agent bullet description rendering (P0 "Agent spawn rationale") ────────

def test_agent_bullet_without_description_falls_back_to_subagent_type():
    """Legacy fallback: if Agent tool input has no ``description`` key, the
    bullet renders exactly as before — ``🤖 Agent(subagent_type)`` with no
    trailing colon. Preserves the pre-fix format for older transcripts."""
    from thinking_harvester import _tool_use_annotation
    block = {"kind": "tool_use", "ts": "", "meta": {
        "name": "Agent", "id": "tu1",
        "input": {"subagent_type": "neo4j-news"},  # no description
    }}
    ann = _tool_use_annotation(block)
    assert ann == "🤖 Agent(neo4j-news)"


def test_agent_bullet_includes_short_description():
    """Agent.input.description is appended as ``: `<desc>` `` — wrapped in
    a single-backtick code span so free-text markdown control chars in the
    description render as literals."""
    from thinking_harvester import _tool_use_annotation
    block = {"kind": "tool_use", "ts": "", "meta": {
        "name": "Agent", "id": "tu1",
        "input": {"subagent_type": "neo4j-news",
                  "description": "BURL post-earnings news 2025-11-25"},
    }}
    ann = _tool_use_annotation(block)
    assert ann == "🤖 Agent(neo4j-news): `BURL post-earnings news 2025-11-25`"


def test_agent_description_truncated_to_80_body_plus_ellipsis():
    """Truncation: description body capped at 80 chars; 1-char ``…`` suffix on
    overflow; total visible inside the code span = up to 81 chars."""
    from thinking_harvester import _tool_use_annotation
    long_desc = "X" * 200
    block = {"kind": "tool_use", "ts": "", "meta": {
        "name": "Agent", "id": "tu1",
        "input": {"subagent_type": "test-sub", "description": long_desc},
    }}
    ann = _tool_use_annotation(block)
    prefix = "🤖 Agent(test-sub): `"
    suffix = "`"
    assert ann.startswith(prefix)
    assert ann.endswith(suffix)
    body = ann[len(prefix):-len(suffix)]
    assert body.endswith("…")
    assert len(body) == 81, f"body+ellipsis should be 81 chars, got {len(body)}"
    assert body[:-1] == "X" * 80


def test_agent_description_internal_newlines_collapsed():
    """Descriptions with internal whitespace/newlines must render on one line
    so the bullet doesn't break the list structure in Obsidian."""
    from thinking_harvester import _tool_use_annotation
    block = {"kind": "tool_use", "ts": "", "meta": {
        "name": "Agent", "id": "tu1",
        "input": {"subagent_type": "x", "description": "first\nsecond\t\tthird"},
    }}
    ann = _tool_use_annotation(block)
    assert ann == "🤖 Agent(x): `first second third`"


def test_agent_description_with_markdown_chars_rendered_as_literal():
    """Description containing markdown control chars (``*``, ``_``, link
    syntax) is wrapped in a code span so Obsidian renders the chars as
    literals rather than applying italic / bold / link formatting."""
    from thinking_harvester import _tool_use_annotation
    block = {"kind": "tool_use", "ts": "", "meta": {
        "name": "Agent", "id": "tu1",
        "input": {"subagent_type": "x",
                  "description": "fetch *BURL* data [see](url) _q3_"},
    }}
    ann = _tool_use_annotation(block)
    # Single-backtick fence suffices — no backtick in desc.
    assert ann == "🤖 Agent(x): `fetch *BURL* data [see](url) _q3_`"


def test_agent_description_containing_backtick_uses_double_fence():
    """When description itself contains a ``\u0060`` (rare), single-backtick
    fence would break the code span. Escalate to a double-backtick fence —
    CommonMark allows the inner single backtick when the fence is wider."""
    from thinking_harvester import _tool_use_annotation
    block = {"kind": "tool_use", "ts": "", "meta": {
        "name": "Agent", "id": "tu1",
        "input": {"subagent_type": "x",
                  "description": "refs `foo` in code"},
    }}
    ann = _tool_use_annotation(block)
    assert ann == "🤖 Agent(x): ``refs `foo` in code``"


def test_repeat_subagent_types_now_distinguishable_end_to_end(tmp_path):
    """End-to-end regression for the real learner pain point: BURL Q3 FY2025
    spawned two ``neo4j-news`` agents with different descriptions; before the
    fix both rendered as ``- 🤖 Agent(neo4j-news)`` (ambiguous). After the
    fix, each bullet carries its distinct description and reviewers can tell
    them apart without opening subagent traces.

    Covers BOTH surfaces where ``_tool_use_annotation`` is called — primary
    ``thinking.md`` rendering AND subagent-trace rendering (via the shared
    helper). Here we assert on the primary note (subagent-trace coverage is
    exercised transitively by the shared helper)."""
    import json
    from thinking_harvester import harvest

    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    session_id = "cafebabe-1111-2222-3333-444455556666"
    primary = projects_root / f"{session_id}.jsonl"
    primary.write_text(
        json.dumps({
            "type": "assistant",
            "message": {"content": [
                {"type": "tool_use", "id": "tu1", "name": "Agent",
                 "input": {"subagent_type": "neo4j-news",
                           "description": "BURL post-earnings news 2025-11-25"}},
                {"type": "tool_use", "id": "tu2", "name": "Agent",
                 "input": {"subagent_type": "neo4j-news",
                           "description": "Off-price peer comp prints pre-BURL"}},
            ], "stop_reason": "tool_use"},
            "timestamp": "2026-01-01T00:00:00Z",
        }) + "\n"
        + json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "done"}],
                        "stop_reason": "end_turn"},
            "timestamp": "2026-01-01T00:00:01Z",
        }) + "\n"
    )

    vault_root = tmp_path / "vault"
    harvest(
        thinking_type="learning", ticker="TEST", quarter="Q1_FY2025",
        session_id=session_id,
        vault_root=vault_root, projects_root=projects_root,
    )
    out = (vault_root / "TEST" / "events" / "Q1_FY2025" / "learning"
           / "thinking.md").read_text(encoding="utf-8")
    # Both descriptions must appear (wrapped in a code span), disambiguating
    # the repeat subagent type.
    assert "🤖 Agent(neo4j-news): `BURL post-earnings news 2025-11-25`" in out
    assert "🤖 Agent(neo4j-news): `Off-price peer comp prints pre-BURL`" in out
