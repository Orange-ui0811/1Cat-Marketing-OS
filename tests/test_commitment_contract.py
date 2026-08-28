from commitment_contract import allowed_commitment_actions, target_commitment_status


def test_commitment_actions_are_exact_and_map_to_runtime_statuses():
    assert allowed_commitment_actions() == (
        "accept",
        "activate",
        "wait",
        "submit",
        "request_takeover",
        "pause",
    )
    assert target_commitment_status("submit") == "submitted"
    assert "submitted" not in allowed_commitment_actions()
