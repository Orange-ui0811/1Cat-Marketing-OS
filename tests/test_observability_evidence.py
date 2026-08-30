import json
import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import marketing_workflow_observability as workflow_observability


def test_failed_observability_check_preserves_canonical_latest(tmp_path, monkeypatch):
    canonical = tmp_path / "marketing-workflow-observability-latest.json"
    canonical.write_text('{"passed": true, "case_id": "accepted"}\n', encoding="utf-8")
    monkeypatch.setattr(workflow_observability, "EVIDENCE_DIR", tmp_path)
    monkeypatch.setattr(workflow_observability, "LATEST_EVIDENCE", canonical)

    paths = workflow_observability.write_evidence({
        "passed": False,
        "case_id": "synthetic-check",
        "execution_mode": "synthetic",
    })

    assert paths == [tmp_path / "marketing-workflow-observability-synthetic-latest.json"]
    assert json.loads(canonical.read_text(encoding="utf-8"))["case_id"] == "accepted"


def test_passed_real_observability_check_updates_mode_and_canonical(tmp_path, monkeypatch):
    canonical = tmp_path / "marketing-workflow-observability-latest.json"
    monkeypatch.setattr(workflow_observability, "EVIDENCE_DIR", tmp_path)
    monkeypatch.setattr(workflow_observability, "LATEST_EVIDENCE", canonical)

    result = {"passed": True, "case_id": "real-check", "execution_mode": "real"}
    paths = workflow_observability.write_evidence(result)

    assert paths == [
        tmp_path / "marketing-workflow-observability-real-latest.json",
        canonical,
    ]
    assert json.loads(paths[0].read_text(encoding="utf-8")) == result
    assert json.loads(canonical.read_text(encoding="utf-8")) == result
