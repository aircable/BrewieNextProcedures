#!/usr/bin/env python3
"""Require a release tag to match program-package.yml."""

import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def main(tag):
    version = str(yaml.safe_load((ROOT / "program-package.yml").read_text())["version"])
    expected = f"v{version}"
    if tag != expected:
        print(f"Tag {tag!r} does not match package version; expected {expected!r}", file=sys.stderr)
        return 1
    print(f"Release tag {tag} matches package version.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else ""))

