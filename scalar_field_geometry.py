# scalar_field_geometry.py

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Literal, Protocol, Sequence

import hashlib
import json
import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

GraphMode = Literal["directed", "undirected"]
PathScope = Literal["completed", "active_phase"]
InitialAssociationRule = Literal[
    "random_distinct_no_self",
    "cyclic_offsets",
]


# =============================================================================
# 1. Rule protocols
# =============================================================================

class PhaseRule(Protocol):
    def __call__(self, ell: int) -> int:
        ...


class PairWeightRule(Protocol):
    def __call__(self, path_lengths: FloatArray) -> FloatArray:
        ...


class TripletLiftRule(Protocol):
    def __call__(self, pair_weights: FloatArray) -> FloatArray:
        ...


class ScalarUpdateRule(Protocol):
    def __call__(self, context: "ScalarUpdateContext") -> FloatArray:
        ...


class AssociationRemapRule(Protocol):
    name: str

    def __call__(self, context: "RemapContext") -> IntArray:
        ...


# =============================================================================
# 2. Association-state validation and provenance
# =============================================================================

def _jsonable_metadata(metadata: dict[str, object] | None) -> dict[str, object]:
    if metadata is None:
        return {}

    return json.loads(json.dumps(metadata, sort_keys=True, default=str))


def association_fingerprint(
    *,
    assoc: IntArray,
    step: int,
    rule_name: str,
    parent_fingerprint: str | None,
    metadata: dict[str, object] | None = None,
) -> str:
    """
    Stable fingerprint for one association-state snapshot.

    The fingerprint records:
        - association table,
        - step,
        - producing rule,
        - parent state fingerprint,
        - optional metadata.

    This does not prevent remapping.
    It prevents silent mutation of already-produced records.
    """

    payload = {
        "assoc": np.asarray(assoc, dtype=np.int64).tolist(),
        "step": int(step),
        "rule_name": str(rule_name),
        "parent_fingerprint": parent_fingerprint,
        "metadata": _jsonable_metadata(metadata),
    }

    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_association_array(
    assoc: IntArray,
    *,
    allow_self_association: bool = False,
) -> IntArray:
    """
    Validate an association table.

    Required shape:
        assoc[n_points, 3]

    Meaning:
        assoc[i, r] = point associated to i in slot r.

    Conditions:
        - exactly three slots per point,
        - target indices in range,
        - three distinct targets per point,
        - no self-association unless explicitly allowed.
    """

    assoc = np.asarray(assoc, dtype=np.int64)

    if assoc.ndim != 2 or assoc.shape[1] != 3:
        raise ValueError("assoc must have shape (n_points, 3).")

    n_points = int(assoc.shape[0])

    if n_points < 4:
        raise ValueError("n_points must be at least 4.")

    if np.any(assoc < 0) or np.any(assoc >= n_points):
        raise ValueError("Association target out of range.")

    for i in range(n_points):
        targets = list(map(int, assoc[i]))

        if len(set(targets)) != 3:
            raise ValueError(
                f"Point {i} must have exactly three distinct associates."
            )

        if not allow_self_association and i in targets:
            raise ValueError(
                f"Point {i} cannot associate to itself."
            )

    return assoc


