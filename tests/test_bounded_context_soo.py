from __future__ import annotations

import numpy as np

import scalar_field_geometry as sfg
from rank3_enforced.bounded_context_soo import (
    BoundedContextSOOUpdateRule,
    BoundednessDerivedStiffnessProfile,
    build_bounded_context_soo_update_rule,
)
from rank3_enforced.locked_registries import build_scalar_update_rule, registry_names


def _state() -> sfg.FrozenAssociationState:
    assoc = np.array(
        [
            [1, 2, 3],
            [2, 0, 4],
            [0, 1, 5],
            [0, 4, 5],
            [1, 3, 5],
            [2, 3, 4],
        ],
        dtype=np.int64,
    )
    fp = sfg.association_fingerprint(
        assoc=assoc,
        step=0,
        rule_name="test_bounded_context_soo",
        parent_fingerprint=None,
        metadata={"test": True},
    )
    return sfg.FrozenAssociationState(
        assoc=assoc,
        step=0,
        rule_name="test_bounded_context_soo",
        fingerprint=fp,
        parent_fingerprint=None,
        metadata={"test": True},
    )


def _geometry(state: sfg.FrozenAssociationState) -> sfg.GeometrySnapshot:
    return sfg.build_geometry_snapshot(
        state=state,
        ell=0,
        phase_rule=sfg.cyclic_phase_rule,
        graph_mode="directed",
        path_scope="completed",
        pair_weight_rule=sfg.bounded_inverse_length_pair_weight,
        triplet_lift_rule=sfg.product_triplet_lift,
    )


def test_bounded_context_soo_matches_direct_context_formula():
    state = _state()
    phi = np.array([1.0, -0.5, -0.5, 0.25, 0.0, -0.25], dtype=np.float64)
    prev = phi.copy()
    K = np.array([100.0, 100.0, 100.0, 100.0 / 3.0, 100.0 / 9.0, 0.0], dtype=np.float64)
    eps = 0.1
    rule = BoundedContextSOOUpdateRule(
        stiffness_profile=BoundednessDerivedStiffnessProfile(values=K),
        epsilon=eps,
    )
    context = sfg.ScalarUpdateContext(ell=0, phase=0, phi_current=phi, phi_previous=prev, geometry=_geometry(state))
    got = rule(context)
    expected = 2.0 * phi - prev - (eps ** 2) * K * (phi - phi[state.assoc].mean(axis=1))
    assert np.allclose(got, expected, atol=1e-14)
    report = rule.get_bounded_context_execution_report()
    assert report is not None
    assert report.passed


def test_bounded_context_soo_registry_builder():
    names = registry_names()["scalar_update_rules"]
    assert "bounded_context_soo_v1" in names
    rule = build_scalar_update_rule(
        "bounded_context_soo_v1",
        {"epsilon": 0.1, "stiffness_values": [1.0, 0.0, 2.0, 3.0, 4.0, 5.0]},
    )
    assert rule.primitive_operator_id == "bounded_context_soo_v1"


def test_bounded_context_soo_rejects_negative_stiffness():
    try:
        build_bounded_context_soo_update_rule({"stiffness_values": [1.0, -1.0, 0.0]})
    except Exception as exc:
        assert "nonnegative" in str(exc)
    else:
        raise AssertionError("negative stiffness was not rejected")
