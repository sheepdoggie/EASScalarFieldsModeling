from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .capabilities import FRAMEWORK_RELEASE_LABEL, FRAMEWORK_VERSION
from .fingerprints import file_hash, stable_json_hash
from .version_guard import compute_framework_code_sha256


_CODE_ROOTS = (
    "rank3_enforced",
    "scalar_field_geometry.py",
    "run_declarative_overlay.py",
    "run_signed_declarative_overlay.py",
    "run_dual_declarative_overlay.py",
    "pyproject.toml",
)


@dataclass(frozen=True)
class ReleaseIdentityReport:
    schema: str
    passed: bool
    repo_root: str
    manifest_path: str
    framework_zip_path: str
    framework_tar_gz_path: str | None
    latest_framework_version: str | None
    latest_framework_release_label: str | None
    manifest_framework_sha256: str | None
    actual_framework_sha256: str | None
    manifest_framework_size_bytes: int | None
    actual_framework_size_bytes: int | None
    manifest_code_sha256: str | None
    actual_source_tree_code_sha256: str
    actual_framework_zip_code_sha256: str | None
    accepted_framework_code_sha256: tuple[str, ...]
    manifest_tar_gz_sha256: str | None
    actual_tar_gz_sha256: str | None
    required_files_in_zip_missing: tuple[str, ...]
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _strip_zip_root(name: str) -> str:
    parts = Path(name).parts
    if not parts:
        return name
    if parts[0] in {"enforceable_rank3_modeling", "EASScalarFieldsModeling"} or parts[0].startswith("EASScalarFieldsModeling_"):
        return "/".join(parts[1:])
    return name


def _zip_code_entries(zip_path: str | Path) -> list[tuple[str, str]]:
    zip_path = Path(zip_path)
    entries: list[tuple[str, str]] = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            rel = _strip_zip_root(info.filename)
            include = False
            if rel.startswith("rank3_enforced/") and rel.endswith(".py") and "__pycache__" not in rel.split("/"):
                include = True
            elif rel in _CODE_ROOTS and rel != "rank3_enforced":
                include = True
            if not include:
                continue
            import hashlib
            digest = hashlib.sha256(zf.read(info.filename)).hexdigest()
            entries.append((rel, digest))
    return sorted(set(entries))


def compute_framework_zip_code_sha256(zip_path: str | Path) -> str:
    """Compute the same code identity hash from a release ZIP.

    The internal release archive is usually rooted at ``enforceable_rank3_modeling/``.
    This function strips that archive root and hashes the same identity file set used
    by ``version_guard.compute_framework_code_sha256`` for an installed source tree.
    """
    return stable_json_hash(_zip_code_entries(zip_path))


