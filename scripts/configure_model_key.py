#!/usr/bin/env python3
"""Write a provider API key to the project-local Secret file without echoing it."""
from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path


def read_key(source: Path | None) -> str:
    if source is not None:
        value = source.read_text(encoding="utf-8").strip()
    else:
        value = getpass.getpass("DeepSeek API Key（输入不会显示）: ").strip()
    if len(value) < 16 or any(character.isspace() for character in value):
        raise SystemExit("DeepSeek API Key 为空或格式无效；未修改 Secret。")
    return value


def write_key(destination: Path, value: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(value)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        os.chmod(destination, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", default=".runtime/secrets/model_api_key")
    parser.add_argument("--from-file", type=Path)
    args = parser.parse_args()
    write_key(Path(args.destination), read_key(args.from_file))
    print("DeepSeek API Key 已写入项目本机 Secret 文件；未写入 .env、镜像或日志。")


if __name__ == "__main__":
    main()
