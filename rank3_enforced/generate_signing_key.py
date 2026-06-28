from __future__ import annotations

import sys
from pathlib import Path

from .signing import create_signing_keypair


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        print("Usage: python -m rank3_enforced.generate_signing_key <private_key.pem> <public_key.pem>")
        return 2
    create_signing_keypair(private_key_path=Path(argv[0]), public_key_path=Path(argv[1]))
    print(f"Wrote private key: {argv[0]}")
    print(f"Wrote public key: {argv[1]}")
    print("Keep the private key outside AI-editable workspaces. Do not include it in output ZIPs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
