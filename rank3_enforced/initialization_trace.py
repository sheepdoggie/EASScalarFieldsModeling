from __future__ import annotations

from dataclasses import dataclass, field

from .fingerprints import stable_json_hash
from .soo_trace import SOOUpdateTrace


@dataclass(frozen=True)
class InitializationSourceTrace:
    """Immutable trace of the sealed support-origin initialization source."""

    mode: str
    start_sites: str
    source_rule: str
    source_hash: str
    support_hash: str
    source_l1: float
    source_l2: float
    nonzero_count: int
    support_nonzero_count: int
    vacuum_nonzero_count: int
    require_nonzero_support_activation: bool
    require_vacuum_zero_elsewhere: bool
    passed: bool
    details: dict[str, object] = field(default_factory=dict)

    def fingerprint(self) -> str:
        return stable_json_hash(self)


@dataclass(frozen=True)
class InitializationEpochReport:
    """Report for the initialization epoch before measurement readouts begin."""

    mode: str
    initialization_cycles: int
    measurement_starts_after_initialization: bool
    initial_phi_hash: str
    source_trace: InitializationSourceTrace
    phi_after_initialization_hash: str
    phi_previous_for_measurement_hash: str | None = None
    initial_two_ledger_hash: str | None = None
    settling_report_hash: str | None = None
    soo_trace_hashes: tuple[str, ...] = ()
    passed: bool = False
    details: dict[str, object] = field(default_factory=dict)

    def fingerprint(self) -> str:
        return stable_json_hash(self)


@dataclass(frozen=True)
class InitializationResult:
    phi_after_initialization: object
    report: InitializationEpochReport
    soo_traces: tuple[SOOUpdateTrace, ...] = ()
    phi_previous_for_measurement: object | None = None
    initial_two_ledger_report: object | None = None
    settling_report: object | None = None