@dataclass(frozen=True)
class FrozenAssociationState:
    """
    One immutable association-geometry snapshot.

    This state cannot be edited in place.

    Remapping is allowed only by producing a new FrozenAssociationState through
    a named AssociationRemapRule.
    """

    assoc: IntArray
    step: int
    rule_name: str
    fingerprint: str
    parent_fingerprint: str | None = None
    metadata: dict[str, object] | None = None
    allow_self_association: bool = False
    initial_phi_previous: FloatArray | None = None

    def __post_init__(self) -> None:
        assoc = validate_association_array(
            self.assoc,
            allow_self_association=self.allow_self_association,
        )

        expected = association_fingerprint(
            assoc=assoc,
            step=self.step,
            rule_name=self.rule_name,
            parent_fingerprint=self.parent_fingerprint,
            metadata=self.metadata,
        )

        if self.fingerprint != expected:
            raise ValueError("Association fingerprint mismatch.")

        assoc = assoc.copy()
        assoc.setflags(write=False)

        object.__setattr__(self, "assoc", assoc)

    @property
    def n_points(self) -> int:
        return int(self.assoc.shape[0])

    def target(self, point: int, phase: int) -> int:
        return int(self.assoc[point, phase % 3])

    def active_edges(
        self,
        *,
        phase: int,
        graph_mode: GraphMode,
    ) -> list[tuple[int, int]]:
        """
        Phase-local active association edges.
        """

        r = phase % 3
        edges: list[tuple[int, int]] = []

        for i in range(self.n_points):
            j = int(self.assoc[i, r])
            edges.append((i, j))

            if graph_mode == "undirected":
                edges.append((j, i))

        return edges

    def completed_edges(
        self,
        *,
        graph_mode: GraphMode,
    ) -> list[tuple[int, int]]:
        """
        All three association slots for every point.
        """

        edges: list[tuple[int, int]] = []

        for i in range(self.n_points):
            for r in range(3):
                j = int(self.assoc[i, r])
                edges.append((i, j))

                if graph_mode == "undirected":
                    edges.append((j, i))

        return edges

    def verify(self) -> bool:
        expected = association_fingerprint(
            assoc=self.assoc,
            step=self.step,
            rule_name=self.rule_name,
            parent_fingerprint=self.parent_fingerprint,
            metadata=self.metadata,
        )

        return expected == self.fingerprint and not self.assoc.flags.writeable


# =============================================================================
# 3. Initial association generation
# =============================================================================

def generate_initial_association_state(
    *,
    n_points: int,
    seed: int,
    generation_rule: InitialAssociationRule = "random_distinct_no_self",
    allow_self_association: bool = False,
) -> FrozenAssociationState:
    """
    Automatically generate G_0.

    This function is the only initial association generator.

    It does not govern later remapping. Later association changes must pass
    through an AssociationRemapRule.
    """

    if n_points < 4:
        raise ValueError("n_points must be at least 4.")

    if generation_rule == "random_distinct_no_self":
        rng = np.random.default_rng(seed)
        assoc = np.zeros((n_points, 3), dtype=np.int64)

        for i in range(n_points):
            candidates = [j for j in range(n_points) if allow_self_association or j != i]
            assoc[i] = rng.choice(candidates, size=3, replace=False)

    elif generation_rule == "cyclic_offsets":
        assoc = np.zeros((n_points, 3), dtype=np.int64)

        for i in range(n_points):
            assoc[i, 0] = (i + 1) % n_points
            assoc[i, 1] = (i + 2) % n_points
            assoc[i, 2] = (i + 3) % n_points

    else:
        raise ValueError(f"Unknown generation_rule: {generation_rule}")

    metadata = {
        "initial_seed": int(seed),
        "generation_rule": generation_rule,
        "allow_self_association": bool(allow_self_association),
    }

    rule_name = f"initial::{generation_rule}"

    fingerprint = association_fingerprint(
        assoc=assoc,
        step=0,
        rule_name=rule_name,
        parent_fingerprint=None,
        metadata=metadata,
    )

    return FrozenAssociationState(
        assoc=assoc,
        step=0,
        rule_name=rule_name,
        fingerprint=fingerprint,
        parent_fingerprint=None,
        metadata=metadata,
        allow_self_association=allow_self_association,
    )


# =============================================================================
# 4. Geometry reports from association state
# =============================================================================

def cyclic_phase_rule(ell: int) -> int:
    return ell % 3


def adjacency_from_association_state(
    *,
    state: FrozenAssociationState,
    graph_mode: GraphMode,
    path_scope: PathScope,
    phase: int,
) -> IntArray:
    """
    Build adjacency from association state.

    path_scope="completed":
        use all three association slots.

    path_scope="active_phase":
        use only the slot active in the selected phase.
    """

    adjacency = np.zeros((state.n_points, state.n_points), dtype=np.int64)

    if path_scope == "completed":
        edges = state.completed_edges(graph_mode=graph_mode)
    elif path_scope == "active_phase":
        edges = state.active_edges(phase=phase, graph_mode=graph_mode)
    else:
        raise ValueError(f"Unknown path_scope: {path_scope}")

    for i, j in edges:
        adjacency[i, j] = 1

    return adjacency


