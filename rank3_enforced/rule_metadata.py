from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RuleStatus(str, Enum):
    ADMITTED = "admitted"
    CANDIDATE = "candidate"
    CONTROL = "control"
    DEMONSTRATION = "demonstration"
    REJECTED = "rejected"


class AdmissionVerdict(str, Enum):
    ADMITTED = "Admitted"
    CONTROL = "Control"
    TERMINAL = "Terminal"
    AMBIGUOUS = "Ambiguous"
    REJECTED = "Rejected"


@dataclass(frozen=True)
class RuleMetadata:
    """
    Required metadata for any rule supplied to the enforced runner.

    A rule without metadata may still be used by the raw geometry engine, but it
    cannot be used by the certified/enforced API.
    """

    name: str
    version: str
    status: RuleStatus
    source_hash: str
    allowed_for_certified_runs: bool = False
    notes: str = ""


def get_rule_metadata(rule: Any) -> RuleMetadata:
    meta = getattr(rule, "metadata", None)
    if isinstance(meta, RuleMetadata):
        return meta

    meta = getattr(rule, "rule_metadata", None)
    if isinstance(meta, RuleMetadata):
        return meta

    raise TypeError(
        f"Rule {rule!r} does not expose RuleMetadata via .metadata or .rule_metadata."
    )


def require_rule_status(
    *,
    metadata: RuleMetadata,
    allowed_statuses: tuple[RuleStatus, ...],
    context: str,
) -> None:
    if metadata.status not in allowed_statuses:
        allowed = ", ".join(status.value for status in allowed_statuses)
        raise ValueError(
            f"{context}: rule {metadata.name!r} has status {metadata.status.value!r}; "
            f"allowed statuses are: {allowed}."
        )
