"""Pure policy helpers for Runtime Run capabilities."""


def require_workflow_write(run: dict) -> None:
    """Reject every organization write from an interactive chat Run."""
    if run.get("purpose", "workflow") != "workflow":
        raise ValueError("interactive Agent chat is read-only and cannot mutate organization state")
