from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("real_agent_demo_under_test", ROOT / "scripts" / "real_agent_demo.py")
assert SPEC and SPEC.loader
DEMO = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = DEMO
SPEC.loader.exec_module(DEMO)


def test_three_real_agent_scenarios_are_bounded():
    assert {key: value.role_id for key, value in DEMO.ROLE_SPECS.items()} == {
        "pma": "DROLE-01",
        "bga": "DROLE-02",
        "mo": "DROLE-03",
    }
    assert "不执行发布" in DEMO.ROLE_SPECS["pma"].objective
    assert "不执行真实发布" in DEMO.ROLE_SPECS["bga"].objective
    assert "不代替人类" in DEMO.ROLE_SPECS["mo"].objective
    assert DEMO.ROLE_SPECS["pma"].allowed_candidate_kinds == ("brief", "evidence", "fact", "claim")
    assert DEMO.ROLE_SPECS["bga"].allowed_candidate_kinds == ("campaign", "content", "review")
    assert DEMO.ROLE_SPECS["mo"].allowed_candidate_kinds == ("review",)
