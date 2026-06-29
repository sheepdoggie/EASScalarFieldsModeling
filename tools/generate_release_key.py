#!/usr/bin/env python3
"""Generate an Ed25519 release signing keypair.

Usage:
    python tools/generate_release_key.py PRIVATE_KEY.pem PUBLIC_KEY.pem

Commit PUBLIC_KEY.pem. Never commit PRIVATE_KEY.pem.
"""
from __future__ import annotations
import pathlib
import sys
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: generate_release_key.py PRIVATE_KEY.pem PUBLIC_KEY.pem", file=sys.stderr)
        return 2
    private_path = pathlib.Path(sys.argv[1]).expanduser()
    public_path = pathlib.Path(sys.argv[2]).expanduser()
    if private_path.exists():
        raise SystemExit(f"Refusing to overwrite existing private key: {private_path}")
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_path.write_bytes(private_bytes)
    public_path.write_bytes(public_bytes)
    try:
        private_path.chmod(0o600)
    except OSError:
        pass
    print(f"Wrote private key: {private_path}")
    print(f"Wrote public key:  {public_path}")
    print("Commit the public key only. Never commit the private key.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
