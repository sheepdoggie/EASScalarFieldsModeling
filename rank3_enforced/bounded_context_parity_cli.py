from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

import scalar_field_geometry as sfg
from .bounded_context_soo import (
    BoundedContextSOOUpdateRule,
    BoundednessDerivedStiffnessProfile,
)
from .controls import CertifiedIdentityRemapRule
from .fingerprints import stable_json_hash


def _make_state(assoc: np.ndarray, *, rule_name: str, metadata: dict[str, Any]) -> sfg.FrozenAssociationState:
    fp = sfg.association_fingerprint(
        assoc=np.asarray(assoc, dtype=np.int64),
        step=0,
        rule_name=rule_name,
        parent_fingerprint=None,
        metadata=metadata,
    )
    return sfg.FrozenAssociationState(
        assoc=np.asarray(assoc, dtype=np.int64),
        step=0,
        rule_name=rule_name,
        fingerprint=fp,
        parent_fingerprint=None,
        metadata=metadata,
        allow_self_association=False,
    )


def build_triangle_field(depth: int = 7, extra_vacuum: int = 32) -> dict[str, Any]:
    names: list[str] = []
    roles: list[str] = []
    shell: list[int] = []
    core: list[int] = []
    for r in range(3):
        core.append(len(names)); names.append(f"c{r}"); roles.append("core_triangle"); shell.append(0)
    dressing: list[int] = []
    for r in range(3):
        dressing.append(len(names)); names.append(f"d{r}"); roles.append("dressing"); shell.append(1)
    tree: dict[tuple[int, int, int], int] = {}
    for r in range(3):
        for level in range(1, depth + 1):
            for b in range(2 ** level):
                idx = len(names); tree[(r, level, b)] = idx
                names.append(f"v{r}_{level}_{b}"); roles.append(f"exterior_shell_{level}"); shell.append(level + 1)
    vac: list[int] = []
    for j in range(extra_vacuum):
        idx = len(names); vac.append(idx); names.append(f"vac{j}"); roles.append("background_vacuum"); shell.append(depth + 2)
    N = len(names)
    assoc = np.zeros((N, 3), dtype=np.int64)
    for r in range(3):
        assoc[core[r], 0] = core[(r + 1) % 3]
        assoc[core[r], 1] = core[(r - 1) % 3]
        assoc[core[r], 2] = dressing[r]
    for r in range(3):
        assoc[dressing[r], 0] = core[r]
        assoc[dressing[r], 1] = tree[(r, 1, 0)]
        assoc[dressing[r], 2] = tree[(r, 1, 1)]
    for r in range(3):
        for level in range(1, depth + 1):
            for b in range(2 ** level):
                idx = tree[(r, level, b)]
                inward = dressing[r] if level == 1 else tree[(r, level - 1, b // 2)]
                assoc[idx, 0] = inward
                if level < depth:
                    assoc[idx, 1] = tree[(r, level + 1, 2 * b)]
                    assoc[idx, 2] = tree[(r, level + 1, 2 * b + 1)]
                else:
                    assoc[idx, 1] = vac[(2 * b) % extra_vacuum]
                    assoc[idx, 2] = vac[(2 * b + 1) % extra_vacuum]
    for j, idx in enumerate(vac):
        assoc[idx, 0] = vac[(j + 1) % extra_vacuum]
        assoc[idx, 1] = vac[(j - 1) % extra_vacuum]
        assoc[idx, 2] = vac[(j + 7) % extra_vacuum]
    return {"names": names, "roles": np.asarray(roles), "shell": np.asarray(shell), "core": core, "dressing": dressing, "vac": vac, "assoc": assoc}


def build_lepton_like_field(depth: int = 5, extra_vacuum: int = 36) -> dict[str, Any]:
    geom = build_triangle_field(depth=depth, extra_vacuum=extra_vacuum)
    roles = geom["roles"].astype(object)
    roles[roles == "core_triangle"] = "lepton_core_triangle"
    roles[roles == "dressing"] = "fixed_dressing_contact"
    geom["roles"] = roles.astype(str)
    return geom


def stiffness_values(geom: dict[str, Any], *, Kt: float, mode: str) -> np.ndarray:
    roles = geom["roles"]
    N = len(roles)
    if mode == "uniform_whole_field":
        return np.full(N, float(Kt), dtype=np.float64)
    if mode != "bounded_decay":
        raise ValueError(f"unknown K mode {mode}")
    K = np.zeros(N, dtype=np.float64)
    core_mask = (roles == "core_triangle") | (roles == "lepton_core_triangle")
    dressing_mask = (roles == "dressing") | (roles == "fixed_dressing_contact")
    K[core_mask] = Kt
    K[dressing_mask] = Kt / 3.0
    for role in sorted(set(str(r) for r in roles)):
        if role.startswith("exterior_shell_"):
            level = int(role.rsplit("_", 1)[-1])
            K[roles == role] = Kt / (3.0 ** (level + 1))
    K[roles == "background_vacuum"] = 0.0
    return K


def initial_phi(geom: dict[str, Any], kind: str) -> np.ndarray:
    N = len(geom["roles"])
    phi = np.zeros(N, dtype=np.float64)
    core = geom["core"]
    dressing = geom["dressing"]
    if kind == "core_common":
        phi[core] = 1.0
    elif kind == "core_plus_dressing_common":
        phi[core] = 1.0
        phi[dressing] = 1.0 / 3.0
    elif kind == "charge_like_boundary_dressing":
        phi[core] = 1.0
        phi[dressing] = -1.0 / 3.0
    elif kind == "zero_sum_core":
        phi[core[0]] = 1.0
        phi[core[1]] = -0.5
        phi[core[2]] = -0.5
    else:
        raise ValueError(f"unknown init {kind}")
    return phi


def run_reference(geom: dict[str, Any], phi0: np.ndarray, K: np.ndarray, *, eps: float, steps: int) -> np.ndarray:
    assoc = np.asarray(geom["assoc"], dtype=np.int64)
    prev = phi0.copy()
    curr = phi0.copy()
    hist = [curr.copy()]
    for _ in range(steps):
        context_mean = curr[assoc].mean(axis=1)
        nxt = 2.0 * curr - prev - (eps ** 2) * K * (curr - context_mean)
        prev, curr = curr, np.asarray(nxt, dtype=np.float64)
        hist.append(curr.copy())
    return np.asarray(hist, dtype=np.float64)


def _zero_triplet_lift(pair_weights: np.ndarray) -> np.ndarray:
    n = int(np.asarray(pair_weights).shape[0])
    return np.zeros((n, n, n), dtype=np.float64)


def run_framework(geom: dict[str, Any], phi0: np.ndarray, K: np.ndarray, *, eps: float, steps: int) -> tuple[np.ndarray, BoundedContextSOOUpdateRule, sfg.FrozenAssociationState]:
    state = _make_state(
        geom["assoc"],
        rule_name="bounded_context_parity_geometry",
        metadata={"diagnostic": "bounded_context_soo parity gate"},
    )
    profile = BoundednessDerivedStiffnessProfile(
        values=K,
        source_kind="boundedness_derived_context_candidate",
        details={"parity_gate": True},
    )
    rule = BoundedContextSOOUpdateRule(stiffness_profile=profile, epsilon=eps)
    # Use the framework rule and ScalarUpdateContext directly. The parity gate is
    # operator-level; building all-pairs path/tensor snapshots is irrelevant to
    # bounded_context_soo_v1 and would dominate runtime for the large shell graph.
    dummy = np.zeros((0, 0), dtype=np.float64)
    tensor = np.zeros((0, 0, 0), dtype=np.float64)
    prev = phi0.copy()
    curr = phi0.copy()
    hist = [curr.copy()]
    for ell in range(steps):
        geometry = sfg.GeometrySnapshot(
            state=state,
            ell=ell,
            phase=ell % 3,
            adjacency=dummy.astype(np.int64),
            path_lengths=dummy,
            pair_weights=dummy,
            tensor_geometry=tensor,
        )
        context = sfg.ScalarUpdateContext(
            ell=ell,
            phase=ell % 3,
            phi_current=curr.copy(),
            phi_previous=prev.copy(),
            geometry=geometry,
        )
        nxt = np.asarray(rule(context), dtype=np.float64)
        prev, curr = curr, nxt
        hist.append(curr.copy())
    return np.asarray(hist, dtype=np.float64), rule, state


def shell_label(geom: dict[str, Any], sh: int) -> str:
    roles = geom["roles"]
    shells = geom["shell"]
    if sh == 0:
        return "core"
    if sh == 1:
        return "dressing"
    if np.any((shells == sh) & (roles == "background_vacuum")):
        return "background_vacuum"
    return f"exterior_shell_{sh - 1}"


def summarize(geom: dict[str, Any], hist: np.ndarray) -> dict[str, float | int]:
    roles = geom["roles"]
    shells = geom["shell"]
    core = geom["core"]
    dressing = geom["dressing"]
    late = hist[-90:] if hist.shape[0] >= 90 else hist
    ever = np.max(np.abs(hist), axis=0) > 1e-9
    row: dict[str, float | int] = {
        "ever_nonzero_total": int(ever.sum()),
        "ever_nonzero_background": int(np.sum(ever & (roles == "background_vacuum"))),
        "max_total_norm": float(np.max(np.linalg.norm(hist, axis=1))),
        "late_mean_total_norm": float(np.mean(np.linalg.norm(late, axis=1))),
    }
    C = hist[:, core]
    D = hist[:, dressing]
    common = C.mean(axis=1)
    spread = np.sqrt(np.mean((C - common[:, None]) ** 2, axis=1)) / (np.sqrt(np.mean(C ** 2, axis=1)) + 1e-15)
    row.update({
        "late_rms_core": float(np.mean(np.sqrt(np.mean(late[:, core] ** 2, axis=1)))),
        "late_rms_dressing": float(np.mean(np.sqrt(np.mean(late[:, dressing] ** 2, axis=1)))),
        "core_late_spread_mean": float(np.mean(spread[-90:] if spread.size >= 90 else spread)),
        "core_range_min": float(np.min(C)),
        "core_range_max": float(np.max(C)),
        "dressing_range_min": float(np.min(D)),
        "dressing_range_max": float(np.max(D)),
    })
    for sh in sorted(set(int(x) for x in shells)):
        mask = shells == sh
        label = shell_label(geom, sh)
        row[f"late_rms_{label}"] = float(np.mean(np.sqrt(np.mean(late[:, mask] ** 2, axis=1))))
    return row


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run bounded_context_soo_v1 triangle/lepton parity gate.")
    parser.add_argument("--output-dir", default="/mnt/data/bounded_context_soo_framework_parity")
    parser.add_argument("--kt", type=float, default=100.0)
    parser.add_argument("--epsilon", type=float, default=0.1)
    parser.add_argument("--steps", type=int, default=360)
    args = parser.parse_args(argv)

    out = Path(args.output_dir)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sectors = {
        "triangle": build_triangle_field(depth=7, extra_vacuum=32),
        "lepton_like": build_lepton_like_field(depth=5, extra_vacuum=36),
    }
    inits = ["core_common", "core_plus_dressing_common", "charge_like_boundary_dressing", "zero_sum_core"]
    kmodes = ["bounded_decay", "uniform_whole_field"]
    summary_rows: list[dict[str, Any]] = []
    parity_rows: list[dict[str, Any]] = []

    for sector_name, geom in sectors.items():
        state = _make_state(geom["assoc"], rule_name="bounded_context_parity_geometry", metadata={"sector": sector_name})
        geo_df = {
            "point": np.arange(len(geom["roles"])),
            "name": geom["names"],
            "role": geom["roles"],
            "shell": geom["shell"],
            "assoc_0": geom["assoc"][:, 0],
            "assoc_1": geom["assoc"][:, 1],
            "assoc_2": geom["assoc"][:, 2],
        }
        for kmode in kmodes:
            geo_df[f"K_{kmode}"] = stiffness_values(geom, Kt=args.kt, mode=kmode)
        pd.DataFrame(geo_df).to_csv(out / f"geometry_and_stiffness_{sector_name}.csv", index=False)
        for kmode in kmodes:
            K = stiffness_values(geom, Kt=args.kt, mode=kmode)
            for init in inits:
                phi0 = initial_phi(geom, init)
                ref = run_reference(geom, phi0, K, eps=args.epsilon, steps=args.steps)
                fw, rule, _ = run_framework(geom, phi0, K, eps=args.epsilon, steps=args.steps)
                diff = fw - ref
                max_abs = float(np.max(np.abs(diff)))
                l2 = float(np.linalg.norm(diff))
                parity_pass = bool(max_abs <= 1e-12)
                parity_rows.append({
                    "sector": sector_name,
                    "K_mode": kmode,
                    "init": init,
                    "max_abs_framework_minus_reference": max_abs,
                    "l2_framework_minus_reference": l2,
                    "parity_pass": parity_pass,
                    "association_fingerprint": state.fingerprint,
                    "framework_execution_report_hash": rule.get_bounded_context_execution_report().fingerprint() if rule.get_bounded_context_execution_report() else None,
                })
                ref_sum = summarize(geom, ref)
                fw_sum = summarize(geom, fw)
                summary_rows.append({"sector": sector_name, "update": "reference_context", "K_mode": kmode, "init": init, **ref_sum})
                summary_rows.append({"sector": sector_name, "update": "framework_bounded_context_soo_v1", "K_mode": kmode, "init": init, **fw_sum})

                # Compact timeseries and plots for framework result.
                rows = []
                shells = geom["shell"]
                core = geom["core"]
                dressing = geom["dressing"]
                for t in range(fw.shape[0]):
                    row = {"t": t, "sector": sector_name, "K_mode": kmode, "init": init, "total_norm": float(np.linalg.norm(fw[t]))}
                    for i, c in enumerate(core): row[f"c{i}"] = float(fw[t, c])
                    for i, d in enumerate(dressing): row[f"d{i}"] = float(fw[t, d])
                    for sh in sorted(set(int(x) for x in shells)):
                        mask = shells == sh
                        row[f"rms_{shell_label(geom, sh)}"] = float(np.sqrt(np.mean(fw[t, mask] ** 2)))
                    rows.append(row)
                pd.DataFrame(rows).to_csv(out / f"timeseries_{sector_name}_{kmode}_{init}.csv", index=False)

                plt.figure(figsize=(10, 5))
                for lab in ["core", "dressing", "exterior_shell_1", "exterior_shell_2", "exterior_shell_3", "exterior_shell_5", "background_vacuum"]:
                    col = f"rms_{lab}"
                    if col in rows[0]:
                        plt.plot([r[col] for r in rows], label=lab)
                plt.title(f"{sector_name}: {kmode}, {init}")
                plt.xlabel("step")
                plt.ylabel("RMS scalar value")
                plt.legend(fontsize=7)
                plt.tight_layout()
                plt.savefig(out / f"shell_rms_{sector_name}_{kmode}_{init}.png", dpi=150)
                plt.close()

    summary = pd.DataFrame(summary_rows)
    parity = pd.DataFrame(parity_rows)
    summary.to_csv(out / "bounded_context_parity_summary.csv", index=False)
    parity.to_csv(out / "bounded_context_parity_gate.csv", index=False)

    gate = {
        "gate": "bounded_context_soo_framework_parity_v1",
        "framework_operator": "bounded_context_soo_v1",
        "reference_operator": "direct complete-rank-3 context update",
        "epsilon": float(args.epsilon),
        "Kt": float(args.kt),
        "steps": int(args.steps),
        "parity_pass": bool(parity["parity_pass"].all()),
        "max_abs_difference": float(parity["max_abs_framework_minus_reference"].max()),
        "source_provenance": "recorded in geometry/stiffness CSVs, parity CSV, execution report hashes, script/module source",
        "verdict_independence": "no charge, attraction, path-shortening, midpoint-zero, detector, or damping target used by update",
        "external_admission_verdict": "not_run",
        "admission_status": "diagnostic_only_not_certified",
    }
    (out / "PARITY_GATE.json").write_text(json.dumps(gate, indent=2, sort_keys=True), encoding="utf-8")
    (out / "README.md").write_text(
        "# bounded_context_soo_v1 framework parity gate\n\n"
        "Adds/tests the candidate boundedness-derived complete rank-3 context SOO kernel.\n\n"
        "Update law:\n"
        "Phi_next(i)=2 Phi_curr(i)-Phi_prev(i)-epsilon^2 K_i(Phi_curr(i)-mean_r Phi_curr(a_r(i))).\n\n"
        "Status: diagnostic only; external admission verdict not run.\n",
        encoding="utf-8",
    )

    zip_path = out.with_suffix(".zip")
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in out.rglob("*"):
            z.write(p, p.relative_to(out.parent))
    sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    (out / "ZIP_SHA256.txt").write_text(f"{sha}  {zip_path.name}\n", encoding="utf-8")
    # Re-add checksum file after computing zip once.
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in out.rglob("*"):
            z.write(p, p.relative_to(out.parent))
    sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    print(json.dumps({"output_dir": str(out), "zip_path": str(zip_path), "sha256": sha, **gate}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