def all_pairs_shortest_path_lengths(adjacency: IntArray) -> FloatArray:
    """
    Association-native path length.

    L[i,j] = shortest number of association steps from i to j.
    L[i,j] = np.inf if unreachable.

    This is not coordinate distance.
    """

    adjacency = np.asarray(adjacency, dtype=np.int64)

    if adjacency.ndim != 2 or adjacency.shape[0] != adjacency.shape[1]:
        raise ValueError("adjacency must be square.")

    n = int(adjacency.shape[0])
    L = np.full((n, n), np.inf, dtype=np.float64)

    for source in range(n):
        L[source, source] = 0.0

        queue: deque[int] = deque([source])
        visited = {source}

        while queue:
            i = queue.popleft()

            for raw_j in np.where(adjacency[i] != 0)[0]:
                j = int(raw_j)

                if j not in visited:
                    visited.add(j)
                    L[source, j] = L[source, i] + 1.0
                    queue.append(j)

    return L


def inverse_length_pair_weight(path_lengths: FloatArray) -> FloatArray:
    """
    Example pair-weight rule.

    W[i,j] = 1 / L[i,j] for connected distinct points.
    W[i,i] = 0.
    W[i,j] = 0 if disconnected.
    """

    L = np.asarray(path_lengths, dtype=np.float64)
    W = np.zeros_like(L, dtype=np.float64)

    valid = np.isfinite(L) & (L > 0.0)
    W[valid] = 1.0 / L[valid]

    return W


def bounded_inverse_length_pair_weight(path_lengths: FloatArray) -> FloatArray:
    """
    Example pair-weight rule.

    W[i,j] = 1 / (1 + L[i,j]) for connected distinct points.
    W[i,i] = 0.
    W[i,j] = 0 if disconnected.
    """

    L = np.asarray(path_lengths, dtype=np.float64)
    W = np.zeros_like(L, dtype=np.float64)

    valid = np.isfinite(L) & (L > 0.0)
    W[valid] = 1.0 / (1.0 + L[valid])

    return W


def product_triplet_lift(pair_weights: FloatArray) -> FloatArray:
    """
    Example triplet-lift rule.

    T[i,j,k] = W[i,j] * W[j,k] * W[k,i]

    This is a derived rank-3 tensor geometry, not a scalar-field value.
    """

    W = np.asarray(pair_weights, dtype=np.float64)

    if W.ndim != 2 or W.shape[0] != W.shape[1]:
        raise ValueError("pair_weights must be square.")

    T = np.einsum("ij,jk,ki->ijk", W, W, W)
    n = W.shape[0]

    for i in range(n):
        T[i, i, :] = 0.0
        T[i, :, i] = 0.0
        T[:, i, i] = 0.0

    return T.astype(np.float64)


def minimum_triplet_lift(pair_weights: FloatArray) -> FloatArray:
    """
    Example triplet-lift rule.

    T[i,j,k] = min(W[i,j], W[j,k], W[k,i])
    """

    W = np.asarray(pair_weights, dtype=np.float64)

    if W.ndim != 2 or W.shape[0] != W.shape[1]:
        raise ValueError("pair_weights must be square.")

    n = int(W.shape[0])
    T = np.zeros((n, n, n), dtype=np.float64)

    for i in range(n):
        for j in range(n):
            for k in range(n):
                if i == j or j == k or k == i:
                    continue

                T[i, j, k] = min(W[i, j], W[j, k], W[k, i])

    return T


@dataclass(frozen=True)
class GeometrySnapshot:
    """
    Derived geometry report for one layer.

    This object is derived from the association state.

    It contains:
        - adjacency,
        - path lengths,
        - pair weights,
        - rank-3 tensor geometry.
    """

    state: FrozenAssociationState
    ell: int
    phase: int
    adjacency: IntArray
    path_lengths: FloatArray
    pair_weights: FloatArray
    tensor_geometry: FloatArray


