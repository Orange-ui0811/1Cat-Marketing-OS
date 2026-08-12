#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs" / "baseline" / "V0.3"
EXPECTED_COUNT = 79
EXPECTED_MANIFEST_HASH = "b1a6a716d9bdcc9cca9ab58dca4bf57279d7cb391a0122452887f850a7eef983"

files = sorted(BASE.rglob("*.md"))
if len(files) != EXPECTED_COUNT:
    raise SystemExit(f"baseline count mismatch: expected {EXPECTED_COUNT}, got {len(files)}")
manifest_file = BASE / "09_Implementation_Handoff" / "06_V0.3规范文件SHA-256清单.md"
actual = hashlib.sha256(manifest_file.read_bytes()).hexdigest()
print(f"baseline_markdown_count={len(files)}")
print(f"manifest_file_sha256={actual}")
print(f"frozen_manifest_set_sha256={EXPECTED_MANIFEST_HASH}")

