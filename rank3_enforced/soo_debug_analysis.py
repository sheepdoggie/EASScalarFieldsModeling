from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .fingerprints import file_hash, stable_json_hash


@dataclass(frozen=True)
class SOODebugPairAnalysisReport:
    report_schema: str
    status: str
    same_run_dir: str
    opposite_run_dir: str
    output_dir: str
    initialization_context: dict[str, Any]
    run_summaries: tuple[dict[str, Any], ...]
    comparison_summary: dict[str, Any]
    generated_files: tuple[str, ...]
    forbidden_interpretations: tuple[str, ...]
    report_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"Required report is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _optional_json(path: Path) -> Any | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _orientation_from_overlay_or_name(run_dir: Path) -> str:
    overlay = _optional_json(run_dir / "overlay.json")
    if isinstance(overlay, dict):
        pc = overlay.get("path_construction") or {}
        if isinstance(pc, dict) and pc.get("orientation"):
            return str(pc["orientation"])
        for module in overlay.get("optional_modules", []) or []:
            if isinstance(module, dict) and module.get("module_id") == "charge_attraction_repulsion":
                params = module.get("params") or {}
                if params.get("orientation"):
                    return str(params["orientation"])
    name = run_dir.name.lower()
    if "opposite" in name:
        return "opposite"
    if "same" in name:
        return "same"
    return "unknown"


def _path_points(path_report: dict[str, Any]) -> list[int]:
    pts = [int(path_report.get("left_anchor"))]
    pts.extend(int(x) for x in path_report.get("path_points", []) or [])
    pts.append(int(path_report.get("right_anchor")))
    return pts