def build_geometry_snapshot(
    *,
    state: FrozenAssociationState,
    ell: int,
    phase_rule: PhaseRule,
    graph_mode: GraphMode,
    path_scope: PathScope,
    pair_weight_rule: PairWeightRule,
    triplet_lift_rule: TripletLiftRule,
) -> GeometrySnapshot:
    """
    Pure geometry pipeline:

        association state
            -> adjacency
                -> path lengths
                    -> pair weights
                        -> rank-3 tensor geometry

    No scalar field values are used.
    """

    phase = int(phase_rule(ell)) % 3

    adjacency = adjacency_from_association_state(
        state=state,
        graph_mode=graph_mode,
        path_scope=path_scope,
        phase=phase,
    )

    path_lengths = all_pairs_shortest_path_lengths(adjacency)
    pair_weights = np.asarray(pair_weight_rule(path_lengths), dtype=np.float64)
    tensor_geometry = np.asarray(triplet_lift_rule(pair_weights), dtype=np.float64)

    n = state.n_points

    if pair_weights.shape != (n, n):
        raise ValueError(
            f"pair_weight_rule returned shape {pair_weights.shape}; expected {(n, n)}."
        )

    if tensor_geometry.shape != (n, n, n):
        raise ValueError(
            "triplet_lift_rule returned shape "
            f"{tensor_geometry.shape}; expected {(n, n, n)}."
        )

    return GeometrySnapshot(
        state=state,
        ell=ell,
        phase=phase,
        adjacency=adjacency,
        path_lengths=path_lengths,
        pair_weights=pair_weights,
        tensor_geometry=tensor_geometry,
    )


# =============================================================================
# 5. Scalar update and remap contexts
# =============================================================================

@dataclass(frozen=True)
class ScalarUpdateContext:
    """
    Context passed into the externally supplied scalar update rule.

    The engine does not hard-code SOO. Second-order rules may use
    phi_previous. First-order/control rules may ignore it.
    """

    ell: int
    phase: int
    phi_current: FloatArray
    geometry: GeometrySnapshot
    phi_previous: FloatArray | None = None


@dataclass(frozen=True)
class RemapContext:
    """
    Context passed into the externally supplied association remap rule.

    Remapping is allowed only through this explicit boundary.
    """

    ell: int
    phase: int
    state_current: FrozenAssociationState
    phi_current: FloatArray
    phi_next: FloatArray
    geometry: GeometrySnapshot


@dataclass(frozen=True)
class IdentityRemapRule:
    """
    Negative-control remap rule.

    Produces no association change.
    """

    name: str = "identity_no_remap"

    def __call__(self, context: RemapContext) -> IntArray:
        return context.state_current.assoc.copy()


@dataclass(frozen=True)
class SlotRotationRemapRule:
    """
    Demonstration remap rule.

    It rotates association slots:

        [a0, a1, a2] -> [a1, a2, a0]

    This is useful for testing that remapping infrastructure works.

    It is not a physical/SOO claim.
    """

    name: str = "demo_slot_rotation"

    def __call__(self, context: RemapContext) -> IntArray:
        return np.roll(context.state_current.assoc, shift=-1, axis=1)


def apply_association_remap(
    *,
    context: RemapContext,
    remap_rule: AssociationRemapRule,
    allow_self_association: bool = False,
) -> FrozenAssociationState:
    """
    Legal association transition:

        G_ell -> G_{ell+1}

    No model code should mutate G_ell in place.
    """

    next_assoc = np.asarray(remap_rule(context), dtype=np.int64)
    next_assoc = validate_association_array(
        next_assoc,
        allow_self_association=allow_self_association,
    )

    next_step = context.state_current.step + 1

    metadata = {
        "ell": int(context.ell),
        "phase": int(context.phase),
        "remap_rule": remap_rule.name,
        "parent_step": int(context.state_current.step),
    }

    fingerprint = association_fingerprint(
        assoc=next_assoc,
        step=next_step,
        rule_name=remap_rule.name,
        parent_fingerprint=context.state_current.fingerprint,
        metadata=metadata,
    )

    return FrozenAssociationState(
        assoc=next_assoc,
        step=next_step,
        rule_name=remap_rule.name,
        fingerprint=fingerprint,
        parent_fingerprint=context.state_current.fingerprint,
        metadata=metadata,
        allow_self_association=allow_self_association,
    )


# =============================================================================
# 6. Example scalar update rule
# =============================================================================

