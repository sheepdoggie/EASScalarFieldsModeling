from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .capabilities import (
    FRAMEWORK_RELEASE_LABEL,
    FRAMEWORK_VERSION,
    capability_report,
)
from .fingerprints import file_hash, stable_json_hash
from .release_manifest import (
    DEFAULT_RELEASE_MANIFEST_URL,
    DEFAULT_RELEASE_PUBLIC_KEY_URL,
    DEFAULT_RELEASE_SIGNATURE_URL,
    ReleaseManifestError,
    verify_release_manifest_sources,
)

RELEASE_GUARD_CACHE_FILENAME = ".rank3_release_guard_passed.json"


@dataclass(frozen=True)
class LocalFrameworkIdentity:
    framework_version: str
    framework_release_label: str
    package_root: str
    code_sha256: str
    framework_zip_path: str | None
    framework_zip_sha256: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VersionGuardReport:
    schema: str
    passed: bool
    mode: str
    source: str
    used_cache: bool
    checked_at_unix: float
    cache_path: str
    manifest_url: str
    signature_url: str
    public_key_url: str
    local_identity: dict[str, Any]
    release_manifest: dict[str, Any] | None
    capability_report: dict[str, Any]
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _code_files_for_identity(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for rel in (
        "rank3_enforced",
        "scalar_field_geometry.py",
        "run_declarative_overlay.py",
        "run_signed_declarative_overlay.py",
        "run_dual_declarative_overlay.py",
        "pyproject.toml",
    ):
        path = root / rel
        if path.is_dir():
            candidates.extend(sorted(p for p in path.rglob("*.py") if "__pycache__" not in p.parts))
        elif path.is_file():
            candidates.append(path)
    return sorted(set(candidates), key=lambda p: p.relative_to(root).as_posix())


def compute_framework_code_sha256(root: str | Path | None = None) -> str:
    root = Path(root) if root is not None else _package_root()
    pairs = []
    for path in _code_files_for_identity(root):
        pairs.append((path.relative_to(root).as_posix(), file_hash(path)))
    return stable_json_hash(pairs)


def local_framework_identity(*, framework_zip_path: str | Path | None = None) -> LocalFrameworkIdentity:
    root = _package_root()
    zip_sha: str | None = None
    zip_path_str: str | None = None
    if framework_zip_path is None:
        framework_zip_path = os.environ.get("RANK3_FRAMEWORK_ZIP")
    if framework_zip_path:
        zip_path = Path(framework_zip_path).expanduser()
        zip_path_str = str(zip_path)
        if zip_path.exists():
            zip_sha = file_hash(zip_path)
    return LocalFrameworkIdentity(
        framework_version=FRAMEWORK_VERSION,
        framework_release_label=FRAMEWORK_RELEASE_LABEL,
        package_root=str(root),
        code_sha256=compute_framework_code_sha256(root),
        framework_zip_path=zip_path_str,
        framework_zip_sha256=zip_sha,
    )


def _cache_path(cache_path: str | Path | None = None, cache_dir: str | Path | None = None) -> Path:
    if cache_path is None:
        cache_path = os.environ.get("RANK3_VERSION_GUARD_CACHE")
    if cache_path:
        return Path(cache_path).expanduser()
    if cache_dir is None:
        cache_dir = os.environ.get("RANK3_RUN_ENV_DIR") or os.getcwd()
    return Path(cache_dir).expanduser() / RELEASE_GUARD_CACHE_FILENAME


def _report_from_cache(path: Path, *, local: LocalFrameworkIdentity, ttl_seconds: int) -> VersionGuardReport | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        report = VersionGuardReport(**payload)
    except Exception:
        return None
    if not report.passed:
        return None
    age = time.time() - float(report.checked_at_unix)
    if ttl_seconds >= 0 and age > ttl_seconds:
        return None
    cached_local = report.local_identity or {}
    if cached_local.get("code_sha256") != local.code_sha256:
        return None
    return VersionGuardReport(
        **{**report.to_dict(), "used_cache": True, "source": "cache"}
    )


def _write_cache(path: Path, report: VersionGuardReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def enforce_latest_release_guard(
    *,
    run_kind: str = "candidate",
    mode: str | None = None,
    manifest_url: str | None = None,
    signature_url: str | None = None,
    public_key_url: str | None = None,
    cache_path: str | Path | None = None,
    cache_dir: str | Path | None = None,
    ttl_seconds: int | None = None,
    force_refresh: bool | None = None,
    framework_zip_path: str | Path | None = None,
) -> VersionGuardReport:
    """Fail closed unless the installed framework matches the signed latest manifest.

    The first successful check writes a run-environment cache file. Subsequent
    process executions in the same run environment reuse the cached pass as long
    as the local code fingerprint has not changed and the cache TTL has not
    expired. This avoids repeated GitHub checks in multi-overlay loops.
    """
    mode = (mode or os.environ.get("RANK3_RELEASE_GUARD", "required")).lower()
    if run_kind == "archive_reproduction" and mode == "required":
        mode = "warn"
    if mode in {"off", "disabled", "0", "false"}:
        local = local_framework_identity(framework_zip_path=framework_zip_path)
        cap = capability_report(())
        return VersionGuardReport(
            schema="rank3_release_guard_v1",
            passed=True,
            mode="off",
            source="disabled",
            used_cache=False,
            checked_at_unix=time.time(),
            cache_path=str(_cache_path(cache_path, cache_dir)),
            manifest_url=manifest_url or DEFAULT_RELEASE_MANIFEST_URL,
            signature_url=signature_url or DEFAULT_RELEASE_SIGNATURE_URL,
            public_key_url=public_key_url or DEFAULT_RELEASE_PUBLIC_KEY_URL,
            local_identity=local.to_dict(),
            release_manifest=None,
            capability_report=cap.to_dict(),
            errors=("release guard disabled by environment/mode",),
        )

    manifest_url = manifest_url or os.environ.get("RANK3_RELEASE_MANIFEST_URL") or DEFAULT_RELEASE_MANIFEST_URL
    signature_url = signature_url or os.environ.get("RANK3_RELEASE_SIGNATURE_URL") or DEFAULT_RELEASE_SIGNATURE_URL
    public_key_url = public_key_url or os.environ.get("RANK3_RELEASE_PUBLIC_KEY_URL") or DEFAULT_RELEASE_PUBLIC_KEY_URL
    ttl_seconds = int(os.environ.get("RANK3_RELEASE_GUARD_CACHE_TTL_SECONDS", ttl_seconds if ttl_seconds is not None else 86400))
    force_refresh = bool(
        force_refresh
        if force_refresh is not None
        else os.environ.get("RANK3_RELEASE_GUARD_FORCE_REFRESH", "0") in {"1", "true", "yes"}
    )
    cache = _cache_path(cache_path, cache_dir)
    local = local_framework_identity(framework_zip_path=framework_zip_path)

    if not force_refresh:
        cached = _report_from_cache(cache, local=local, ttl_seconds=ttl_seconds)
        if cached is not None:
            return cached

    errors: list[str] = []
    release_dict: dict[str, Any] | None = None
    cap_report = capability_report(())
    try:
        verification = verify_release_manifest_sources(
            manifest_source=manifest_url,
            signature_source=signature_url,
            public_key_source=public_key_url,
        )
        release_dict = verification.to_dict()
        if not verification.manifest_signature_valid:
            errors.append("release manifest signature invalid")
        manifest = verification.details.get("manifest", {})
        required_capabilities = tuple(str(x) for x in manifest.get("required_capabilities", ()))
        cap_report = capability_report(required_capabilities)
        if not cap_report.passed:
            errors.append("missing required capabilities: " + ", ".join(cap_report.missing_capabilities))
        expected_code_hash = manifest.get("latest_framework_code_sha256")
        accepted_code_hashes = set(str(x) for x in manifest.get("accepted_framework_code_sha256", ()))
        if expected_code_hash:
            accepted_code_hashes.add(str(expected_code_hash))
        expected_zip_hash = manifest.get("latest_framework_sha256")
        if accepted_code_hashes:
            if local.code_sha256 not in accepted_code_hashes:
                errors.append(
                    "local framework code hash mismatch: "
                    f"expected one of {sorted(accepted_code_hashes)}, observed {local.code_sha256}"
                )
        elif local.framework_zip_sha256 and expected_zip_hash:
            if local.framework_zip_sha256 != expected_zip_hash:
                errors.append(
                    "local framework ZIP hash mismatch: "
                    f"expected {expected_zip_hash}, observed {local.framework_zip_sha256}"
                )
        else:
            errors.append(
                "release manifest has no latest_framework_code_sha256 and no local framework ZIP hash was available"
            )
    except ReleaseManifestError as exc:
        errors.append(str(exc))
    except Exception as exc:
        errors.append(f"unexpected release guard error: {exc}")

    passed = not errors
    report = VersionGuardReport(
        schema="rank3_release_guard_v1",
        passed=passed,
        mode=mode,
        source="remote_or_configured_manifest",
        used_cache=False,
        checked_at_unix=time.time(),
        cache_path=str(cache),
        manifest_url=manifest_url,
        signature_url=signature_url,
        public_key_url=public_key_url,
        local_identity=local.to_dict(),
        release_manifest=release_dict,
        capability_report=cap_report.to_dict(),
        errors=tuple(errors),
    )
    if passed:
        _write_cache(cache, report)
        return report
    if mode in {"warn", "warning"}:
        return report
    raise RuntimeError("Latest-framework release guard failed:\n" + "\n".join(f"- {e}" for e in errors))
