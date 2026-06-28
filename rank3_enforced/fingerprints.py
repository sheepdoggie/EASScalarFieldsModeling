from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import numpy as np


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return {
            "array_hash": array_hash(value),
            "shape": tuple(int(x) for x in value.shape),
            "dtype": str(value.dtype),
        }
    if hasattr(value, "value"):
        return value.value
    return str(value)


def stable_json_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=_json_default).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def array_hash(array: np.ndarray) -> str:
    arr = np.asarray(array)
    digest = hashlib.sha256()
    digest.update(str(arr.dtype).encode("utf-8"))
    digest.update(json.dumps(tuple(int(x) for x in arr.shape)).encode("utf-8"))
    digest.update(np.ascontiguousarray(arr).tobytes())
    return digest.hexdigest()


def object_source_hash(obj: Any) -> str:
    try:
        source = inspect.getsource(obj)
    except (OSError, TypeError):
        source = repr(obj)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def file_hash(path: str | Path) -> str:
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_hash(root: str | Path, *, suffixes: tuple[str, ...] = (".py",)) -> str:
    root = Path(root)
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        rel = path.relative_to(root).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(file_hash(path).encode("utf-8"))
    return digest.hexdigest()
