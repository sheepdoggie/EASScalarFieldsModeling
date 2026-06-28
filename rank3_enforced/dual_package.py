from __future__ import annotations

import base64
import json
import shutil
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .certificates import canonical_json_bytes, read_json, write_json
from .encryption import (
    decrypt_payload,
    encrypt_bytes_for_recipient,
    read_encrypted_payload,
    write_encrypted_payload,
)
from .fingerprints import file_hash, stable_json_hash
from .package_manifest import package_and_sign_enforced_result
from .signing import load_private_key, load_public_key, sign_bytes, verify_signature, write_public_key


@dataclass(frozen=True)
class TransferManifest:
    schema: str
    transfer_mode: str
    canonical_package_name: str
    plaintext_package_name: str
    encrypted_package_name: str
    canonical_package_sha256: str
    plaintext_package_sha256: str
    encrypted_package_sha256: str
    evidence_envelope_hash: str
    certificate_public_key_sha256: str
    recipient_public_key_sha256: str
    encryption_algorithm: str
    signature_algorithm: str
    plaintext_and_encrypted_payload_are_same_canonical_package: bool
    timestamp_utc: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def signable_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


@dataclass(frozen=True)
class DualPackageVerificationReport:
    transfer_manifest_signature_valid: bool
    plaintext_hash_valid: bool
    encrypted_hash_valid: bool
    decrypted_payload_hash_valid: bool | None
    inner_certificate_valid: bool | None
    details: dict[str, Any]

    @property
    def valid(self) -> bool:
        required = (
            self.transfer_manifest_signature_valid
            and self.plaintext_hash_valid
            and self.encrypted_hash_valid
        )
        if self.decrypted_payload_hash_valid is not None:
            required = required and self.decrypted_payload_hash_valid
        if self.inner_certificate_valid is not None:
            required = required and self.inner_certificate_valid
        return bool(required)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _canonical_zip_directory(source_dir: str | Path, zip_path: str | Path) -> None:
    source_dir = Path(source_dir)
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    fixed_dt = (2026, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(source_dir).as_posix()
            info = zipfile.ZipInfo(rel, date_time=fixed_dt)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())


def _write_signature(path: str | Path, signature: bytes) -> None:
    Path(path).write_text(base64.b64encode(signature).decode("ascii") + "\n", encoding="utf-8")


def _read_signature(path: str | Path) -> bytes:
    return base64.b64decode(Path(path).read_text(encoding="utf-8").strip())


def create_dual_evidence_package(
    *,
    result,
    output_dir: str | Path,
    signing_private_key_path: str | Path,
    recipient_public_key_path: str | Path,
    overlay_path: str | Path | None = None,
    command: str = "not_recorded",
    environment: dict[str, Any] | None = None,
    keep_canonical_directory: bool = False,
) -> TransferManifest:
    """Create matched plaintext and encrypted evidence packages.

    The canonical signed evidence package is built first, then zipped once.
    The plaintext ZIP is that canonical ZIP. The encrypted payload encrypts the
    exact same ZIP bytes. The transfer manifest binds both to the same hash.
    """
    output = Path(output_dir)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    canonical_dir = output / "canonical_evidence_package"
    package_and_sign_enforced_result(
        result=result,
        output_dir=canonical_dir,
        private_key_path=signing_private_key_path,
        overlay_path=overlay_path,
        command=command,
        environment=environment,
    )

    plaintext_zip = output / "operator_plaintext_package.zip"
    _canonical_zip_directory(canonical_dir, plaintext_zip)
    canonical_sha = file_hash(plaintext_zip)
    plaintext_sha = canonical_sha

    payload = encrypt_bytes_for_recipient(
        plaintext_zip.read_bytes(),
        recipient_public_key_path=recipient_public_key_path,
        aad_sha256=canonical_sha,
    )
    encrypted_path = output / "verifier_encrypted_package.r3enc.json"
    write_encrypted_payload(encrypted_path, payload)
    encrypted_sha = file_hash(encrypted_path)

    private_key = load_private_key(signing_private_key_path)
    transfer_public_key = private_key.public_key()
    write_public_key(output / "TRANSFER_PUBLIC_KEY.pem", transfer_public_key)

    envelope = read_json(canonical_dir / "EVIDENCE_ENVELOPE.json")
    manifest = TransferManifest(
        schema="rank3_dual_evidence_transfer_v1",
        transfer_mode="signed_plaintext_plus_encrypted_same_payload",
        canonical_package_name="operator_plaintext_package.zip",
        plaintext_package_name="operator_plaintext_package.zip",
        encrypted_package_name="verifier_encrypted_package.r3enc.json",
        canonical_package_sha256=canonical_sha,
        plaintext_package_sha256=plaintext_sha,
        encrypted_package_sha256=encrypted_sha,
        evidence_envelope_hash=stable_json_hash(envelope),
        certificate_public_key_sha256=file_hash(canonical_dir / "FRAMEWORK_PUBLIC_KEY.pem"),
        recipient_public_key_sha256=file_hash(recipient_public_key_path),
        encryption_algorithm=payload.algorithm,
        signature_algorithm="Ed25519",
        plaintext_and_encrypted_payload_are_same_canonical_package=True,
        timestamp_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    )
    write_json(output / "TRANSFER_MANIFEST.json", manifest)
    _write_signature(output / "TRANSFER_MANIFEST.sig", sign_bytes(private_key, manifest.signable_bytes()))

    with (output / "TRANSFER_SHA256SUMS.csv").open("w", encoding="utf-8") as handle:
        handle.write("sha256,relative_path\n")
        for rel in (
            "operator_plaintext_package.zip",
            "verifier_encrypted_package.r3enc.json",
            "TRANSFER_MANIFEST.json",
            "TRANSFER_MANIFEST.sig",
            "TRANSFER_PUBLIC_KEY.pem",
        ):
            handle.write(f"{file_hash(output / rel)},{rel}\n")

    if not keep_canonical_directory:
        shutil.rmtree(canonical_dir)

    return manifest


