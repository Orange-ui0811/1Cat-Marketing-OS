import worker
from worker import chat_profile_instructions, execution_mode_uses_real, tool_contract_instruction


def test_pma_tool_contract_exposes_exact_candidate_kinds_and_bounded_retry():
    instruction = tool_contract_instruction("pma")

    assert "brief, evidence, fact, claim" in instruction
    assert "candidate_kinds_read" in instruction
    assert "最多重试一次" in instruction
    assert "tool_search" in instruction
    assert "get_prompt" in instruction
    assert "Runtime Worker会在Hermes成功后原子推进到submitted" in instruction
    assert "不要调用commitment_respond" in instruction


def test_each_profile_gets_its_role_scoped_candidate_kinds():
    assert "campaign, content, review" in tool_contract_instruction("bga")
    assert "review" in tool_contract_instruction("mo")


def test_explicit_execution_mode_wins_over_global_legacy_switch(monkeypatch):
    monkeypatch.setattr(worker, "hermes_enabled", lambda: True)
    assert execution_mode_uses_real("synthetic") is False
    assert execution_mode_uses_real("real") is True
    assert execution_mode_uses_real(None) is True
    monkeypatch.setattr(worker, "hermes_enabled", lambda: False)
    assert execution_mode_uses_real(None) is False


def test_chat_instruction_uses_published_profile_but_forbids_business_writes():
    instruction = chat_profile_instructions(
        "pma",
        "commitment-chat",
        "attempt-chat",
        {
            "role_name": "Product Marketing Agent",
            "skills": [{"id": "fact-version", "enabled": True}],
            "memory_summary": "不保存正式事实。",
        },
    )

    assert "Product Marketing Agent" in instruction
    assert "fact-version" in instruction
    assert "只读Tool" in instruction
    assert "严禁创建或修改Commitment" in instruction
    assert "attempt_id=attempt-chat" in instruction


def test_workflow_profile_instructions_respect_published_skill_and_prompt_snapshot():
    instruction = worker.profile_instructions(
        "pma",
        "commitment-test",
        "attempt-test",
        {
            "six_pack": [
                {"key": "role_manifest", "status": "ready"},
                {"key": "soul", "status": "ready"},
            ],
            "skills": [
                {"id": "fact-version", "source": "SKL-PM-01", "enabled": True, "status": "ready"},
                {"id": "disabled", "source": "SKL-PM-02", "enabled": False, "status": "ready"},
            ],
            "permissions": {"tools": ["Fact Registry"], "network": False, "terminal": False, "browser": False},
            "prompt_templates": {"workflow": {"version": "v9", "body": "这是发布后的工作流模板，只生成有来源且需人工审核的候选对象。"}},
        },
    )
    assert "Published workflow prompt v9" in instruction
    assert "这是发布后的工作流模板" in instruction
    assert "tools=['Fact Registry']" in instruction
    assert "SKL-PM-01" in instruction
    assert "SKL-PM-02" not in instruction
