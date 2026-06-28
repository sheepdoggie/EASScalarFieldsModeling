from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

import scalar_field_geometry as sfg
from .fingerprints import array_hash, stable_json_hash


def freeze_array(array: np.ndarray) -> np.ndarray:
    frozen = np.asarray(array).copy()
    frozen.setflags(write=False)
    return frozen


@dataclass(frozen=True)
class ImmutableGeometrySnapshot:
    state: sfg.FrozenAssociationState
    ell: int
    phase: int
    adjacency: np.ndarray
    path_lengths: np.ndarray
    pair_weights: np.ndarray
    tensor_geometry: np.ndarray

    @classmethod
    def from_snapshot(cls, snapshot: sfg.GeometrySnapshot) -> "ImmutableGeometrySnapshot":
        return cls(
            state=snapshot.state,
            ell=int(snapshot.ell),
            phase=int(snapshot.phase),
            adjacency=freeze_array(snapshot.adjacency),
            path_lengths=freeze_array(snapshot.path_lengths),
            pair_weights=freeze_array(snapshot.pair_weights),
            tensor_geometry=freeze_array(snapshot.tensor_geometry),
        )

    def fingerprint(self) -> str:
        return stable_json_hash(
            {
                "state_fingerprint": self.state.fingerprint,
                "ell": self.ell,
                "phase": self.phase,
                "adjacency": array_hash(self.adjacency),
                "path_lengths": array_hash(self.path_lengths),
                "pair_weights": array_hash(self.pair_weights),
                "tensor_geometry": array_hash(self.tensor_geometry),
            }
        )


@dataclass(frozen=True)
class ImmutableScalarFieldGeometryResult:
    states: tuple[sfg.FrozenAssociationState, ...]
    phi: np.ndarray
    geometry_snapshots: tuple[ImmutableGeometrySnapshot, ...]

    @classmethod
    def from_result(cls, result: sfg.ScalarFieldGeometryResult) -> "ImmutableScalarFieldGeometryResult":
        return cls(
            states=tuple(result.states),
            phi=freeze_array(result.phi),
            geometry_snapshots=tuple(
                ImmutableGeometrySnapshot.from_snapshot(snapshot)
                for snapshot in result.geometry_snapshots
            ),
        )

    def verify(self) -> bool:
        return (
            not self.phi.flags.writeable
            and all(state.verify() for state in self.states)
            and all(not snap.adjacency.flags.writeable for snap in self.geometry_snapshots)
            and all(not snap.path_lengths.flags.writeable for snap in self.geometry_snapshots)
            and all(not snap.pair_weights.flags.writeable for snap in self.geometry_snapshots)
            and all(not snap.tensor_geometry.flags.writeable for snap in self.geometry_snapshots)
        )

    def fingerprint(self) -> str:
        return stable_json_hash(
            {
                "states": [state.fingerprint for state in self.states],
                "phi": array_hash(self.phi),
                "geometry_snapshots": [snap.fingerprint() for snap in self.geometry_snapshots],
            }
        )
