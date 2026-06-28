import numpy as np
import scalar_field_geometry as sfg
from rank3_enforced.path_facing_remap import PathTargetDerivedExternalRemapRule
from rank3_enforced.locked_registries import build_association_remap_rule


def make_state(assoc):
    arr = np.asarray(assoc, dtype=np.int64)
    fp = sfg.association_fingerprint(
        assoc=arr,
        step=0,
        rule_name="test_initial",
        parent_fingerprint=None,
        metadata={},
    )
    return sfg.FrozenAssociationState(
        assoc=arr,
        step=0,
        rule_name="test_initial",
        fingerprint=fp,
        parent_fingerprint=None,
        metadata={},
        allow_self_association=True,
    )


def make_context(assoc):
    state = make_state(assoc)
    geom = sfg.GeometrySnapshot(
        state=state,
        ell=0,
        phase=0,
        adjacency=np.zeros((state.n_points, state.n_points), dtype=np.int64),
        path_lengths=np.zeros((state.n_points, state.n_points), dtype=np.float64),
        pair_weights=np.zeros((state.n_points, state.n_points), dtype=np.float64),
        tensor_geometry=np.zeros((state.n_points, state.n_points, state.n_points), dtype=np.float64),
    )
    phi = np.zeros(state.n_points)
    return sfg.RemapContext(
        ell=0,
        phase=0,
        state_current=state,
        phi_current=phi,
        phi_next=phi.copy(),
        geometry=geom,
    )


def test_path_target_derived_external_slots_keep_path_slot_fixed():
    assoc = np.array([
        [1, 2, 3],
        [4, 5, 6],
        [0, 4, 5],
        [0, 6, 7],
        [1, 6, 7],
        [2, 7, 0],
        [3, 0, 1],
        [4, 1, 2],
    ])
    ctx = make_context(assoc)
    rule = PathTargetDerivedExternalRemapRule(eligible_points=(0,), path_slot=0, remap_slots=(1,2))
    out = rule(ctx)
    assert out[0,0] == assoc[0,0]
    assert out[0,1] == assoc[1,1]
    assert out[0,2] == assoc[1,2]
    assert np.array_equal(out[1:], assoc[1:])


def test_path_target_derived_respects_fixed_points_and_slots():
    assoc = np.array([
        [1, 2, 3],
        [4, 5, 6],
        [0, 4, 5],
        [0, 6, 7],
        [1, 6, 7],
        [2, 7, 0],
        [3, 0, 1],
        [4, 1, 2],
    ])
    ctx = make_context(assoc)
    rule = PathTargetDerivedExternalRemapRule(
        eligible_points=(0,2),
        fixed_points=(2,),
        fixed_slots_by_point={0:(2,)},
    )
    out = rule(ctx)
    assert out[0,1] == assoc[1,1]
    assert out[0,2] == assoc[0,2]
    assert np.array_equal(out[2], assoc[2])


def test_registry_builds_path_target_derived_rule():
    rule = build_association_remap_rule(
        "path_target_derived_external_remap_v1",
        {"eligible_points":[0], "path_slot":0, "remap_slots":[1,2]},
    )
    assert rule.name == "path_target_derived_external_remap_v1"
