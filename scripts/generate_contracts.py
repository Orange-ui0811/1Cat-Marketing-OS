#!/usr/bin/env python3
"""Generate the frozen R0 JSON Schemas and lightweight TypeScript declarations."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "packages" / "contracts"
TYPES = ROOT / "packages" / "generated-types"

STRING = {"type": "string", "minLength": 1}
OBJECT = {"type": "object"}
ARRAY = {"type": "array"}

CONTRACTS = {
    "digital-role-manifest": {
        "required": ["role_id", "profile_id", "name", "mission", "owner_role", "lifecycle", "bundle_version"],
        "properties": {"role_id": STRING, "profile_id": STRING, "name": STRING, "mission": STRING,
                       "owner_role": STRING, "lifecycle": {"enum": ["defined", "onboarding", "shadow", "active_limited", "suspended", "retraining", "retired"]},
                       "responsibilities": ARRAY, "non_responsibilities": ARRAY, "bundle_version": STRING},
    },
    "organization-event-subscription": {
        "required": ["event_id", "event_type", "subscriber_role", "delivery", "correlation_id"],
        "properties": {"event_id": STRING, "event_type": STRING, "subscriber_role": STRING,
                       "delivery": {"enum": ["pending", "delivered", "dead_letter", "acknowledged"]},
                       "correlation_id": STRING, "payload": OBJECT, "deduplication_key": STRING},
    },
    "work-commitment": {
        "required": ["commitment_id", "version", "objective", "proposed_role", "status", "acceptance"],
        "properties": {"commitment_id": STRING, "version": {"type": "integer", "minimum": 1}, "objective": STRING,
                       "proposed_role": STRING, "committed_role": {"type": ["string", "null"]},
                       "status": {"enum": ["proposed", "clarifying", "accepted", "active", "waiting", "submitted", "fulfilled", "rejected", "manual_takeover", "paused", "cancelled"]},
                       "acceptance": OBJECT, "dependencies": ARRAY, "state_history": ARRAY},
    },
    "role-handoff": {
        "required": ["handoff_id", "commitment_id", "sender_role", "recipient", "purpose", "status", "object_refs"],
        "properties": {"handoff_id": STRING, "commitment_id": STRING, "sender_role": STRING, "recipient": STRING,
                       "purpose": STRING, "status": {"enum": ["pending", "accepted", "returned_for_revision", "rejected_out_of_scope", "dependency_missing", "superseded"]},
                       "object_refs": ARRAY, "evidence_refs": ARRAY, "residual_risks": ARRAY},
    },
    "context-snapshot": {
        "required": ["snapshot_id", "commitment_id", "attempt_id", "object_refs", "authority_snapshot_id", "expires_at"],
        "properties": {"snapshot_id": STRING, "commitment_id": STRING, "attempt_id": STRING, "object_refs": ARRAY,
                       "authority_snapshot_id": STRING, "expires_at": {"type": "string", "format": "date-time"}, "content_hash": STRING},
    },
    "tool-capability-policy": {
        "required": ["policy_id", "role_id", "profile_id", "service_identity_id", "capabilities", "effect"],
        "properties": {"policy_id": STRING, "role_id": STRING, "profile_id": STRING, "service_identity_id": STRING,
                       "capabilities": ARRAY, "effect": {"enum": ["allow", "deny"]}, "conditions": OBJECT},
    },
    "approval-grant": {
        "required": ["grant_id", "subject", "subject_version", "subject_hash", "action", "scope", "status", "issued_by", "remaining_uses"],
        "properties": {"grant_id": STRING, "subject": STRING, "subject_version": {"type": "integer", "minimum": 1},
                       "subject_hash": STRING, "action": STRING, "scope": OBJECT,
                       "status": {"enum": ["issued", "active", "consumed", "revoked", "expired", "invalidated"]},
                       "issued_by": STRING, "remaining_uses": {"type": "integer", "minimum": 0}},
    },
    "agent-run-task-attempt": {
        "required": ["agent_run_id", "attempt_id", "commitment_id", "role_id", "profile_id", "status", "context_snapshot_id"],
        "properties": {"agent_run_id": STRING, "attempt_id": STRING, "commitment_id": STRING, "role_id": STRING,
                       "profile_id": STRING, "hermes_run_id": {"type": ["string", "null"]},
                       "status": {"enum": ["queued", "accepted", "running", "result_received", "validating", "evidence_accepted", "evidence_rejected", "failed", "cancelled", "unknown"]},
                       "context_snapshot_id": STRING, "output_ref": {"type": ["string", "null"]}, "retryability": {"enum": ["safe", "unsafe", "not_applicable"]}},
    },
    "structured-output": {
        "required": ["schema_id", "schema_version", "object_type", "candidate_status", "payload", "source_refs"],
        "properties": {"schema_id": STRING, "schema_version": STRING, "object_type": STRING,
                       "candidate_status": {"enum": ["candidate", "pass_candidate", "submitted"]}, "payload": OBJECT,
                       "source_refs": ARRAY, "unknowns": ARRAY, "residual_risks": ARRAY},
    },
    "human-collaboration-workspace": {
        "required": ["workspace_id", "actor_id", "permissions", "inbox", "takeover_available"],
        "properties": {"workspace_id": STRING, "actor_id": STRING, "permissions": ARRAY, "inbox": ARRAY,
                       "takeover_available": {"const": True}, "audit_export_available": {"type": "boolean"}},
    },
}


def schema(name: str, body: dict) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://1cat.local/contracts/{name}/1.0.0",
        "title": "".join(part.title() for part in name.split("-")),
        "type": "object",
        "additionalProperties": False,
        **body,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    TYPES.mkdir(parents=True, exist_ok=True)
    exports = ["// Generated from packages/contracts. Do not edit by hand."]
    manifest = {}
    for name, body in CONTRACTS.items():
        payload = schema(name, body)
        path = OUT / f"{name}.schema.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        type_name = payload["title"]
        exports.append(f"export interface {type_name} {{ [key: string]: unknown }}")
        manifest[name] = {"version": "1.0.0", "file": path.name, "status": "R0"}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (TYPES / "contracts.ts").write_text("\n".join(exports) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

