from __future__ import annotations

import json
import sys
from pathlib import Path

from .dual_package import verify_dual_evidence_package


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("Usage: python -m rank3_enforced.verify_dual_package <transfer_dir> [recipient_private_key.pem]")
        return 2
    recipient_key = Path(argv[1]) if len(argv) > 1 else None
    report = verify_dual_evidence_package(Path(argv[0]), recipient_private_key_path=recipient_key)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str))
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
