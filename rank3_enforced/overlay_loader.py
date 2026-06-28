from __future__ import annotations

import json
from pathlib import Path

from .exceptions import ManifestError
from .fingerprints import file_hash, stable_json_hash
from .overlay_schema import DeclarativeOverlay, parse_declarative_overlay


def load_declarative_overlay(path: str | Path) -> tuple[DeclarativeOverlay, str]:
    """Load a data-only JSON overlay and return (overlay, overlay_hash)."""

    overlay_path = Path(path)
    if overlay_path.suffix.lower() != ".json":
        raise ManifestError(
            "Enforced overlays must be JSON files. Arbitrary Python/YAML loaders are not accepted."
        )
    if not overlay_path.is_file():
        raise ManifestError(f"Overlay file does not exist: {overlay_path}")

    with overlay_path.open("r", encoding="utf-8") as handle:
        try:
            payload = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ManifestError(f"Overlay is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise ManifestError("Overlay root must be a JSON object.")

    overlay = parse_declarative_overlay(payload)
    overlay_hash = stable_json_hash({"file_hash": file_hash(overlay_path), "payload": payload})
    return overlay, overlay_hash
