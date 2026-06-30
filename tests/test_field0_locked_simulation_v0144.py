from __future__ import annotations

import pytest

from rank3_enforced.field0_locked_simulation import (
    ADMISSIBILITY_REGISTRY,
    Field0Configuration,
    Field0LockedSimulationRunner,
    FieldPoint,
    FrozenAdmissibilitySpec,
    OperationalConstraintError,
    PreRunSimulationContract,
    _normalize_assoc,
    make_contract,
    run_exploratory,
)


def test_field0_locked_runner_passes_operational_constraints():
    contract = make_contract(spec_id="LOCKED_PURE_GRADIENT_STATIC_ASSOCIATIONS", cycles=4, point_count=6)
    reports = Field0LockedSimulationRunner(contract).run()
    compliance = reports["OPERATIONAL_CONSTRAINT_COMPLIANCE_REPORT.json"]
    assert compliance["passed"]
    assert compliance["constraints"]["field0_values_and_associations_may_be_imposed"]
    assert not compliance["constraints"]["later_field_values_may_be_imposed"]
    assert not compliance["constraints"]["later_field_associations_may_be_imposed"]
    assert not compliance["constraints"]["admissibility_changes_allowed_during_run"]
    assert compliance["constraints"]["admissibility_variation_allowed_pre_run"]
    assert len(set(compliance["admissibility_hash_by_field"])) == 1


def test_admissibility_variation_is_allowed_only_pre_run():
    pure = Field0LockedSimulationRunner(make_contract(spec_id="LOCKED_PURE_GRADIENT_STATIC_ASSOCIATIONS", cycles=2)).run()
    least = Field0LockedSimulationRunner(make_contract(spec_id="LOCKED_LEAST_GRADIENT_REASSOCIATION", cycles=2)).run()
    pure_spec = pure["FROZEN_ADMISSIBILITY_SPEC_REPORT.json"]["admissibility"]
    least_spec = least["FROZEN_ADMISSIBILITY_SPEC_REPORT.json"]["admissibility"]
    assert pure_spec["id"] != least_spec["id"]
    assert pure_spec["hash"] != least_spec["hash"]
    assert pure_spec["created_before_run"]
    assert least_spec["created_before_run"]


def test_unregistered_or_mutated_admissibility_spec_is_rejected():
    base = ADMISSIBILITY_REGISTRY["LOCKED_PURE_GRADIENT_STATIC_ASSOCIATIONS"]
    mutated = FrozenAdmissibilitySpec(
        id=base.id,
        name=base.name,
        scalar_update_rule=base.scalar_update_rule,
        association_update_rule=base.association_update_rule,
        topology_update_rule=base.topology_update_rule,
        candidate_pool_rule=base.candidate_pool_rule,
        burden_terms=base.burden_terms,
        parameters=(("epsilon2_k", 0.123),),
    )
    contract = PreRunSimulationContract(field0=make_contract().field0, admissibility=mutated, cycles=1)
    with pytest.raises(OperationalConstraintError, match="differs from locked registry"):
        Field0LockedSimulationRunner(contract)


def test_structure_labels_are_rejected_from_field0_generator_surface():
    points = (
        FieldPoint("P0", 1.0, _normalize_assoc(["P1", "P2", "P1"]), (("structure_label", "photon_like"),)),
        FieldPoint("P1", -1.0, _normalize_assoc(["P2", "P0", "P2"])),
        FieldPoint("P2", 0.5, _normalize_assoc(["P0", "P1", "P0"])),
    )
    contract = PreRunSimulationContract(
        field0=Field0Configuration(points=points),
        admissibility=ADMISSIBILITY_REGISTRY["LOCKED_PURE_GRADIENT_STATIC_ASSOCIATIONS"],
        cycles=1,
    )
    with pytest.raises(OperationalConstraintError, match="forbidden structure/target keys"):
        Field0LockedSimulationRunner(contract)


