from __future__ import annotations

from dataclasses import dataclass

from .rule_metadata import AdmissionVerdict


@dataclass(frozen=True)
class BaseGateReport:
    source_provenance_passed: bool
    verdict_independence_passed: bool
    blind_generation_projection_separation_passed: bool
    negative_controls_passed: bool
    leakage_manipulation_checks_passed: bool
    external_admission_verdict: AdmissionVerdict
    details: dict[str, object]

    @property
    def passed(self) -> bool:
        return (
            self.source_provenance_passed
            and self.verdict_independence_passed
            and self.blind_generation_projection_separation_passed
            and self.negative_controls_passed
            and self.leakage_manipulation_checks_passed
            and self.external_admission_verdict == AdmissionVerdict.ADMITTED
        )
