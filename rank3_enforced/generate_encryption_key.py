from __future__ import annotations

import json
import sys
from pathlib import Path

from .encryption import create_encryption_keypair


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        print("Usage: python -m rank3_enforced.generate_encryption_key <private_key.pem> <public_key.pem>")
        return 2
    record = create_encryption_keypair(private_key_path=Path(argv[0]), public_key_path=Path(argv[1]))
    print(json.dumps(record.__dict__, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
