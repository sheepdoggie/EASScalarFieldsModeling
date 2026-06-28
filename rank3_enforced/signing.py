from __future__ import annotations

from pathlib import Path
import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .certificates import (
    CertificateRecord,
    EvidenceEnvelope,
    VerificationReport,
    build_evidence_envelope,
    canonical_json_bytes,
    collect_file_hashes,
    package_hash_from_file_hashes,
    read_json,
    write_json,
    write_sha256sums,
)
from .fingerprints import file_hash, stable_json_hash


def generate_ed25519_private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def write_private_key(path: str | Path, private_key: Ed25519PrivateKey) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )


def write_public_key(path: str | Path, public_key: Ed25519PublicKey) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def load_private_key(path: str | Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("Private key must be an Ed25519 private key.")
    return key


def load_public_key(path: str | Path) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(Path(path).read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError("Public key must be an Ed25519 public key.")
    return key


def public_key_hash(public_key_path: str | Path) -> str:
    return file_hash(public_key_path)


def sign_bytes(private_key: Ed25519PrivateKey, payload: bytes) -> bytes:
    return private_key.sign(payload)


def verify_signature(public_key: Ed25519PublicKey, payload: bytes, signature: bytes) -> bool:
    try:
        public_key.verify(signature, payload)
        return True
    except InvalidSignature:
        return False


def create_signing_keypair(*, private_key_path: str | Path, public_key_path: str | Path) -> None:
    private_key = generate_ed25519_private_key()
    write_private_key(private_key_path, private_key)
    write_public_key(public_key_path, private_key.public_key())


def sign_existing_package(
    *,
    package_dir: str | Path,
    private_key_path: str | Path,
    public_key_path: str | Path,
    result_context: dict[str, object] | None = None,
) -> EvidenceEnvelope:
    """Sign a package that already contains EVIDENCE_ENVELOPE_INPUT.json.

    Most callers should use package_and_sign_enforced_result instead. This
    function is useful when a packaging step has already produced all files and
    an envelope input.
    """
    package_dir = Path(package_dir)
    private_key = load_private_key(private_key_path)
    public_key = private_key.public_key()
    write_public_key(package_dir / "FRAMEWORK_PUBLIC_KEY.pem", public_key)
    envelope_payload = read_json(package_dir / "EVIDENCE_ENVELOPE_INPUT.json")
    envelope = EvidenceEnvelope(**envelope_payload)
    signature = sign_bytes(private_key, envelope.signable_bytes())
    write_json(package_dir / "EVIDENCE_ENVELOPE.json", envelope)
    (package_dir / "EVIDENCE_ENVELOPE.sig").write_text(base64.b64encode(signature).decode("ascii") + "\n", encoding="utf-8")
    cert = CertificateRecord(
        certificate_schema="rank3_certificate_v1",
        certificate_status="valid_framework_certificate",
        signature_algorithm="Ed25519",
        envelope_hash=envelope.fingerprint(),
        public_key_hash=file_hash(package_dir / "FRAMEWORK_PUBLIC_KEY.pem"),
        run_id=envelope.run_id,
        run_kind=envelope.run_kind,
        external_verdict=envelope.external_verdict,
        base_gate_passed=envelope.base_gate_passed,
        admitted=envelope.admitted,
        certifies="provenance_and_framework_execution_integrity",
        timestamp_utc=envelope.timestamp_utc,
    )
    write_json(package_dir / "CERTIFICATE.json", cert)
    write_sha256sums(package_dir, envelope.file_hashes)
    return envelope


def sign_enforced_run_package(
    *,
    package_dir: str | Path,
    result,
    private_key_path: str | Path,
    command_hash: str,
    environment_hash: str,
    rule_registry_hash: str,
    readout_registry_hash: str,
    model_type_registry_hash: str,
    framework_version: str = "0.1.0",
) -> EvidenceEnvelope:
    package_dir = Path(package_dir)
    private_key = load_private_key(private_key_path)
    public_key = private_key.public_key()
    write_public_key(package_dir / "FRAMEWORK_PUBLIC_KEY.pem", public_key)
    envelope = build_evidence_envelope(
        result=result,
        package_root=package_dir,
        command_hash=command_hash,
        environment_hash=environment_hash,
        rule_registry_hash=rule_registry_hash,
        readout_registry_hash=readout_registry_hash,
        model_type_registry_hash=model_type_registry_hash,
        framework_version=framework_version,
    )
    signature = sign_bytes(private_key, envelope.signable_bytes())
    write_json(package_dir / "EVIDENCE_ENVELOPE.json", envelope)
    (package_dir / "EVIDENCE_ENVELOPE.sig").write_text(base64.b64encode(signature).decode("ascii") + "\n", encoding="utf-8")
    cert = CertificateRecord(
        certificate_schema="rank3_certificate_v1",
        certificate_status="valid_framework_certificate",
        signature_algorithm="Ed25519",
        envelope_hash=envelope.fingerprint(),
        public_key_hash=file_hash(package_dir / "FRAMEWORK_PUBLIC_KEY.pem"),
        run_id=envelope.run_id,
        run_kind=envelope.run_kind,
        external_verdict=envelope.external_verdict,
        base_gate_passed=envelope.base_gate_passed,
        admitted=envelope.admitted,
        certifies="provenance_and_framework_execution_integrity",
        timestamp_utc=envelope.timestamp_utc,
    )
    write_json(package_dir / "CERTIFICATE.json", cert)
    write_sha256sums(package_dir, envelope.file_hashes)
    return envelope


def verify_certificate(package_dir: str | Path, *, public_key_path: str | Path | None = None) -> VerificationReport:
    package_dir = Path(package_dir)
    envelope_path = package_dir / "EVIDENCE_ENVELOPE.json"
    signature_path = package_dir / "EVIDENCE_ENVELOPE.sig"
    if public_key_path is None:
        public_key_path = package_dir / "FRAMEWORK_PUBLIC_KEY.pem"
    missing = tuple(
        rel for rel in ("EVIDENCE_ENVELOPE.json", "EVIDENCE_ENVELOPE.sig", "FRAMEWORK_PUBLIC_KEY.pem")
        if not (package_dir / rel).exists()
    )
    if missing:
        return VerificationReport(
            certificate_status="missing_or_invalid",
            signature_valid=False,
            file_hashes_valid=False,
            package_hash_valid=False,
            unexpected_files=(),
            missing_files=missing,
            details={"reason": "required certificate files missing"},
        )
    envelope_data = read_json(envelope_path)
    envelope = EvidenceEnvelope(**envelope_data)
    signature = base64.b64decode(signature_path.read_text(encoding="utf-8").strip())
    public_key = load_public_key(public_key_path)
    signature_valid = verify_signature(public_key, envelope.signable_bytes(), signature)

    observed_hashes = collect_file_hashes(package_dir)
    expected_hashes = dict(envelope.file_hashes)
    unexpected = tuple(sorted(set(observed_hashes) - set(expected_hashes)))
    absent = tuple(sorted(set(expected_hashes) - set(observed_hashes)))
    mismatches = {
        rel: {"expected": expected_hashes[rel], "observed": observed_hashes.get(rel)}
        for rel in sorted(set(expected_hashes) & set(observed_hashes))
        if expected_hashes[rel] != observed_hashes[rel]
    }
    file_hashes_valid = not unexpected and not absent and not mismatches
    observed_package_hash = package_hash_from_file_hashes(observed_hashes)
    package_hash_valid = observed_package_hash == envelope.package_hash
    status = "valid_framework_certificate" if signature_valid and file_hashes_valid and package_hash_valid else "missing_or_invalid"
    return VerificationReport(
        certificate_status=status,
        signature_valid=signature_valid,
        file_hashes_valid=file_hashes_valid,
        package_hash_valid=package_hash_valid,
        unexpected_files=unexpected,
        missing_files=absent,
        details={
            "mismatches": mismatches,
            "observed_package_hash": observed_package_hash,
            "expected_package_hash": envelope.package_hash,
            "run_id": envelope.run_id,
            "run_kind": envelope.run_kind,
            "external_verdict": envelope.external_verdict,
            "base_gate_passed": envelope.base_gate_passed,
            "admitted": envelope.admitted,
        },
    )
