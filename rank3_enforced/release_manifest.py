from __future__ import annotations

import base64
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.request import urlopen

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization

from .fingerprints import file_hash, stable_json_hash

DEFAULT_RELEASE_MANIFEST_URL = (
    "https://raw.githubusercontent.com/sheepdoggie/EASScalarFieldsModeling/"
    "main/releases/current/FRAMEWORK_RELEASE_MANIFEST.json"
)
DEFAULT_RELEASE_SIGNATURE_URL = (
    "https://raw.githubusercontent.com/sheepdoggie/EASScalarFieldsModeling/"
    "main/releases/current/FRAMEWORK_RELEASE_MANIFEST.sig"
)
DEFAULT_RELEASE_PUBLIC_KEY_URL = (
    "https://raw.githubusercontent.com/sheepdoggie/EASScalarFieldsModeling/"
    "main/releases/current/FRAMEWORK_RELEASE_PUBLIC_KEY.pem"
)


@dataclass(frozen=True)
class ReleaseManifestVerification:
    manifest_source: str
    signature_source: str
    public_key_source: str
    manifest_signature_valid: bool
    manifest_hash: str
    public_key_hash: str
    latest_framework_version: str
    latest_framework_release_label: str
    latest_framework_sha256: str | None
    latest_framework_code_sha256: str | None
    required_capabilities: tuple[str, ...]
    details: dict[str, Any]

    @property
    def valid(self) -> bool:
        return self.manifest_signature_valid

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReleaseManifestError(RuntimeError):
    pass


def _read_source(source: str | Path) -> bytes:
    source_str = str(source)
    if source_str.startswith("http://") or source_str.startswith("https://"):
        try:
            with urlopen(source_str, timeout=20) as response:  # nosec: user-controlled release URL by design
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            raise ReleaseManifestError(f"Could not fetch release source {source_str!r}: {exc}") from exc
    return Path(source).expanduser().read_bytes()


def _decode_signature(payload: bytes) -> bytes:
    # Release tools write raw Ed25519 bytes. Do not strip raw signatures:
    # a valid Ed25519 signature may begin or end with a byte that Python
    # classifies as whitespace. Base64 text is accepted as a convenience for
    # platforms that cannot store raw signature blobs cleanly.
    if len(payload) == 64:
        return payload
    stripped = payload.strip()
    try:
        decoded = base64.b64decode(stripped, validate=True)
    except Exception:
        return payload
    return decoded


def parse_manifest_bytes(manifest_bytes: bytes) -> dict[str, Any]:
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except Exception as exc:
        raise ReleaseManifestError(f"Release manifest is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ReleaseManifestError("Release manifest must be a JSON object.")
    return manifest


def verify_release_manifest_sources(
    *,
    manifest_source: str | Path = DEFAULT_RELEASE_MANIFEST_URL,
    signature_source: str | Path = DEFAULT_RELEASE_SIGNATURE_URL,
    public_key_source: str | Path = DEFAULT_RELEASE_PUBLIC_KEY_URL,
) -> ReleaseManifestVerification:
    manifest_bytes = _read_source(manifest_source)
    signature_bytes = _decode_signature(_read_source(signature_source))
    public_key_bytes = _read_source(public_key_source)
    try:
        public_key = serialization.load_pem_public_key(public_key_bytes)
        public_key.verify(signature_bytes, manifest_bytes)
        signature_valid = True
    except InvalidSignature:
        signature_valid = False
    except Exception as exc:
        raise ReleaseManifestError(f"Could not verify release manifest signature: {exc}") from exc

    manifest = parse_manifest_bytes(manifest_bytes)
    return ReleaseManifestVerification(
        manifest_source=str(manifest_source),
        signature_source=str(signature_source),
        public_key_source=str(public_key_source),
        manifest_signature_valid=signature_valid,
        manifest_hash=stable_json_hash(manifest),
        public_key_hash=__import__("hashlib").sha256(public_key_bytes).hexdigest(),
        latest_framework_version=str(manifest.get("latest_framework_version", "unknown")),
        latest_framework_release_label=str(manifest.get("latest_framework_release_label", "unknown")),
        latest_framework_sha256=manifest.get("latest_framework_sha256"),
        latest_framework_code_sha256=manifest.get("latest_framework_code_sha256"),
        required_capabilities=tuple(str(x) for x in manifest.get("required_capabilities", ())),
        details={"manifest": manifest},
    )


def verify_local_release_manifest(
    *,
    manifest_path: str | Path,
    signature_path: str | Path,
    public_key_path: str | Path,
    framework_zip_path: str | Path | None = None,
) -> ReleaseManifestVerification:
    report = verify_release_manifest_sources(
        manifest_source=manifest_path,
        signature_source=signature_path,
        public_key_source=public_key_path,
    )
    if framework_zip_path is not None:
        manifest = report.details["manifest"]
        observed = file_hash(framework_zip_path)
        expected = manifest.get("latest_framework_sha256")
        if expected and observed != expected:
            raise ReleaseManifestError(
                f"Framework ZIP hash mismatch: expected {expected}, observed {observed}"
            )
    return report
