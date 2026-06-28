import numpy as np
import pytest
import scalar_field_geometry as sfg
from rank3_enforced.dynamic_paths import (
    DressingRoleMap,
    RelationalPathRecord,
)
from rank3_enforced.external_path_monitor import (
    ExternalPathEditRequest,
    apply_external_path_edit_request,
    call_external_path_monitor,
    make_path_monitor_snapshot,
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


def test_external_path_monitor_applies_requested_remove_and_insert_without_ontology_rule():
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
    snapshot = make_path_monitor_snapshot(assoc=assoc, path=path, cycle=12, phase=0)
    assert snapshot.path_length == 3
    with pytest.raises(ManifestError):
        call_external_path_monitor(snapshot, lambda _s: ExternalPathEditRequest(operation="none"))

    remove_request = ExternalPathEditRequest(
        operation="remove_node",
        path_id="lane0",
        target_node=2,
        reason="exploratory midpoint monitor",
        monitor_fingerprint=snapshot.fingerprint(),
    )
    removed = apply_external_path_edit_request(assoc=assoc, path=path, request=remove_request)
    assert removed.path_after.ordered_nodes == (1, 3)
    assert removed.transaction_report.validation["delta_L"] == -1
    assert removed.transaction_report.validation["ontology_rule"] is False
    assert removed.transaction_report.scalar_values_moved is False

    insert_request = ExternalPathEditRequest(
        operation="insert_existing_node",
        path_id="lane0",
        new_node=6,
        insert_after_index=1,
        reason="exploratory reinforcement monitor",
        monitor_fingerprint=snapshot.fingerprint(),
    )
    inserted = apply_external_path_edit_request(assoc=assoc, path=path, request=insert_request)
    assert inserted.path_after.ordered_nodes == (1, 2, 6, 3)
    assert inserted.transaction_report.validation["delta_L"] == 1
    assert inserted.transaction_report.validation["external_monitor_request_required"] is True

    bad_request = ExternalPathEditRequest(operation="remove_node", path_id="lane0", target_node=2, ontology_rule=True)
    with pytest.raises(ManifestError):
        apply_external_path_edit_request(assoc=assoc, path=path, request=bad_request)
