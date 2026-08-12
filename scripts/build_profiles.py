#!/usr/bin/env python3
"""Build reproducible Hermes profile bundles from the frozen V0.3 specifications."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs" / "baseline" / "V0.3"
PROFILES = ROOT / "profiles"

ROLE_MAP = {
    "pma": {
        "role": "DROLE-01",
        "name": "Product Marketing Agent",
        "soul": "DROLE-01_Product_Marketing_Agent_SOUL_v0.3.md",
        "manifest": "DROLE-01_Product_Marketing_Agent_Role_Manifest_v0.3.md",
        "memory": "DROLE-01_Product_Marketing_Agent_Memory_Policy_v0.3.md",
        "daily": "DROLE-01_Product_Marketing_Agent_Daily_Operation_v0.3.md",
        "allowlist": "DROLE-01_PMA_Tool_Allowlist_v0.3.md",
        "skill_dir": "PMA",
        "skill_prefix": "SKL-PM-",
    },
    "bga": {
        "role": "DROLE-02",
        "name": "Brand & Growth Agent",
        "soul": "DROLE-02_Brand_and_Growth_Agent_SOUL_v0.3.md",
        "manifest": "DROLE-02_Brand_and_Growth_Agent_Role_Manifest_v0.3.md",
        "memory": "DROLE-02_Brand_and_Growth_Agent_Memory_Policy_v0.3.md",
        "daily": "DROLE-02_Brand_and_Growth_Agent_Daily_Operation_v0.3.md",
        "allowlist": "DROLE-02_BGA_Tool_Allowlist_v0.3.md",
        "skill_dir": "BGA",
        "skill_prefix": "SKL-BG-",
    },
    "mo": {
        "role": "DROLE-03",
        "name": "Marketing Orchestrator",
        "soul": "DROLE-03_Marketing_Orchestrator_SOUL_v0.3.md",
        "manifest": "DROLE-03_Marketing_Orchestrator_Role_Manifest_v0.3.md",
        "memory": "DROLE-03_Marketing_Orchestrator_Memory_Policy_v0.3.md",
        "daily": "DROLE-03_Marketing_Orchestrator_Daily_Operation_v0.3.md",
        "allowlist": "DROLE-03_MO_Tool_Allowlist_v0.3.md",
        "skill_dir": "MO",
        "skill_prefix": "SKL-OR-",
    },
}

DISABLED_TOOLSETS = [
    "web", "browser", "terminal", "file", "code_execution", "vision",
    "video", "image_gen", "video_gen", "bfl", "x_search", "tts",
    "skills", "todo", "memory", "context_engine", "session_search",
    "clarify", "delegation", "cronjob", "homeassistant", "spotify",
    "discord", "discord_admin", "yuanbao", "computer_use",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def skill_name(path: Path) -> str:
    stem = path.stem.replace("_v0.3", "")
    return re.sub(r"[^A-Za-z0-9-]+", "-", stem).strip("-").lower()


def write_skill(source: Path, destination: Path, dormant: bool = False) -> None:
    text = source.read_text(encoding="utf-8")
    title = text.splitlines()[0].removeprefix("#").strip()
    frontmatter = (
        "---\n"
        f"name: {skill_name(source)}\n"
        f"description: {title}。仅用于一猫营销R0候选产物与人工协作，不授予平台写入能力。\n"
        f"metadata:\n  source_sha256: {sha(source)}\n  dormant: {str(dormant).lower()}\n"
        "---\n\n"
    )
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "SKILL.md").write_text(frontmatter + text + "\n", encoding="utf-8")


def main() -> None:
    shared_sources = sorted((BASE / "03_Skill_Spec" / "Shared").glob("SKL-*.md"))
    for profile, spec in ROLE_MAP.items():
        home = PROFILES / profile
        if home.exists():
            shutil.rmtree(home)
        (home / "skills").mkdir(parents=True)
        shutil.copy2(BASE / "02_SOUL" / spec["soul"], home / "SOUL.md")
        shutil.copy2(BASE / "01_Role_Manifest" / spec["manifest"], home / "ROLE_MANIFEST.md")
        shutil.copy2(BASE / "04_Memory_Policy" / spec["memory"], home / "MEMORY_POLICY.md")
        shutil.copy2(BASE / "05_Daily_Operation" / spec["daily"], home / "DAILY_OPERATION.md")
        shutil.copy2(BASE / "07_Tool_Permission" / spec["allowlist"], home / "TOOL_ALLOWLIST.md")
        (home / "MEMORY.md").write_text(
            "# Durable Memory\n\n仅保存稳定偏好、组织约束和权威对象引用。禁止PII、业务原件、审批、Commitment状态和完整日志。\n",
            encoding="utf-8",
        )
        for source in shared_sources:
            write_skill(source, home / "skills" / source.stem.split("_")[0])
        role_sources = sorted((BASE / "03_Skill_Spec" / spec["skill_dir"]).glob(f'{spec["skill_prefix"]}*.md'))
        for source in role_sources:
            if source.name.startswith("SKL-BG-11"):
                continue
            write_skill(source, home / "skills" / source.stem.split("_")[0])
        config = {
            "model": {"default": "gpt-5.6-terra", "provider": "openai-codex"},
            "gateway": {"api_server": {"enabled": True, "host": "0.0.0.0", "port": 8080}},
            "skills": {"auto_load": False},
            "approvals": {"mode": "ask"},
            "agent": {"max_turns": 24, "disabled_toolsets": DISABLED_TOOLSETS},
            "platform_toolsets": {"api_server": ["organization-runtime"]},
            "mcp_servers": {
                "organization-runtime": {
                    "url": "http://organization-mcp:8001/mcp",
                    "transport": "http",
                    "enabled": True,
                    "timeout": 20,
                }
            },
            # Defense in depth: even accidental terminal exposure cannot use
            # the local host backend; no Docker socket is mounted in R0.
            "terminal": {"backend": "docker"},
        }
        try:
            import yaml
            config_text = yaml.safe_dump(config, allow_unicode=True, sort_keys=False)
        except ImportError:
            config_text = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
        (home / "config.yaml").write_text(config_text, encoding="utf-8")
        files = sorted(p for p in home.rglob("*") if p.is_file())
        manifest = {
            "role_id": spec["role"], "profile_id": profile, "bundle_version": "0.1.0-r0",
            "hermes_commit": "3c27eb6234bf91b8ceee9e9071591b31e9b148cb",
            "files": {str(path.relative_to(home)): sha(path) for path in files},
        }
        (home / "bundle-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    dormant_source = BASE / "03_Skill_Spec" / "BGA" / "SKL-BG-11_视频号增长Playbook集成_v0.3.md"
    dormant = PROFILES / "dormant" / "SKL-BG-11"
    if dormant.parent.exists():
        shutil.rmtree(dormant.parent)
    write_skill(dormant_source, dormant, dormant=True)
    (dormant / "ACTIVATION_BLOCKED").write_text("R0_SCOPE_GATE: video channel skill must not be loaded.\n", encoding="utf-8")


if __name__ == "__main__":
    main()