def load_manifest(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("release manifest must be a JSON object")
    return payload


def check_release_identity(
    *,
    repo_root: str | Path = ".",
    manifest_path: str | Path | None = None,
    framework_zip_path: str | Path | None = None,
    framework_tar_gz_path: str | Path | None = None,
) -> ReleaseIdentityReport:
    repo_root = Path(repo_root).expanduser().resolve()
    manifest_path = Path(manifest_path or repo_root / "releases/current/FRAMEWORK_RELEASE_MANIFEST.json").expanduser().resolve()
    manifest = load_manifest(manifest_path)
    if framework_zip_path is None:
        rel = manifest.get("framework_zip_relative_path") or ""
        framework_zip_path = repo_root / rel if rel else repo_root / "releases/current" / str(manifest.get("latest_framework_filename", ""))
    framework_zip_path = Path(framework_zip_path).expanduser().resolve()
    if framework_tar_gz_path is None:
        tar_name = manifest.get("latest_framework_tar_gz_filename")
        if tar_name:
            framework_tar_gz_path = framework_zip_path.parent / str(tar_name)
    framework_tar_gz_path_obj = Path(framework_tar_gz_path).expanduser().resolve() if framework_tar_gz_path else None

    errors: list[str] = []
    actual_zip_sha: str | None = None
    actual_zip_size: int | None = None
    actual_zip_code: str | None = None
    actual_tar_sha: str | None = None
    missing_required: list[str] = []

    actual_tree_code = compute_framework_code_sha256(repo_root)

    if framework_zip_path.exists():
        actual_zip_sha = file_hash(framework_zip_path)
        actual_zip_size = framework_zip_path.stat().st_size
        actual_zip_code = compute_framework_zip_code_sha256(framework_zip_path)
        with zipfile.ZipFile(framework_zip_path) as zf:
            names = set(zf.namelist())
        for required in manifest.get("required_files_in_zip", ()):
            if str(required) not in names:
                missing_required.append(str(required))
    else:
        errors.append(f"framework ZIP missing: {framework_zip_path}")

    if framework_tar_gz_path_obj and framework_tar_gz_path_obj.exists():
        actual_tar_sha = file_hash(framework_tar_gz_path_obj)
    elif framework_tar_gz_path_obj:
        errors.append(f"framework TAR.GZ missing: {framework_tar_gz_path_obj}")

    latest_version = manifest.get("latest_framework_version")
    latest_label = manifest.get("latest_framework_release_label")
    manifest_zip_sha = manifest.get("latest_framework_sha256")
    manifest_zip_size = manifest.get("latest_framework_size_bytes")
    manifest_code = manifest.get("latest_framework_code_sha256")
    accepted_code = tuple(str(x) for x in manifest.get("accepted_framework_code_sha256", ()))
    manifest_tar_sha = manifest.get("latest_framework_tar_gz_sha256")

    if str(latest_version) != FRAMEWORK_VERSION:
        errors.append(f"manifest version mismatch: expected {FRAMEWORK_VERSION}, observed {latest_version}")
    if str(latest_label) != FRAMEWORK_RELEASE_LABEL:
        errors.append(f"manifest release label mismatch: expected {FRAMEWORK_RELEASE_LABEL}, observed {latest_label}")
    if actual_zip_sha and manifest_zip_sha != actual_zip_sha:
        errors.append(f"framework ZIP hash mismatch: manifest {manifest_zip_sha}, actual {actual_zip_sha}")
    if actual_zip_size is not None and manifest_zip_size != actual_zip_size:
        errors.append(f"framework ZIP size mismatch: manifest {manifest_zip_size}, actual {actual_zip_size}")
    if manifest_code != actual_tree_code:
        errors.append(f"source-tree code hash mismatch: manifest {manifest_code}, actual {actual_tree_code}")
    if actual_zip_code and manifest_code != actual_zip_code:
        errors.append(f"framework ZIP code hash mismatch: manifest {manifest_code}, actual {actual_zip_code}")
    if manifest_code and manifest_code not in accepted_code:
        errors.append("latest_framework_code_sha256 is not listed in accepted_framework_code_sha256")
    if actual_tar_sha and manifest_tar_sha != actual_tar_sha:
        errors.append(f"framework TAR.GZ hash mismatch: manifest {manifest_tar_sha}, actual {actual_tar_sha}")
    if missing_required:
        errors.append("framework ZIP missing required files: " + ", ".join(missing_required))

    return ReleaseIdentityReport(
        schema="rank3_release_identity_report_v1",
        passed=not errors,
        repo_root=str(repo_root),
        manifest_path=str(manifest_path),
        framework_zip_path=str(framework_zip_path),
        framework_tar_gz_path=str(framework_tar_gz_path_obj) if framework_tar_gz_path_obj else None,
        latest_framework_version=str(latest_version) if latest_version is not None else None,
        latest_framework_release_label=str(latest_label) if latest_label is not None else None,
        manifest_framework_sha256=str(manifest_zip_sha) if manifest_zip_sha is not None else None,
        actual_framework_sha256=actual_zip_sha,
        manifest_framework_size_bytes=int(manifest_zip_size) if isinstance(manifest_zip_size, int) else None,
        actual_framework_size_bytes=actual_zip_size,
        manifest_code_sha256=str(manifest_code) if manifest_code is not None else None,
        actual_source_tree_code_sha256=actual_tree_code,
        actual_framework_zip_code_sha256=actual_zip_code,
        accepted_framework_code_sha256=accepted_code,
        manifest_tar_gz_sha256=str(manifest_tar_sha) if manifest_tar_sha is not None else None,
        actual_tar_gz_sha256=actual_tar_sha,
        required_files_in_zip_missing=tuple(missing_required),
        errors=tuple(errors),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check release manifest/source/archive identity self-consistency.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--framework-zip", default=None)
    parser.add_argument("--framework-tar-gz", default=None)
    parser.add_argument("--output", default=None, help="Optional JSON report path.")
    args = parser.parse_args(argv)
    report = check_release_identity(
        repo_root=args.repo_root,
        manifest_path=args.manifest,
        framework_zip_path=args.framework_zip,
        framework_tar_gz_path=args.framework_tar_gz,
    )
    payload = report.to_dict()
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).expanduser().write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
