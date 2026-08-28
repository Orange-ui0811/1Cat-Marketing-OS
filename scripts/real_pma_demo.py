#!/usr/bin/env python3
"""Backward-compatible PMA shortcut; prefer real_agent_demo.py --role pma."""

from real_agent_demo import main


if __name__ == "__main__":
    raise SystemExit(main(["--role", "pma"]))
