import numpy as np
import pytest
import scalar_field_geometry as sfg
from rank3_enforced.dynamic_paths import (
    DressingRoleMap,
    PathChangeAdmission,
    RelationalPathRecord,
    lengthen_path_record,
    shorten_path_record,
)
from rank3_enforced.exceptions import ManifestError
from rank3_enforced.locked_registries import build_association_remap_rule
from rank3_enforced.role_path_remap import PathContinuationRoleRemapRule


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


def make_context(assoc, ell=0):
    state = make_state(assoc)
    geom = sfg.GeometrySnapshot(
        state=state,
        ell=ell,
        phase=ell % 3,
        adjacency=np.zeros((state.n_points, state.n_points), dtype=np.int64),
        path_lengths=np.zeros((state.n_points, state.n_points), dtype=np.float64),
        pair_weights=np.zeros((state.n_points, state.n_points), dtype=np.float64),
        tensor_geometry=np.zeros((state.n_points, state.n_points, state.n_points), dtype=np.float64),
    )
    phi = np.zeros(state.n_points)
    return sfg.RemapContext(
        ell=ell,
        phase=ell % 3,
        state_current=state,
        phi_current=phi,
        phi_next=phi.copy(),
        geometry=geom,
    )


def test_path_continuation_role_remap_is_orientation_aware_and_keeps_boundary_slots():
    # Points: 0=A_d, 1=p0, 2=p1, 3=p2, 4=B_d, 5=A_b, 6=B_b, 7=A_vac, 8=B_vac, 9=bg
    assoc = np.array([
        [5, 1, 7],  # A_d: slot0 boundary, slot1 path p0, slot2 vacuum
        [0, 2, 9],  # p0: slot0 toward A, slot1 toward B
        [1, 3, 9],
        [2, 4, 9],
        [6, 3, 8],  # B_d: slot0 boundary, slot1 path p2, slot2 vacuum
        [0, 7, 8],
        [4, 8, 7],
        [5, 9, 1],
        [6, 2, 9],
        [7, 8, 0],
    ], dtype=np.int64)
    path = RelationalPathRecord(path_id="lane0", left_endpoint=0, right_endpoint=4, ordered_nodes=(1, 2, 3))
    roles = (
        DressingRoleMap(point=0, boundary_slot=0, path_slot=1, vacuum_slot=2, path_id="lane0", endpoint_side="left"),
        DressingRoleMap(point=4, boundary_slot=0, path_slot=1, vacuum_slot=2, path_id="lane0", endpoint_side="right"),
    )
    rule = PathContinuationRoleRemapRule(paths=(path,), dressing_roles=roles, cadence=1)
    out = rule(make_context(assoc))
    # A side advances p0 -> p1 using path direction toward B.
    assert out[0, 1] == 2
    # B side advances p2 -> p1 using path direction toward A.
    assert out[4, 1] == 2
    # Boundary slots are fixed.
    assert out[0, 0] == 5
    assert out[4, 0] == 6
    # Scalar movement is prohibited by report.
    assert rule.get_role_path_remap_reports()[-1].details["scalar_values_moved"] is False


def test_path_continuation_role_remap_can_exchange_path_and_vacuum_roles():
    assoc = np.array([
        [5, 1, 7],
        [0, 2, 9],
        [1, 3, 9],
        [2, 4, 9],
        [6, 3, 8],
        [0, 7, 8],
        [4, 8, 7],
        [5, 9, 1],
        [6, 2, 9],
        [7, 8, 0],
    ], dtype=np.int64)
    path = RelationalPathRecord(path_id="lane0", left_endpoint=0, right_endpoint=4, ordered_nodes=(1, 2, 3))
    role = DressingRoleMap(
        point=0,
        boundary_slot=0,
        path_slot=1,
        vacuum_slot=2,
        path_id="lane0",
        endpoint_side="left",
        allow_path_vacuum_exchange=True,
    )
    rule = PathContinuationRoleRemapRule(paths=(path,), dressing_roles=(role,), cadence=1)
    out = rule(make_context(assoc))
    # Exchanged: path role now in slot2, vacuum role in slot1.
    assert out[0, 2] == 2
    assert out[0, 1] == 7
    assert out[0, 0] == 5


def test_registry_builds_path_continuation_role_remap_rule():
    rule = build_association_remap_rule(
        "path_continuation_role_remap_v1",
        {
            "cadence": 2,
            "path_records": [{"path_id": "lane0", "left_endpoint": 0, "right_endpoint": 4, "ordered_nodes": [1, 2, 3]}],
            "dressing_roles": [
                {"point": 0, "boundary_slot": 0, "path_slot": 1, "vacuum_slot": 2, "path_id": "lane0", "endpoint_side": "left"},
                {"point": 4, "boundary_slot": 0, "path_slot": 1, "vacuum_slot": 2, "path_id": "lane0", "endpoint_side": "right"},
            ],
        },
    )
    assert rule.name == "path_continuation_role_remap_v1"


def test_path_shortening_and_lengthening_require_admission_gate():
    assoc = np.array([
        [1, 5, 6],
        [0, 2, 6],
        [1, 3, 6],
        [2, 4, 6],
        [3, 5, 6],
        [0, 4, 6],
        [0, 1, 2],
    ], dtype=np.int64)
    path = RelationalPathRecord(path_id="lane0", left_endpoint=0, right_endpoint=4, ordered_nodes=(1, 2, 3))
    rejected = PathChangeAdmission(admitted=False, reason="control failed")
    with pytest.raises(ManifestError):
        shorten_path_record(assoc=assoc, path=path, admission=rejected)
    admitted = PathChangeAdmission(
        admitted=True,
        reason="test gate",
        phase_complete=True,
        negative_controls_passed=True,
        label_independence_checked=True,
    )
    shrunk = shorten_path_record(assoc=assoc, path=path, admission=admitted)
    assert shrunk.path_after.ordered_nodes == (1, 3)
    assert shrunk.transaction_report.validation["delta_L"] == -1
    grown = lengthen_path_record(assoc=assoc, path=path, new_node=6, admission=admitted)
    assert grown.path_after.path_length == path.path_length + 1
    assert grown.transaction_report.validation["delta_L"] == 1
