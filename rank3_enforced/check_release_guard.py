from __future__ import annotations

import argparse
import json
from pathlib import Path

from .version_guard import enforce_latest_release_guard


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify latest signed framework release guard.")
    parser.add_argument("--run-kind", default="candidate")
    parser.add_argument("--mode", default=None, help="required, warn, or off")
    parser.add_argument("--manifest-url", default=None)
    parser.add_argument("--signature-url", default=None)
    parser.add_argument("--public-key-url", default=None)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--cache-path", default=None)
    parser.add_argument("--framework-zip", default=None)
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()
    report = enforce_latest_release_guard(
        run_kind=args.run_kind,
        mode=args.mode,
        manifest_url=args.manifest_url,
        signature_url=args.signature_url,
        public_key_url=args.public_key_url,
        cache_dir=args.cache_dir,
        cache_path=args.cache_path,
        framework_zip_path=args.framework_zip,
        force_refresh=args.force_refresh,
    )
    payload = report.to_dict()
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
