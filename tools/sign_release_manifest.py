#!/usr/bin/env python3
"""Sign a release manifest using Ed25519.

The signature is over the exact manifest bytes. Do not edit the manifest after signing.

Usage:
    python tools/sign_release_manifest.py MANIFEST.json PRIVATE_KEY.pem MANIFEST.sig
"""
from __future__ import annotations
import pathlib
import sys
from cryptography.hazmat.primitives import serialization


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: sign_release_manifest.py MANIFEST.json PRIVATE_KEY.pem MANIFEST.sig", file=sys.stderr)
        return 2
    manifest_path = pathlib.Path(sys.argv[1])
    private_key_path = pathlib.Path(sys.argv[2]).expanduser()
    sig_path = pathlib.Path(sys.argv[3])
    manifest_bytes = manifest_path.read_bytes()
    private_key = serialization.load_pem_private_key(private_key_path.read_bytes(), password=None)
    signature = private_key.sign(manifest_bytes)
    sig_path.write_bytes(signature)
    print(f"Signed manifest: {manifest_path}")
    print(f"Wrote signature:  {sig_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
