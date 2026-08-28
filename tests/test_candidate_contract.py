from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "candidate_contract_under_test", ROOT / "apps" / "organization-mcp" / "candidate_contract.py"
)
assert SPEC and SPEC.loader
CANDIDATES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CANDIDATES)


def test_candidate_kinds_are_role_scoped():
    assert CANDIDATES.allowed_candidate_kinds("DROLE-01") == ("brief", "evidence", "fact", "claim")
    assert CANDIDATES.allowed_candidate_kinds("DROLE-02") == ("campaign", "content", "review")
    assert CANDIDATES.allowed_candidate_kinds("DROLE-03") == ("review",)


def test_cross_role_candidate_kind_fails_closed():
    with pytest.raises(ValueError, match="not allowed"):
        CANDIDATES.validate_candidate_kind("DROLE-01", "campaign")
    with pytest.raises(ValueError, match="not allowed"):
        CANDIDATES.validate_candidate_kind("DROLE-03", "claim")


def test_unknown_role_fails_closed():
    with pytest.raises(ValueError, match="unknown role"):
        CANDIDATES.allowed_candidate_kinds("DROLE-99")


def test_real_candidate_metadata_keeps_case_step_attempt_and_mode_provenance():
    metadata = CANDIDATES.candidate_metadata("DROLE-01", "commitment-1", "attempt-1", {
        "case_id": "case-1", "stage_key": "pma", "execution_mode": "real", "ignored": "value",
    })
    assert metadata == {
        "candidate": True,
        "role_id": "DROLE-01",
        "commitment_id": "commitment-1",
        "attempt_id": "attempt-1",
        "case_id": "case-1",
        "stage_key": "pma",
        "execution_mode": "real",
    }


def test_marketing_case_bga_cannot_create_publish_task_before_human_approval():
    with pytest.raises(ValueError, match="人工内容审核"):
        CANDIDATES.validate_manual_publish_context("DROLE-02", {"case_id": "case-1", "stage_key": "bga"})
    CANDIDATES.validate_manual_publish_context("DROLE-02", {})
    with pytest.raises(ValueError, match="only BGA"):
        CANDIDATES.validate_manual_publish_context("DROLE-01", {})
