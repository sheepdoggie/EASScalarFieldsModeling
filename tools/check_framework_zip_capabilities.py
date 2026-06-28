#!/usr/bin/env python3
"""Check that a framework ZIP contains the capability files required by the release manifest.

Usage:
    python tools/check_framework_zip_capabilities.py FRAMEWORK_RELEASE_MANIFEST.json enforceable_rank3_modeling.zip
"""
from __future__ import annotations
import json
import pathlib
import sys
import zipfile


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: check_framework_zip_capabilities.py MANIFEST.json FRAMEWORK_ZIP", file=sys.stderr)
        return 2
    manifest = json.loads(pathlib.Path(sys.argv[1]).read_text())
    zip_path = pathlib.Path(sys.argv[2])
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
    missing = [p for p in manifest.get("required_files_in_zip", []) if p not in names]
    if missing:
        print("MISSING REQUIRED FILES:")
        for p in missing:
            print("  -", p)
        return 1
    print("Required capability files: present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
