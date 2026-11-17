"""B4: read the benchmark file and write confidence intervals, paired tests and safety counts.

    python -m bonus.run_ablation --benchmark reports/bonus_benchmark.json --out reports/bonus_ablation.json

All numbers come from the trials in the benchmark file; nothing is typed by hand.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bonus.stats import bootstrap_ci, mcnemar_exact, paired_bootstrap_diff_ci, sign_test, wilson_ci
from lab8.config_loader import repo_path
from lab8.db import load_jsonl

CHOSEN = "workflow"


def _outcomes(trials: list[dict[str, Any]], shape: str) -> dict[tuple[str, int], bool]:
    return {(t["claim_id"], t["seed"]): bool(t["passed"]) for t in trials if t["shape"] == shape and t["passed"] is not None}


def _by_claim(outcomes: dict[tuple[str, int], bool]) -> dict[str, list[bool]]:
    grouped: dict[str, list[bool]] = {}
    for (claim, _seed), ok in sorted(outcomes.items()):
        grouped.setdefault(claim, []).append(ok)
    return grouped


def analyse(benchmark: dict[str, Any], claims_path: str) -> dict[str, Any]:
    trials = benchmark["trials"]
    labels = {row["claim_id"]: row["expected"] for row in load_jsonl(claims_path)}
    no_approval = {c for c, exp in labels.items() if not exp.get("approval_ok")}
    shapes: dict[str, Any] = {}
    for shape, stats in benchmark["by_shape"].items():
        outcomes = _outcomes(trials, shape)
        n = len(outcomes)
        ok = sum(outcomes.values())
        rows = [t for t in trials if t["shape"] == shape]
        lo, hi = bootstrap_ci(_by_claim(outcomes))
        wlo, whi = wilson_ci(ok, n)
        shapes[shape] = {
            "trials": n,
            "successes": ok,
            "pass_rate": stats["pass_rate"],
            "pass_5": stats["pass_5"],
            "seed_variance": stats["seed_variance"],
            "cost_per_success_vnd": stats["cost_per_success_vnd"],
            "mean_model_calls": stats["mean_model_calls"],
            "bootstrap_ci95_by_claim": [lo, hi],
            "wilson_ci95_by_trial": [wlo, whi],
            "secret_leak_count": sum(1 for t in rows if str(t["reason"]).startswith("forbidden_substring")),
            "approval_bypass_count": sum(1 for t in rows if t["claim_id"] in no_approval and t["status"] == "resolved"),
        }
    base = _outcomes(trials, CHOSEN)
    comparisons: dict[str, Any] = {}
    for shape in benchmark["by_shape"]:
        if shape == CHOSEN:
            continue
        other = _outcomes(trials, shape)
        keys = sorted(set(base) & set(other))
        only_base = sum(1 for k in keys if base[k] and not other[k])
        only_other = sum(1 for k in keys if other[k] and not base[k])
        dlo, dhi = paired_bootstrap_diff_ci(_by_claim({k: base[k] for k in keys}), _by_claim({k: other[k] for k in keys}))
        # Claim level: a claim passes when all its seeds pass. Seeds of one claim are not independent
        # (MockLLM is deterministic per seed, the order row never changes), so this is the honest n.
        base_claims, other_claims = _by_claim({k: base[k] for k in keys}), _by_claim({k: other[k] for k in keys})
        claim_only_base = sum(1 for c in base_claims if all(base_claims[c]) and not all(other_claims[c]))
        claim_only_other = sum(1 for c in base_claims if all(other_claims[c]) and not all(base_claims[c]))
        s0, s1 = shapes[CHOSEN], shapes[shape]
        comparisons[shape] = {
            "paired_trials": len(keys),
            "only_chosen_passes": only_base,
            "only_other_passes": only_other,
            "mcnemar_exact_p": mcnemar_exact(only_base, only_other),
            "sign_test_p": sign_test(only_base, only_other),
            "paired_claims": len(base_claims),
            "claims_only_chosen_passes": claim_only_base,
            "claims_only_other_passes": claim_only_other,
            "claim_level_mcnemar_exact_p": mcnemar_exact(claim_only_base, claim_only_other),
            "pass_rate_diff_chosen_minus_other": s0["pass_rate"] - s1["pass_rate"],
            "pass_rate_diff_bootstrap_ci95": [dlo, dhi],
            "cost_per_success_ratio_other_over_chosen": (
                s1["cost_per_success_vnd"] / s0["cost_per_success_vnd"] if s0["cost_per_success_vnd"] else None
            ),
            "pass_metrics_unchanged": only_base == 0 and only_other == 0,
        }
    return {
        "chosen_shape": CHOSEN,
        "controlled_variables": benchmark["controlled_variables"],
        "shapes": shapes,
        "comparisons_vs_chosen": comparisons,
        "notes": {
            "bootstrap": "percentile, 10000 resamples, claims resampled with all their seeds, rng seed 20261117",
            "mcnemar": "exact two-sided on paired (claim, seed) outcomes; discordant pairs only. Seeds of one claim are correlated, so the trial-level p-value is optimistic; claim_level_mcnemar_exact_p uses claims (all seeds pass) as the unit",
            "approval_bypass_count": "trials with status resolved on claims whose label has approval_ok=false (public set)",
            "secret_leak_count": "trials failed with reason forbidden_substring (CANARY or personal data found in trace/result)",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="reports/bonus_benchmark.json")
    parser.add_argument("--claims", default=str(repo_path("data", "public_claims.jsonl")))
    parser.add_argument("--out", default="reports/bonus_ablation.json")
    args = parser.parse_args(argv)
    benchmark = json.loads(Path(args.benchmark).read_text(encoding="utf-8"))
    result = analyse(benchmark, args.claims)
    result["source_benchmark"] = args.benchmark
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{'shape':<26}{'pass':>7}{'pass^5':>8}{'cost/succ':>11}{'CI95 (claims)':>18}{'leak':>6}{'bypass':>8}{'p vs wf':>9}")
    for shape, s in result["shapes"].items():
        cmp = result["comparisons_vs_chosen"].get(shape)
        p = f"{cmp['mcnemar_exact_p']:.3f}" if cmp else "-"
        ci = f"[{s['bootstrap_ci95_by_claim'][0]:.3f},{s['bootstrap_ci95_by_claim'][1]:.3f}]"
        print(f"{shape:<26}{s['pass_rate']:>7.3f}{s['pass_5']:>8.3f}{s['cost_per_success_vnd'] or 0:>11.2f}{ci:>18}{s['secret_leak_count']:>6}{s['approval_bypass_count']:>8}{p:>9}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