@dataclass(frozen=True)
class ContrastTensorUpdateRule:
    """
    Example scalar update rule.

    This is a replaceable demonstration rule.

    It updates point i from the contrast between i and its active associate j,
    weighted by tensor completions around (i,j).

    This rule is not hard-coded into the engine.
    """

    stiffness: float

    def __call__(self, context: ScalarUpdateContext) -> FloatArray:
        phi = np.asarray(context.phi_current, dtype=np.float64)
        state = context.geometry.state
        T = context.geometry.tensor_geometry
        phase = context.phase

        next_phi = phi.copy()

        for i in range(state.n_points):
            j = state.target(i, phase)

            coupling_ij = float(np.sum(T[i, j, :]))
            contrast = phi[j] - phi[i]

            next_phi[i] = phi[i] + self.stiffness * coupling_ij * contrast

        return next_phi


# =============================================================================
# 7. Full scalar-field geometry engine
# =============================================================================

@dataclass(frozen=True)
class ScalarFieldGeometryConfig:
    """
    Full module configuration.

    Every model-bearing rule is passed in explicitly.
    """

    initial_state: FrozenAssociationState
    initial_phi: FloatArray
    n_layers: int

    graph_mode: GraphMode
    path_scope: PathScope

    phase_rule: PhaseRule
    pair_weight_rule: PairWeightRule
    triplet_lift_rule: TripletLiftRule
    scalar_update_rule: ScalarUpdateRule
    association_remap_rule: AssociationRemapRule

    allow_self_association: bool = False
    initial_phi_previous: FloatArray | None = None


@dataclass(frozen=True)
class ScalarFieldGeometryResult:
    """
    Complete scalar-field geometry run.

    states:
        G_0, G_1, ..., G_{n_layers-1}

    phi:
        scalar field layers Phi[ell, i]

    geometry_snapshots:
        derived geometry reports used for transitions.
        length = n_layers - 1
    """

    states: list[FrozenAssociationState]
    phi: FloatArray
    geometry_snapshots: list[GeometrySnapshot]


def run_scalar_field_geometry(
    config: ScalarFieldGeometryConfig,
) -> ScalarFieldGeometryResult:
    """
    Coherent scalar field geometry engine.

    Update order per transition:

        G_ell
            -> geometry report
                -> Phi_{ell+1}
                    -> G_{ell+1} by named remap rule

    Association states are immutable snapshots.
    Remapping occurs only through association_remap_rule.
    """

    if config.n_layers < 1:
        raise ValueError("n_layers must be at least 1.")

    initial_phi = np.asarray(config.initial_phi, dtype=np.float64)

    n = config.initial_state.n_points

    if initial_phi.shape != (n,):
        raise ValueError(f"initial_phi must have shape {(n,)}, got {initial_phi.shape}.")

    phi = np.zeros((config.n_layers, n), dtype=np.float64)
    phi[0] = initial_phi

    states: list[FrozenAssociationState] = [config.initial_state]
    geometry_snapshots: list[GeometrySnapshot] = []

    for ell in range(config.n_layers - 1):
        current_state = states[-1]

        if not current_state.verify():
            raise ValueError(f"Association state at ell={ell} failed verification.")

        geometry = build_geometry_snapshot(
            state=current_state,
            ell=ell,
            phase_rule=config.phase_rule,
            graph_mode=config.graph_mode,
            path_scope=config.path_scope,
            pair_weight_rule=config.pair_weight_rule,
            triplet_lift_rule=config.triplet_lift_rule,
        )

        update_context = ScalarUpdateContext(
            ell=ell,
            phase=geometry.phase,
            phi_current=phi[ell].copy(),
            geometry=geometry,
            phi_previous=(phi[ell - 1].copy() if ell > 0 else (np.asarray(config.initial_phi_previous, dtype=np.float64).copy() if config.initial_phi_previous is not None else None)),
        )

        next_phi = np.asarray(config.scalar_update_rule(update_context), dtype=np.float64)

        if next_phi.shape != (n,):
            raise ValueError(
                f"scalar_update_rule returned shape {next_phi.shape}; expected {(n,)}."
            )

        phi[ell + 1] = next_phi

        remap_context = RemapContext(
            ell=ell,
            phase=geometry.phase,
            state_current=current_state,
            phi_current=phi[ell].copy(),
            phi_next=next_phi.copy(),
            geometry=geometry,
        )

        next_state = apply_association_remap(
            context=remap_context,
            remap_rule=config.association_remap_rule,
            allow_self_association=config.allow_self_association,
        )

        states.append(next_state)
        geometry_snapshots.append(geometry)

    return ScalarFieldGeometryResult(
        states=states,
        phi=phi,
        geometry_snapshots=geometry_snapshots,
    )