def test_association_to_non_field0_point_is_rejected():
    points = (
        FieldPoint("P0", 1.0, _normalize_assoc(["P1", "P2", "P3"])),
        FieldPoint("P1", -1.0, _normalize_assoc(["P2", "P0", "P2"])),
        FieldPoint("P2", 0.5, _normalize_assoc(["P0", "P1", "P0"])),
    )
    contract = PreRunSimulationContract(
        field0=Field0Configuration(points=points),
        admissibility=ADMISSIBILITY_REGISTRY["LOCKED_PURE_GRADIENT_STATIC_ASSOCIATIONS"],
        cycles=1,
    )
    with pytest.raises(OperationalConstraintError, match="does not reference a field-0 point"):
        Field0LockedSimulationRunner(contract)


def test_conjugate_split_is_authorized_by_pre_run_admissibility_not_runner_special_construction():
    reports = Field0LockedSimulationRunner(
        make_contract(spec_id="LOCKED_CONJUGATE_SPLIT_ON_FIRST_ASSOCIATION", cycles=2, point_count=4, vacuum=True)
    ).run()
    assoc = reports["ASSOCIATION_TRANSITION_LEDGER.json"]["records"]
    split_events = [r for r in assoc if r.get("event") == "admissible_topology_transition"]
    assert split_events
    assert all(r["authorized_by_pre_run_admissibility_hash"] for r in split_events)
    assert all(not r["runner_special_construction"] for r in split_events)
    assert all(not r["structure_label_used"] for r in split_events)


def test_least_gradient_reassociation_uses_single_functional_for_all_slots():
    reports = Field0LockedSimulationRunner(
        make_contract(spec_id="LOCKED_LEAST_GRADIENT_REASSOCIATION", cycles=2, point_count=5)
    ).run()
    burden = reports["ADMISSIBILITY_BURDEN_LEDGER.json"]
    assert burden["single_functional_for_all_slots"]
    assert burden["records"]
    assert all(r["single_functional_for_all_slots"] for r in burden["records"])
    assert all(not r["slot_role_known_to_generator"] for r in burden["records"])
    assert all(not r["target_tuple_used"] for r in burden["records"])


def test_postrun_observer_readout_does_not_feed_generator():
    reports = Field0LockedSimulationRunner(make_contract(cycles=3)).run()
    observer = reports["POSTRUN_OBSERVER_READOUT_REPORT.json"]
    assert observer["observer_output_feeds_generator"] is False
    assert observer["structure_labels_assigned_during_run"] is False
    assert all(r["observer_only"] and not r["feeds_generator"] for r in observer["lambda_records"])


def test_exploratory_multi_run_reports_all_locked_specs(tmp_path):
    reports = run_exploratory(
        output_root=tmp_path,
        spec_ids=["LOCKED_PURE_GRADIENT_STATIC_ASSOCIATIONS", "LOCKED_LEAST_GRADIENT_REASSOCIATION"],
        cycles=2,
        point_count=4,
    )
    assert reports["EXPLORATORY_VERDICT_REPORT.json"]["all_runs_passed_operational_constraints"]
    assert (tmp_path / "FIELD0_INPUT_CONFIGURATION_REPORT.json").exists()
    runs = reports["FROZEN_ADMISSIBILITY_SPEC_REPORT.json"]["runs"]
    assert set(runs) == {"LOCKED_PURE_GRADIENT_STATIC_ASSOCIATIONS", "LOCKED_LEAST_GRADIENT_REASSOCIATION"}


def test_legacy_runners_are_quarantined_as_historical_diagnostics():
    reports = Field0LockedSimulationRunner(make_contract(cycles=1)).run()
    legacy = reports["LEGACY_RUNNER_QUARANTINE_REPORT.json"]
    modules = {r["module"] for r in legacy["legacy_runners"]}
    assert "rank3_enforced.endpoint_class_path_response_separation" in modules
    assert "rank3_enforced.vacuum_admissibility_variation" in modules
    assert "rank3_enforced.whole_field_conjugate_vacuum" in modules
    assert legacy["legacy_runners_available_only_as_historical_diagnostics"]
