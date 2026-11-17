"""B4: statistics and variants. Standard library only, offline."""

from __future__ import annotations

import math

import pytest

from bonus import stats, variants
from bonus.run_ablation import analyse
from lab8.mock_llm import complete as real_complete
from lab8.shapes import SHAPES, swarm_reference, orchestrator
from lab8.db import connect


# ---- statistics -----------------------------------------------------------------------------

def test_mcnemar_exact_known_values():
    assert stats.mcnemar_exact(0, 0) == 1.0
    assert stats.mcnemar_exact(1, 0) == 1.0          # one discordant pair can never be significant
    assert stats.mcnemar_exact(5, 0) == pytest.approx(2 / 32)
    assert stats.mcnemar_exact(10, 0) == pytest.approx(2 / 1024)
    assert stats.mcnemar_exact(3, 3) == 1.0
    assert stats.sign_test(7, 2) == stats.mcnemar_exact(2, 7)  # symmetric


def test_wilson_interval_for_all_pass_is_not_a_point():
    lo, hi = stats.wilson_ci(70, 70)
    assert hi == pytest.approx(1.0)
    assert 0.94 < lo < 0.96  # bootstrap would say [1, 1]; Wilson keeps the uncertainty
    assert stats.wilson_ci(0, 0) == (0.0, 1.0)


def test_bootstrap_is_reproducible_and_collapses_when_everything_passes():
    all_pass = {f"C-{i}": [True] * 5 for i in range(14)}
    assert stats.bootstrap_ci(all_pass, resamples=500) == (1.0, 1.0)
    mixed = {**all_pass, "C-13": [True, True, True, True, False]}
    a = stats.bootstrap_ci(mixed, resamples=500)
    assert a == stats.bootstrap_ci(mixed, resamples=500)  # fixed rng seed
    assert 0.9 < a[0] <= a[1] <= 1.0


def test_paired_bootstrap_difference_contains_observed_difference():
    a = {f"C-{i}": [True] * 5 for i in range(14)}
    b = {**a, "C-0": [False] * 5}
    lo, hi = stats.paired_bootstrap_diff_ci(a, b, resamples=800)
    assert lo <= 5 / 70 <= hi


# ---- variants (same signature, same evaluator) -------------------------------------------------

def _run(shape_fn, public_db, claim_id="C-001", seed=11):
    return shape_fn(claim_id, seed=seed, store_path=str(public_db))


def test_rules_only_makes_no_model_call_and_still_pays(public_db):
    result = _run(variants.rules_only, public_db)
    assert result.model_calls == 0
    assert result.status == "resolved" and result.proposal_amount == 35000


def test_no_needs_info_gate_turns_missing_order_into_escalation(public_db):
    result = _run(variants.no_needs_info_gate, public_db, "C-004")
    assert result.status == "escalated"  # the label wants needs_info: this is the ablation's visible damage


def test_no_zero_gate_still_denies_but_goes_through_the_host(public_db):
    result = _run(variants.no_zero_gate, public_db, "C-002")
    assert result.status == "denied" and result.proposal_amount == 0 and result.refund_effects == []
    conn = connect(public_db)
    try:
        n = conn.execute("SELECT COUNT(*) FROM audit_events WHERE claim_id = 'C-002' AND event_type = 'policy_denied'").fetchone()[0]
    finally:
        conn.close()
    assert n == 1  # the host wrote an audit the contract says a shape-side denial must not produce


def test_swarm_pruned_drops_peer_and_parse_calls_deterministically(public_db):
    full = _run(SHAPES["swarm"], public_db, "C-003", 22).model_calls
    runs = {_run(variants.swarm_pruned, public_db, "C-003", 22).model_calls for _ in range(2)}
    assert len(runs) == 1 and runs.pop() <= full
    assert swarm_reference.complete is real_complete  # patch is always undone


def test_pruning_decision_depends_only_on_seed_purpose_prompt():
    assert variants._dropped(11, "peer", "x") == variants._dropped(11, "peer", "x")
    rate = sum(variants._dropped(s, "peer", "x") for s in range(400)) / 400
    assert math.isclose(rate, variants.PRUNE_RATE, abs_tol=0.1)


def test_orchestrator_without_model_turns_is_cheaper_and_equally_correct(public_db):
    full = _run(SHAPES["orchestrator"], public_db, "C-003", 11)
    ablated = _run(variants.orchestrator_no_model_turns, public_db, "C-003", 11)
    assert ablated.model_calls == full.model_calls - 2
    assert (ablated.status, ablated.proposal_amount) == (full.status, full.proposal_amount)
    assert orchestrator.complete is real_complete


# ---- analysis ---------------------------------------------------------------------------------

def _fake_benchmark():
    trials = []
    for shape, fails in (("workflow", set()), ("other", {("C-01", 11)})):
        for claim in ("C-01", "C-02", "C-03"):
            for seed in (11, 22):
                ok = (claim, seed) not in fails
                trials.append({"shape": shape, "claim_id": claim, "seed": seed, "passed": ok,
                               "reason": "ok" if ok else "refund_mismatch", "status": "denied", "cost_estimate": 10.0})
    by_shape = {s: {"pass_rate": 1.0 if s == "workflow" else 5 / 6, "pass_5": 1.0, "seed_variance": 0.0,
                    "cost_per_success_vnd": 10.0, "mean_model_calls": 1.0} for s in ("workflow", "other")}
    return {"controlled_variables": {}, "by_shape": by_shape, "trials": trials}


def test_analyse_counts_discordant_pairs_and_claims():
    out = analyse(_fake_benchmark(), "data/public_claims.jsonl")
    cmp = out["comparisons_vs_chosen"]["other"]
    assert (cmp["only_chosen_passes"], cmp["only_other_passes"]) == (1, 0)
    assert cmp["mcnemar_exact_p"] == 1.0
    assert (cmp["claims_only_chosen_passes"], cmp["claims_only_other_passes"]) == (1, 0)
    assert cmp["pass_metrics_unchanged"] is False
