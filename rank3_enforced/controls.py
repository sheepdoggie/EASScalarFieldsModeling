from __future__ import annotations

from dataclasses import dataclass

import numpy as np

import scalar_field_geometry as sfg
from .fingerprints import object_source_hash
from .rule_metadata import RuleMetadata, RuleStatus


@dataclass(frozen=True)
class ZeroScalarUpdateRule:
    name: str = "zero_scalar_update"
    metadata: RuleMetadata = RuleMetadata(
        name="zero_scalar_update",
        version="0.1.0",
        status=RuleStatus.CONTROL,
        source_hash="declared_control_zero_scalar_update",
        allowed_for_certified_runs=False,
        notes="Negative control: returns phi unchanged.",
    )

    def __call__(self, context: sfg.ScalarUpdateContext) -> sfg.FloatArray:
        return np.asarray(context.phi_current, dtype=np.float64).copy()


@dataclass(frozen=True)
class CertifiedIdentityRemapRule:
    name: str = "identity_no_remap"
    metadata: RuleMetadata = RuleMetadata(
        name="identity_no_remap",
        version="0.1.0",
        status=RuleStatus.CONTROL,
        source_hash="declared_control_identity_no_remap",
        allowed_for_certified_runs=False,
        notes="Negative control: returns current association table unchanged.",
    )

    def __call__(self, context: sfg.RemapContext) -> sfg.IntArray:
        return context.state_current.assoc.copy()


@dataclass(frozen=True)
class CertifiedSlotRotationRemapRule:
    name: str = "demo_slot_rotation"
    metadata: RuleMetadata = RuleMetadata(
        name="demo_slot_rotation",
        version="0.1.0",
        status=RuleStatus.DEMONSTRATION,
        source_hash="declared_demo_slot_rotation",
        allowed_for_certified_runs=False,
        notes="Demonstration only: rotates association slots; not admitted remap dynamics.",
    )

    def __call__(self, context: sfg.RemapContext) -> sfg.IntArray:
        return np.roll(context.state_current.assoc, shift=-1, axis=1)