# =============================================================================
# 8. Visualization: tensor slice heatmaps
# =============================================================================

def plot_tensor_slice_heatmap(
    tensor_geometry: FloatArray,
    *,
    fixed_axis: Literal[0, 1, 2] = 2,
    fixed_index: int = 0,
    title: str | None = None,
    show: bool = True,
    save_path: str | Path | None = None,
):
    """
    Tensor slice heatmap.

    Shows:
        active T[i,j,k] values.

    Ontological status:
        direct tensor data.
    """

    import matplotlib.pyplot as plt

    T = np.asarray(tensor_geometry, dtype=np.float64)

    if T.ndim != 3 or not (T.shape[0] == T.shape[1] == T.shape[2]):
        raise ValueError("tensor_geometry must be cubic rank-3.")

    n = T.shape[0]

    if fixed_index < 0 or fixed_index >= n:
        raise ValueError("fixed_index out of range.")

    if fixed_axis == 0:
        data = T[fixed_index, :, :]
        label = f"T[{fixed_index}, :, :]"
    elif fixed_axis == 1:
        data = T[:, fixed_index, :]
        label = f"T[:, {fixed_index}, :]"
    elif fixed_axis == 2:
        data = T[:, :, fixed_index]
        label = f"T[:, :, {fixed_index}]"
    else:
        raise ValueError("fixed_axis must be 0, 1, or 2.")

    fig, ax = plt.subplots(figsize=(7, 6))
    image = ax.imshow(data, aspect="auto", interpolation="nearest")

    ax.set_xlabel("Index")
    ax.set_ylabel("Index")
    ax.set_title(title or f"Tensor slice heatmap: {label}")

    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label("Derived tensor weight")

    fig.tight_layout()

    if save_path is not None:
        fig.savefig(save_path, dpi=160)

    if show:
        plt.show()

    return fig


def plot_tensor_slice_from_result(
    result: ScalarFieldGeometryResult,
    *,
    transition_index: int,
    fixed_axis: Literal[0, 1, 2] = 2,
    fixed_index: int = 0,
    show: bool = True,
    save_path: str | Path | None = None,
):
    geometry = result.geometry_snapshots[transition_index]

    return plot_tensor_slice_heatmap(
        geometry.tensor_geometry,
        fixed_axis=fixed_axis,
        fixed_index=fixed_index,
        title=(
            f"Tensor geometry slice, transition {transition_index}, "
            f"phase {geometry.phase}"
        ),
        show=show,
        save_path=save_path,
    )


# =============================================================================
# 9. Visualization: support worldline
# =============================================================================

def support_worldline_matrix(
    *,
    support_path: Sequence[Iterable[int]],
    n_points: int,
) -> FloatArray:
    """
    M[t,i] = 1 if point i participates in the object at step t.

    Ontological status:
        direct relational participation.
    """

    M = np.zeros((len(support_path), n_points), dtype=np.float64)

    for t, support in enumerate(support_path):
        for raw_i in support:
            i = int(raw_i)

            if i < 0 or i >= n_points:
                raise ValueError(f"Support point {i} at step {t} is out of range.")

            M[t, i] = 1.0

    return M


def relational_overlap_path(
    support_path: Sequence[Iterable[int]],
) -> list[float]:
    """
    Consecutive support overlap.

    High overlap:
        relationally continuous movement.

    Low overlap:
        jump-like remapping.
    """

    overlaps: list[float] = []

    for t in range(len(support_path) - 1):
        a = set(map(int, support_path[t]))
        b = set(map(int, support_path[t + 1]))

        union = a | b

        overlaps.append(1.0 if not union else len(a & b) / len(union))

    return overlaps


