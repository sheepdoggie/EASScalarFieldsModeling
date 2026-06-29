from __future__ import annotations

import argparse
import json
from importlib import resources
from pathlib import Path
from typing import Any

from .fingerprints import stable_json_hash

DEFAULT_MECHANISM_SET_ID = "charge_path_admission_mechanisms_v0_1"
_MECHANISM_FILES = {
    DEFAULT_MECHANISM_SET_ID: "charge_path_admission_mechanisms_v0_1.json",
}


def load_mechanism_set(mechanism_set_id: str = DEFAULT_MECHANISM_SET_ID) -> dict[str, Any]:
    if mechanism_set_id not in _MECHANISM_FILES:
        raise ValueError(f"unknown mechanism set: {mechanism_set_id}")
    ref = resources.files("rank3_enforced").joinpath("mechanisms", _MECHANISM_FILES[mechanism_set_id])
    return json.loads(ref.read_text(encoding="utf-8"))


def mechanism_set_fingerprint(mechanism_set_id: str = DEFAULT_MECHANISM_SET_ID) -> str:
    return stable_json_hash(load_mechanism_set(mechanism_set_id))


def admitted_mechanism_ids(mechanism_set_id: str = DEFAULT_MECHANISM_SET_ID) -> tuple[str, ...]:
    payload = load_mechanism_set(mechanism_set_id)
    return tuple(str(m.get("mechanism_id")) for m in payload.get("mechanisms", []) if m.get("certification_usable") is True and m.get("candidate") is False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List framework-declared admission-capable mechanism materials.")
    parser.add_argument("--mechanism-set-id", default=DEFAULT_MECHANISM_SET_ID)
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)
    payload = load_mechanism_set(args.mechanism_set_id)
    payload["mechanism_set_sha256"] = stable_json_hash(payload)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).expanduser().write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
