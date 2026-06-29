#!/usr/bin/env python3
"""Verify a signed release manifest and optional framework ZIP hash.

Usage:
    python tools/verify_release_manifest.py MANIFEST.json MANIFEST.sig PUBLIC_KEY.pem [FRAMEWORK_ZIP]
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import sys
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if len(sys.argv) not in (4, 5):
        print("Usage: verify_release_manifest.py MANIFEST.json MANIFEST.sig PUBLIC_KEY.pem [FRAMEWORK_ZIP]", file=sys.stderr)
        return 2
    manifest_path = pathlib.Path(sys.argv[1])
    sig_path = pathlib.Path(sys.argv[2])
    public_key_path = pathlib.Path(sys.argv[3])
    manifest_bytes = manifest_path.read_bytes()
    public_key = serialization.load_pem_public_key(public_key_path.read_bytes())
    try:
        public_key.verify(sig_path.read_bytes(), manifest_bytes)
    except InvalidSignature:
        print("INVALID: manifest signature failed")
        return 1
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    print("Manifest signature: valid")
    print("Latest version:", manifest.get("latest_framework_version"))
    print("Latest hash:   ", manifest.get("latest_framework_sha256"))
    print("Latest code:   ", manifest.get("latest_framework_code_sha256"))
    print("Accepted code:", manifest.get("accepted_framework_code_sha256"))
    if len(sys.argv) == 5:
        fw_path = pathlib.Path(sys.argv[4])
        actual = sha256_file(fw_path)
        expected = manifest.get("latest_framework_sha256")
        if actual != expected:
            print("INVALID: framework ZIP hash mismatch")
            print("  expected:", expected)
            print("  actual:  ", actual)
            return 1
        print("Framework ZIP hash: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