def _center_points(path_report: dict[str, Any]) -> list[int]:
    pts = [int(x) for x in path_report.get("path_points", []) or []]
    if not pts:
        return []
    n = len(pts)
    if n % 2 == 1:
        return [pts[n // 2]]
    return [pts[n // 2 - 1], pts[n // 2]]


def _role_by_point(path_facing: dict[str, Any] | None, debug: dict[str, Any]) -> dict[int, str]:
    roles: dict[int, str] = {}
    if isinstance(path_facing, dict):
        for rec in path_facing.get("records", []) or []:
            try:
                roles[int(rec["point"])] = str(rec.get("role", "declared_path_point"))
            except Exception:
                pass
    for rec in debug.get("debug_point_roles", []) or []:
        try:
            p = int(rec["point"])
            if p not in roles:
                roles[p] = str(rec.get("seed_role", "debug_neighborhood_point"))
        except Exception:
            pass
    return roles


def _depth_by_point(debug: dict[str, Any]) -> dict[int, int]:
    out: dict[int, int] = {}
    for rec in debug.get("debug_point_roles", []) or []:
        try:
            out[int(rec["point"])] = int(rec.get("min_depth_from_declared_path", -1))
        except Exception:
            pass
    return out


def _point_rows(run_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    debug = _load_json(run_dir / "RUN_DEBUG_REPORT.json")
    path_report = _load_json(run_dir / "PATH_CONSTRUCTION_REPORT.json") if (run_dir / "PATH_CONSTRUCTION_REPORT.json").is_file() else _optional_json(run_dir / "path_construction_report.json")
    if path_report is None:
        # Package currently writes this report under compiled manifest only in some older versions.
        path_report = _optional_json(run_dir / "PATH_FACING_ASSOCIATION_REPORT.json") or {}
    path_facing = _optional_json(run_dir / "PATH_FACING_ASSOCIATION_REPORT.json")
    init = _load_json(run_dir / "initialization_report.json")
    settling = _optional_json(run_dir / "INITIALIZATION_SETTLING_REPORT.json")
    init_two = _optional_json(run_dir / "INITIAL_TWO_LEDGER_REPORT.json")
    raw = _load_json(run_dir / "raw_result_package.json")
    overlay = _optional_json(run_dir / "overlay.json") or {}
    orientation = _orientation_from_overlay_or_name(run_dir)
    roles = _role_by_point(path_facing, debug)
    depths = _depth_by_point(debug)
    center_set: set[int] = set()
    path_set: set[int] = set()
    if isinstance(path_report, dict) and path_report.get("path_points") is not None:
        path_set.update(_path_points(path_report))
        center_set.update(_center_points(path_report))
    if isinstance(path_facing, dict):
        seq = []
        for rec in path_facing.get("records", []) or []:
            try:
                p = int(rec["point"])
                seq.append(p)
                path_set.add(p)
            except Exception:
                pass
    for p, role in roles.items():
        if role in ("declared_path_point", "left_anchor", "right_anchor"):
            path_set.add(p)
        if "center" in role:
            center_set.add(p)
    # If no explicit center roles, infer from path-facing records excluding anchors.
    if not center_set and isinstance(path_facing, dict):
        inner = [int(rec["point"]) for rec in path_facing.get("records", []) or [] if rec.get("role") == "declared_path_point"]
        if inner:
            n = len(inner)
            center_set.update([inner[n // 2]] if n % 2 else [inner[n // 2 - 1], inner[n // 2]])

    rows: list[dict[str, Any]] = []
    layer_summaries: dict[int, dict[str, Any]] = {}
    for layer in debug.get("transition_records", []) or []:
        ell = int(layer.get("ell", -1))
        change_recs = layer.get("soo_change_records", []) or []
        phi_values = {int(v.get("point")): float(v.get("phi")) for v in layer.get("phi_values", []) or [] if "point" in v and "phi" in v}
        for rec in change_recs:
            p = int(rec.get("point"))
            row = {
                "run_id": run_dir.name,
                "orientation": orientation,
                "ell_measurement": ell,
                "phase": rec.get("phase"),
                "point": p,
                "role": roles.get(p, "unknown"),
                "depth_from_declared_path": depths.get(p, None),
                "is_declared_path_or_anchor": p in path_set,
                "is_center_locus": p in center_set,
                "phi_curr": rec.get("phi_curr"),
                "phi_next": rec.get("phi_next"),
                "delta_phi_next_minus_curr": rec.get("delta_phi_next_minus_curr"),
                "active_associate": rec.get("active_associate"),
                "A_theta_phi_prev": rec.get("A_theta_phi_prev"),
                "Pi_A_curr": rec.get("Pi_A_curr"),
            }
            rows.append(row)
            s = layer_summaries.setdefault(ell, {"ell_measurement": ell, "orientation": orientation, "run_id": run_dir.name, "path_points": 0, "center_points": 0, "path_abs_phi_sum": 0.0, "path_abs_delta_sum": 0.0, "center_phi_values": []})
            if p in path_set:
                s["path_points"] += 1
                s["path_abs_phi_sum"] += abs(float(rec.get("phi_curr") or 0.0))
                s["path_abs_delta_sum"] += abs(float(rec.get("delta_phi_next_minus_curr") or 0.0))
            if p in center_set:
                s["center_points"] += 1
                s["center_phi_values"].append(float(rec.get("phi_curr") or 0.0))

    n_layers = None
    if isinstance(raw.get("phi_shape"), list) and raw["phi_shape"]:
        n_layers = int(raw["phi_shape"][0])
    init_cycles = int(init.get("initialization_cycles", 0))
    settling_cycles = int(settling.get("accepted_initialization_rank3_cycles", 0)) if isinstance(settling, dict) else 0
    settling_scan_cycles = int(settling.get("initialization_scan_rank3_cycles", 0)) if isinstance(settling, dict) else 0
    measurement_steps = max(0, (n_layers or 0) - 1)
    summary = {
        "run_id": run_dir.name,
        "orientation": orientation,
        "run_dir": str(run_dir),
        "initialization_mode": init.get("mode"),
        "legacy_initialization_cycles_field": init_cycles,
        "initialization_settling_enabled": bool(settling.get("enabled", False)) if isinstance(settling, dict) else False,
        "initialization_steady_state_reached": bool(settling.get("steady_state_reached", False)) if isinstance(settling, dict) else False,
        "initialization_steady_state_type": settling.get("steady_state_type") if isinstance(settling, dict) else None,
        "accepted_initialization_rank3_cycles": settling_cycles,
        "initialization_scan_rank3_cycles": settling_scan_cycles,
        "initialization_soo_steps": int(settling.get("accepted_initialization_steps", init_cycles)) if isinstance(settling, dict) else init_cycles,
        "initialization_witness_scope": settling.get("witness_scope") if isinstance(settling, dict) else None,
        "initialization_witness_rule": settling.get("witness_rule") if isinstance(settling, dict) else None,
        "initialization_witness_count": len(settling.get("witness_points", [])) if isinstance(settling, dict) else 0,
        "measurement_starts_after_initialization": bool(init.get("measurement_starts_after_initialization")),
        "measurement_layer_zero_role": "Phi_0 is phi_after_initialization; it is not an initialization cycle output inside the measurement run",
        "measurement_layers_recorded": n_layers,
        "measurement_soo_steps": measurement_steps,
        "measurement_full_rank3_cycles": measurement_steps // 3,
        "cycle_count_definition": "full_rank3_cycles=floor(measurement_soo_steps/3), after initialization epoch",
        "initial_two_ledger_hash": init.get("initial_two_ledger_hash"),
        "phi_previous_for_measurement_hash": init.get("phi_previous_for_measurement_hash"),
        "debug_point_count": debug.get("debug_point_count"),
        "debug_neighborhood_depth": debug.get("neighborhood_depth"),
        "forbidden_debug_interpretations": debug.get("forbidden_interpretations", []),
        "initial_two_ledger_present": init_two is not None,
    }
    return rows, {"summary": summary, "layer_summaries": list(layer_summaries.values())}


def _write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def analyze_soo_debug_pair(*, same_run_dir: str | Path, opposite_run_dir: str | Path, output_dir: str | Path) -> SOODebugPairAnalysisReport:
    same_dir = Path(same_run_dir).resolve()
    opposite_dir = Path(opposite_run_dir).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []
    layer_rows: list[dict[str, Any]] = []
    for run_dir in (same_dir, opposite_dir):
        rows, summary_obj = _point_rows(run_dir)
        all_rows.extend(rows)
        run_summaries.append(summary_obj["summary"])
        layer_rows.extend(summary_obj["layer_summaries"])

    _write_csv(out / "soo_path_transition_rows.csv", all_rows)
    _write_csv(out / "soo_path_layer_summaries.csv", layer_rows)

    init_context = {
        "same": run_summaries[0],
        "opposite": run_summaries[1],
        "interpretation": "measurement cycle counts are after initialization; initialization settling scan/accepted cycles are listed separately and use support-influenced exterior witness records",
    }
    comparison = {
        "same_run_id": same_dir.name,
        "opposite_run_id": opposite_dir.name,
        "row_count": len(all_rows),
        "layer_summary_count": len(layer_rows),
        "debugging_is_instrumentation_only": True,
        "soo_was_not_path_specialized_by_debugger": True,
        "analysis_status": "diagnostic_only_not_admission_verdict",
    }
    generated = (
        "SOO_DEBUG_PAIR_ANALYSIS.json",
        "soo_path_transition_rows.csv",
        "soo_path_layer_summaries.csv",
    )
    payload = {
        "report_schema": "rank3_soo_debug_pair_analysis_v1",
        "status": "diagnostic_only_not_admission_verdict",
        "same_run_dir": str(same_dir),
        "opposite_run_dir": str(opposite_dir),
        "output_dir": str(out),
        "initialization_context": init_context,
        "run_summaries": tuple(run_summaries),
        "comparison_summary": comparison,
        "generated_files": generated,
        "forbidden_interpretations": (
            "debug_neighborhood_as_special_SOO_domain",
            "nonzero_phi_as_required_for_path_participation",
            "debug_analysis_as_charge_theorem_certification",
        ),
    }
    report = SOODebugPairAnalysisReport(**payload, report_hash=stable_json_hash(payload))
    (out / "SOO_DEBUG_PAIR_ANALYSIS.json").write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
