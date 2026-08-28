from __future__ import annotations

from typing import Any, Literal


CandidateKind = Literal["brief", "evidence", "fact", "claim", "campaign", "content", "review"]

ROLE_CANDIDATE_KINDS: dict[str, tuple[CandidateKind, ...]] = {
    "DROLE-01": ("brief", "evidence", "fact", "claim"),
    "DROLE-02": ("campaign", "content", "review"),
    "DROLE-03": ("review",),
}


def allowed_candidate_kinds(role_id: str) -> tuple[CandidateKind, ...]:
    try:
        return ROLE_CANDIDATE_KINDS[role_id]
    except KeyError as exc:
        raise ValueError("unknown role for candidate creation") from exc


def validate_candidate_kind(role_id: str, kind: CandidateKind) -> CandidateKind:
    if kind not in allowed_candidate_kinds(role_id):
        allowed = ", ".join(allowed_candidate_kinds(role_id))
        raise ValueError(f"candidate kind '{kind}' is not allowed for {role_id}; allowed: {allowed}")
    return kind


def candidate_metadata(
    role_id: str,
    commitment_id: str,
    attempt_id: str,
    run_context: dict[str, Any],
) -> dict[str, Any]:
    """Build the immutable provenance envelope shared by real MCP candidates."""
    metadata: dict[str, Any] = {
        "candidate": True,
        "role_id": role_id,
        "commitment_id": commitment_id,
        "attempt_id": attempt_id,
    }
    for field in ("case_id", "stage_key", "execution_mode"):
        if run_context.get(field):
            metadata[field] = run_context[field]
    return metadata


def validate_manual_publish_context(role_id: str, run_context: dict[str, Any]) -> None:
    if role_id != "DROLE-02":
        raise ValueError("only BGA may prepare manual publishing")
    if run_context.get("case_id"):
        raise ValueError("Marketing Case发布任务只能在人工内容审核后由Runtime创建")
