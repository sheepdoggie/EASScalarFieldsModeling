from __future__ import annotations

import json
from pathlib import Path

from rank3_enforced.capabilities import FRAMEWORK_CAPABILITIES, FRAMEWORK_RELEASE_LABEL, FRAMEWORK_VERSION
from rank3_enforced.signing import create_signing_keypair, load_private_key, sign_bytes
from rank3_enforced.version_guard import compute_framework_code_sha256, enforce_latest_release_guard


def test_release_guard_passes_once_and_then_uses_cache(tmp_path: Path):
    private_key = tmp_path / "release_private.pem"
    public_key = tmp_path / "release_public.pem"
    create_signing_keypair(private_key_path=private_key, public_key_path=public_key)

    manifest = {
        "project": "EASScalarFieldsModeling",
        "latest_framework_version": FRAMEWORK_VERSION,
        "latest_framework_release_label": FRAMEWORK_RELEASE_LABEL,
        "latest_framework_code_sha256": compute_framework_code_sha256(),
        "latest_framework_sha256": "not_used_when_code_hash_present",
        "required_capabilities": sorted(FRAMEWORK_CAPABILITIES),
    }
    manifest_path = tmp_path / "FRAMEWORK_RELEASE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    sig_path = tmp_path / "FRAMEWORK_RELEASE_MANIFEST.sig"
    sig_path.write_bytes(sign_bytes(load_private_key(private_key), manifest_path.read_bytes()))
    cache = tmp_path / "cache.json"

    first = enforce_latest_release_guard(
        manifest_url=str(manifest_path),
        signature_url=str(sig_path),
        public_key_url=str(public_key),
        cache_path=cache,
        force_refresh=True,
    )
    assert first.passed
    assert not first.used_cache
    assert cache.exists()

    # Delete the signature source. A second call should still pass from the
    # run-environment cache without re-reading the release source.
    sig_path.unlink()
    second = enforce_latest_release_guard(
        manifest_url=str(manifest_path),
        signature_url=str(sig_path),
        public_key_url=str(public_key),
        cache_path=cache,
    )
    assert second.passed
    assert second.used_cache


def test_release_guard_rejects_wrong_code_hash(tmp_path: Path):
    private_key = tmp_path / "release_private.pem"
    public_key = tmp_path / "release_public.pem"
    create_signing_keypair(private_key_path=private_key, public_key_path=public_key)
    manifest = {
        "project": "EASScalarFieldsModeling",
        "latest_framework_version": FRAMEWORK_VERSION,
        "latest_framework_release_label": FRAMEWORK_RELEASE_LABEL,
        "latest_framework_code_sha256": "0" * 64,
        "required_capabilities": sorted(FRAMEWORK_CAPABILITIES),
    }
    manifest_path = tmp_path / "FRAMEWORK_RELEASE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    sig_path = tmp_path / "FRAMEWORK_RELEASE_MANIFEST.sig"
    sig_path.write_bytes(sign_bytes(load_private_key(private_key), manifest_path.read_bytes()))

    report = enforce_latest_release_guard(
        mode="warn",
        manifest_url=str(manifest_path),
        signature_url=str(sig_path),
        public_key_url=str(public_key),
        cache_path=tmp_path / "bad_cache.json",
        force_refresh=True,
    )
    assert not report.passed
    assert any("code hash mismatch" in e for e in report.errors)


def test_release_guard_accepts_rank3_release_dir(tmp_path: Path, monkeypatch):
    private_key = tmp_path / "release_private.pem"
    public_key = tmp_path / "FRAMEWORK_RELEASE_PUBLIC_KEY.pem"
    create_signing_keypair(private_key_path=private_key, public_key_path=public_key)
    manifest = {
        "project": "EASScalarFieldsModeling",
        "latest_framework_version": FRAMEWORK_VERSION,
        "latest_framework_release_label": FRAMEWORK_RELEASE_LABEL,
        "latest_framework_code_sha256": compute_framework_code_sha256(),
        "required_capabilities": sorted(FRAMEWORK_CAPABILITIES),
    }
    manifest_path = tmp_path / "FRAMEWORK_RELEASE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    sig_path = tmp_path / "FRAMEWORK_RELEASE_MANIFEST.sig"
    sig_path.write_bytes(sign_bytes(load_private_key(private_key), manifest_path.read_bytes()))
    monkeypatch.setenv("RANK3_RELEASE_DIR", str(tmp_path))
    report = enforce_latest_release_guard(cache_path=tmp_path / "cache_dir_env.json", force_refresh=True)
    assert report.passed
    assert report.manifest_url.endswith("FRAMEWORK_RELEASE_MANIFEST.json")
