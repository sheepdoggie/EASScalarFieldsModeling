from __future__ import annotations

from pathlib import Path

from rank3_enforced import run_declarative_overlay
from rank3_enforced.package_manifest import package_and_sign_enforced_result
from rank3_enforced.signing import create_signing_keypair, verify_certificate


def test_signed_package_verifies_and_tamper_fails(tmp_path: Path) -> None:
    private_key = tmp_path / "private_key.pem"
    public_key = tmp_path / "public_key.pem"
    create_signing_keypair(private_key_path=private_key, public_key_path=public_key)

    overlay = Path("overlays/minimal_control_overlay.json")
    result = run_declarative_overlay(overlay)
    output = tmp_path / "signed_package"
    package_and_sign_enforced_result(
        result=result,
        output_dir=output,
        private_key_path=private_key,
        overlay_path=overlay,
        command="pytest certificate smoke test",
    )

    report = verify_certificate(output)
    assert report.valid
    assert report.signature_valid
    assert report.file_hashes_valid
    assert report.package_hash_valid

    # Post-signature tampering must invalidate the certificate.
    (output / "readout_results.json").write_text("{}\n", encoding="utf-8")
    tampered = verify_certificate(output)
    assert not tampered.valid
    assert not tampered.file_hashes_valid
