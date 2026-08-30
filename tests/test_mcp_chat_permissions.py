import pytest

from run_purpose_contract import require_workflow_write


def test_workflow_run_keeps_mcp_write_capability():
    require_workflow_write({"purpose": "workflow"})
    require_workflow_write({})  # legacy Runs retain their original workflow semantics


def test_chat_run_cannot_write_through_organization_mcp():
    with pytest.raises(ValueError, match="read-only"):
        require_workflow_write({"purpose": "chat"})