def plot_support_worldline(
    *,
    support_path: Sequence[Iterable[int]],
    n_points: int,
    title: str = "Support worldline",
    show: bool = True,
    save_path: str | Path | None = None,
):
    """
    Support worldline plot.

    Shows:
        which abstract points participate over relational time.

    Ontological status:
        direct relational participation.
    """

    import matplotlib.pyplot as plt

    M = support_worldline_matrix(
        support_path=support_path,
        n_points=n_points,
    )

    fig, ax = plt.subplots(figsize=(9, 5))
    image = ax.imshow(M, aspect="auto", interpolation="nearest")

    ax.set_xlabel("Abstract point index")
    ax.set_ylabel("Relational step")
    ax.set_title(title)

    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label("Object participation")

    fig.tight_layout()

    if save_path is not None:
        fig.savefig(save_path, dpi=160)

    if show:
        plt.show()

    return fig


# =============================================================================
# 10. Visualization: projected graph animation
# =============================================================================

def _import_networkx():
    try:
        import networkx as nx
    except ImportError as exc:
        raise ImportError(
            "Projected graph animation requires networkx. "
            "Install with: pip install networkx"
        ) from exc

    return nx


def union_edges_from_states(
    *,
    states: Sequence[FrozenAssociationState],
    graph_mode: GraphMode,
) -> list[tuple[int, int]]:
    edge_set: set[tuple[int, int]] = set()

    for state in states:
        for i, j in state.completed_edges(graph_mode=graph_mode):
            edge_set.add((int(i), int(j)))

    return sorted(edge_set)


def animate_projected_graph(
    *,
    states: Sequence[FrozenAssociationState],
    support_path: Sequence[Iterable[int]],
    graph_mode: GraphMode = "undirected",
    layout_seed: int = 7,
    interval_ms: int = 900,
    title: str = "Projected relational movement",
    save_path: str | Path | None = None,
    show: bool = True,
):
    """
    Projected graph animation.

    Shows:
        intuitive movement picture.

    Ontological status:
        projection only, not physical space.

    Important:
        node positions are drawing coordinates produced by the graph layout.
        They are not model coordinates.
    """

    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter

    nx = _import_networkx()

    if len(states) != len(support_path):
        raise ValueError("states and support_path must have the same length.")

    if not states:
        raise ValueError("states must be non-empty.")

    n = states[0].n_points

    for state in states:
        if state.n_points != n:
            raise ValueError("All states must have the same number of points.")

    union_edges = union_edges_from_states(
        states=states,
        graph_mode=graph_mode,
    )

    G_union = nx.Graph() if graph_mode == "undirected" else nx.DiGraph()
    G_union.add_nodes_from(range(n))
    G_union.add_edges_from(union_edges)

    # Fixed projection-only layout from the union graph.
    pos = nx.spring_layout(G_union, seed=layout_seed)

    fig, ax = plt.subplots(figsize=(8, 7))

    def draw_frame(frame_index: int) -> None:
        ax.clear()

        state = states[frame_index]
        support = set(map(int, support_path[frame_index]))

        current_edges = state.completed_edges(graph_mode=graph_mode)
        support_edges = [
            (i, j)
            for i, j in current_edges
            if i in support and j in support
        ]

        ambient_nodes = [i for i in range(n) if i not in support]
        support_nodes = sorted(support)

        G_current = nx.Graph() if graph_mode == "undirected" else nx.DiGraph()
        G_current.add_nodes_from(range(n))
        G_current.add_edges_from(current_edges)

        ax.set_title(
            f"{title}\n"
            f"step={frame_index}, assoc_step={state.step}, "
            f"support={tuple(support_nodes)}\n"
            f"projection only; not physical coordinates"
        )

        nx.draw_networkx_edges(
            G_union,
            pos,
            edgelist=union_edges,
            ax=ax,
            alpha=0.10,
            width=1.0,
        )

        nx.draw_networkx_edges(
            G_current,
            pos,
            edgelist=current_edges,
            ax=ax,
            alpha=0.30,
            width=1.4,
        )

        nx.draw_networkx_edges(
            G_current,
            pos,
            edgelist=support_edges,
            ax=ax,
            alpha=0.90,
            width=3.0,
        )

        nx.draw_networkx_nodes(
            G_current,
            pos,
            nodelist=ambient_nodes,
            ax=ax,
            node_size=430,
            alpha=0.35,
        )

        nx.draw_networkx_nodes(
            G_current,
            pos,
            nodelist=support_nodes,
            ax=ax,
            node_size=720,
            alpha=0.95,
        )

        nx.draw_networkx_labels(
            G_current,
            pos,
            ax=ax,
            font_size=10,
        )

        ax.axis("off")

    animation = FuncAnimation(
        fig,
        draw_frame,
        frames=len(states),
        interval=interval_ms,
        repeat=True,
    )

    if save_path is not None:
        save_path = Path(save_path)

        if save_path.suffix.lower() == ".gif":
            fps = max(1, int(1000 / interval_ms))
            animation.save(save_path, writer=PillowWriter(fps=fps))
        else:
            animation.save(save_path)

    if show:
        plt.show()

    return animation


