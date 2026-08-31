#!/usr/bin/env python3
"""Render miner YAML from template using live deploy origin."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    base = os.environ.get("ONLOOKOUT_BASE_URL", "").rstrip("/")
    if not base.startswith("http://") and not base.startswith("https://"):
        print("ONLOOKOUT_BASE_URL must be an http or https origin", file=sys.stderr)
        return 1

    root = Path(__file__).resolve().parents[1]
    template = (root / "miner" / "onlookout-weather.template.yaml").read_text(encoding="utf-8")
    rendered = template.replace("{{ONLOOKOUT_BASE_URL}}", base)
    out = root / "miner" / "onlookout-weather.yaml"
    out.write_text(rendered, encoding="utf-8", newline="\n")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