def verify_dual_evidence_package(
    transfer_dir: str | Path,
    *,
    recipient_private_key_path: str | Path | None = None,
    transfer_public_key_path: str | Path | None = None,
) -> DualPackageVerificationReport:
    transfer_dir = Path(transfer_dir)
    manifest_path = transfer_dir / "TRANSFER_MANIFEST.json"
    signature_path = transfer_dir / "TRANSFER_MANIFEST.sig"
    if transfer_public_key_path is None:
        transfer_public_key_path = transfer_dir / "TRANSFER_PUBLIC_KEY.pem"
    try:
        manifest = TransferManifest(**read_json(manifest_path))
        signature = _read_signature(signature_path)
        public_key = load_public_key(transfer_public_key_path)
        sig_valid = verify_signature(public_key, manifest.signable_bytes(), signature)
    except Exception as exc:
        return DualPackageVerificationReport(
            transfer_manifest_signature_valid=False,
            plaintext_hash_valid=False,
            encrypted_hash_valid=False,
            decrypted_payload_hash_valid=None,
            inner_certificate_valid=None,
            details={"reason": f"manifest/signature verification failed: {exc}"},
        )

    plaintext_path = transfer_dir / manifest.plaintext_package_name
    encrypted_path = transfer_dir / manifest.encrypted_package_name
    plaintext_hash_valid = plaintext_path.exists() and file_hash(plaintext_path) == manifest.plaintext_package_sha256 == manifest.canonical_package_sha256
    encrypted_hash_valid = encrypted_path.exists() and file_hash(encrypted_path) == manifest.encrypted_package_sha256

    decrypted_hash_valid: bool | None = None
    inner_certificate_valid: bool | None = None
    details: dict[str, Any] = {
        "canonical_package_sha256": manifest.canonical_package_sha256,
        "plaintext_package_sha256": manifest.plaintext_package_sha256,
        "encrypted_package_sha256": manifest.encrypted_package_sha256,
    }

    if recipient_private_key_path is not None and encrypted_path.exists():
        try:
            decrypted = decrypt_payload(
                read_encrypted_payload(encrypted_path),
                recipient_private_key_path=recipient_private_key_path,
            )
            # Use hashlib directly to avoid writing the decrypted bytes just to hash them.
            import hashlib
            raw_decrypted_sha = hashlib.sha256(decrypted).hexdigest()
            decrypted_hash_valid = raw_decrypted_sha == manifest.canonical_package_sha256
            details["decrypted_package_sha256"] = raw_decrypted_sha
            if decrypted_hash_valid:
                from .signing import verify_certificate
                with tempfile.TemporaryDirectory() as tmp:
                    zip_path = Path(tmp) / "decrypted.zip"
                    extract_dir = Path(tmp) / "decrypted_package"
                    zip_path.write_bytes(decrypted)
                    with zipfile.ZipFile(zip_path, "r") as zf:
                        zf.extractall(extract_dir)
                    inner_report = verify_certificate(extract_dir)
                    inner_certificate_valid = inner_report.valid
                    details["inner_certificate"] = inner_report.to_dict()
        except Exception as exc:
            decrypted_hash_valid = False
            details["decryption_error"] = str(exc)

    return DualPackageVerificationReport(
        transfer_manifest_signature_valid=sig_valid,
        plaintext_hash_valid=bool(plaintext_hash_valid),
        encrypted_hash_valid=bool(encrypted_hash_valid),
        decrypted_payload_hash_valid=decrypted_hash_valid,
        inner_certificate_valid=inner_certificate_valid,
        details=details,
    )
