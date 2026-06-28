from __future__ import annotations

from pathlib import Path

from rank3_enforced import run_declarative_overlay
from rank3_enforced.dual_package import create_dual_evidence_package, verify_dual_evidence_package
from rank3_enforced.encryption import create_encryption_keypair
from rank3_enforced.signing import create_signing_keypair


def test_dual_plaintext_and_encrypted_packages_match(tmp_path: Path) -> None:
    signing_private = tmp_path / "signing_private.pem"
    signing_public = tmp_path / "signing_public.pem"
    recipient_private = tmp_path / "recipient_private.pem"
    recipient_public = tmp_path / "recipient_public.pem"
    create_signing_keypair(private_key_path=signing_private, public_key_path=signing_public)
    create_encryption_keypair(private_key_path=recipient_private, public_key_path=recipient_public)

    result = run_declarative_overlay(Path("overlays/minimal_control_overlay.json"))
    out = tmp_path / "dual_output"
    manifest = create_dual_evidence_package(
        result=result,
        output_dir=out,
        signing_private_key_path=signing_private,
        recipient_public_key_path=recipient_public,
        overlay_path=Path("overlays/minimal_control_overlay.json"),
        command="pytest dual package smoke test",
    )

    assert (out / "operator_plaintext_package.zip").exists()
    assert (out / "verifier_encrypted_package.r3enc.json").exists()
    assert (out / "TRANSFER_MANIFEST.json").exists()
    assert (out / "TRANSFER_MANIFEST.sig").exists()
    assert manifest.plaintext_and_encrypted_payload_are_same_canonical_package

    public_report = verify_dual_evidence_package(out)
    assert public_report.transfer_manifest_signature_valid
    assert public_report.plaintext_hash_valid
    assert public_report.encrypted_hash_valid

    private_report = verify_dual_evidence_package(out, recipient_private_key_path=recipient_private)
    assert private_report.valid
    assert private_report.decrypted_payload_hash_valid
    assert private_report.inner_certificate_valid

    # Tampering with the plaintext ZIP must invalidate the plaintext hash check.
    with (out / "operator_plaintext_package.zip").open("ab") as handle:
        handle.write(b"tamper")
    tampered = verify_dual_evidence_package(out, recipient_private_key_path=recipient_private)
    assert not tampered.valid
    assert not tampered.plaintext_hash_valid
