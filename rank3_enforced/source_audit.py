from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any


FORBIDDEN_SOURCE_PATTERNS: tuple[str, ...] = (
    "setflags(write=True)",
    ".assoc[",
    "expected_result",
    "desired_result",
    "force_path_shortening",
    "force_path_lengthening",
    "projected_coordinate",
    "spring_layout",
)

WARNING_SOURCE_PATTERNS: tuple[str, ...] = (
    "attraction",
    "repulsion",
    "shorten",
    "lengthen",
    "midpoint",
    "success",
    "failure",
)


@dataclass(frozen=True)
class SourceAuditReport:
    object_name: str
    source_available: bool
    forbidden_hits: tuple[str, ...]
    warning_hits: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return len(self.forbidden_hits) == 0


def audit_object_source(obj: Any, *, object_name: str | None = None) -> SourceAuditReport:
    name = object_name or getattr(obj, "name", obj.__class__.__name__)
    try:
        source = inspect.getsource(obj.__class__ if not inspect.isfunction(obj) else obj)
    except (OSError, TypeError):
        return SourceAuditReport(
            object_name=name,
            source_available=False,
            forbidden_hits=(),
            warning_hits=("source_unavailable",),
        )

    forbidden_hits = tuple(pattern for pattern in FORBIDDEN_SOURCE_PATTERNS if pattern in source)
    warning_hits = tuple(pattern for pattern in WARNING_SOURCE_PATTERNS if pattern in source)
    return SourceAuditReport(
        object_name=name,
        source_available=True,
        forbidden_hits=forbidden_hits,
        warning_hits=warning_hits,
    )