# =============================================================================
# 11. Example usage
# =============================================================================

def example_usage() -> ScalarFieldGeometryResult:
    """
    Minimal working example.

    Dependencies:

        pip install numpy matplotlib networkx pillow

    Run:

        python scalar_field_geometry.py
    """

    initial_state = generate_initial_association_state(
        n_points=12,
        seed=20260626,
        generation_rule="random_distinct_no_self",
    )

    assert initial_state.verify()

    initial_phi = np.array(
        [
            1.0,
            -1.0,
            0.75,
            -0.75,
            0.50,
            -0.50,
            0.25,
            -0.25,
            0.125,
            -0.125,
            0.0,
            0.0,
        ],
        dtype=np.float64,
    )

    config = ScalarFieldGeometryConfig(
        initial_state=initial_state,
        initial_phi=initial_phi,
        n_layers=9,
        graph_mode="undirected",
        path_scope="completed",
        phase_rule=cyclic_phase_rule,
        pair_weight_rule=inverse_length_pair_weight,
        triplet_lift_rule=product_triplet_lift,
        scalar_update_rule=ContrastTensorUpdateRule(stiffness=0.1),

        # Use IdentityRemapRule for a negative-control/no-remap run.
        # Replace with an admitted remap rule when testing remapping.
        association_remap_rule=IdentityRemapRule(),

        allow_self_association=False,
    )

    result = run_scalar_field_geometry(config)

    print("Initial association fingerprint:")
    print(result.states[0].fingerprint)

    print("\nFinal association fingerprint:")
    print(result.states[-1].fingerprint)

    print("\nScalar field Phi[ell, i]:")
    print(result.phi)

    print("\nAssociation states verified:")
    print([state.verify() for state in result.states])

    # -------------------------------------------------------------------------
    # Visualization layer 1:
    # Tensor slice heatmap.
    # Ontological status: direct tensor data.
    # -------------------------------------------------------------------------

    plot_tensor_slice_from_result(
        result,
        transition_index=0,
        fixed_axis=2,
        fixed_index=0,
        save_path="tensor_slice_transition_0_k_0.png",
        show=True,
    )

    # -------------------------------------------------------------------------
    # Visualization layer 2:
    # Support worldline.
    # Ontological status: direct relational participation.
    # -------------------------------------------------------------------------

    support_path = [
        (0, 1, 2, 3),
        (1, 2, 3, 4),
        (2, 3, 4, 5),
        (3, 4, 5, 6),
        (4, 5, 6, 7),
        (5, 6, 7, 8),
        (6, 7, 8, 9),
        (7, 8, 9, 10),
        (8, 9, 10, 11),
    ]

    print("\nRelational support overlaps:")
    for idx, overlap in enumerate(relational_overlap_path(support_path)):
        print(f"{idx} -> {idx + 1}: {overlap:.3f}")

    plot_support_worldline(
        support_path=support_path,
        n_points=initial_state.n_points,
        title="Object support worldline",
        save_path="support_worldline.png",
        show=True,
    )

    # -------------------------------------------------------------------------
    # Visualization layer 3:
    # Projected graph animation.
    # Ontological status: projection only, not physical space.
    # -------------------------------------------------------------------------

    animate_projected_graph(
        states=result.states,
        support_path=support_path,
        graph_mode="undirected",
        layout_seed=11,
        interval_ms=900,
        title="Projected association-graph movement",
        save_path="projected_relational_movement.gif",
        show=True,
    )

    return result


if __name__ == "__main__":
    example_usage()
