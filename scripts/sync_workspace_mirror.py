#!/usr/bin/env python3
"""Deterministically sync the formal workspace source to the standalone Demo1 mirror."""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "apps" / "workspace"
DEFAULT_TARGET = ROOT.parent / "demo1" / "demo1"
ROOT_FILES = (
    "index.html",
    "package.json",
    "package-lock.json",
    "playwright.config.ts",
    "README.md",
    "tsconfig.json",
    "tsconfig.app.json",
    "vite.config.ts",
)
TREES = ("src", "scripts", "tests")


def source_files() -> list[Path]:
    files = [SOURCE / name for name in ROOT_FILES if (SOURCE / name).is_file()]
    for tree in TREES:
        files.extend(path for path in sorted((SOURCE / tree).rglob("*")) if path.is_file())
    return files


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sync(target: Path, check: bool) -> list[str]:
    mismatches: list[str] = []
    for source in source_files():
        relative = source.relative_to(SOURCE)
        destination = target / relative
        if not destination.exists() or digest(source) != digest(destination):
            mismatches.append(relative.as_posix())
            if not check:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
    return mismatches


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync or verify the standalone Demo1 source mirror.")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = args.target.resolve()
    if not target.is_dir():
        raise SystemExit(f"Demo1 mirror does not exist: {target}")
    mismatches = sync(target, args.check)
    if args.check and mismatches:
        print("Workspace mirror differs:")
        for item in mismatches:
            print(f"- {item}")
        return 2
    if args.check:
        print(f"Workspace mirror is consistent ({len(source_files())} files).")
    else:
        print(f"Workspace mirror updated ({len(mismatches)} changed, {len(source_files())} verified files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
