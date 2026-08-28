import worker
from worker import execution_mode_uses_real, tool_contract_instruction


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
