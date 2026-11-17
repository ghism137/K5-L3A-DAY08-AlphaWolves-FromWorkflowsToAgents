"""B7 grader audit. One command: python -m pytest -q tests/test_bonus_grader_audit.py

The three `summarize` candidates (and the official `lab8.metrics.summarize`, as a fourth column)
are put through the metamorphic relations. The tests pin the VERDICT of each variant, so the
suite stays green while it documents which variant deviates and on which metric.
If a relation flips for a variant, the test fails and says which one.
"""

from __future__ import annotations

import pytest

from bonus import grader_relations as gr
from lab8.compensation import quote

# True = the relation holds for that variant. False = the variant deviates (see tests below for why).
EXPECTED = {
    "infra_errors_do_not_move_pass_rate": {"official": False, "grader_a": True, "grader_b": True, "grader_c": False},
    "duplicated_list_keeps_rates_doubles_totals": {"official": False, "grader_a": False, "grader_b": False, "grader_c": False},
    "infra_replace_keeps_pass5": {"official": False, "grader_a": False, "grader_b": False, "grader_c": False},
    "permutation_invariance": {"official": True, "grader_a": False, "grader_b": True, "grader_c": True},
}


@pytest.mark.parametrize("variant", sorted(gr.VARIANTS))
@pytest.mark.parametrize("relation", sorted(gr.RELATIONS))
def test_relation_verdict_for_variant(variant, relation):
    violations = gr.RELATIONS[relation](gr.VARIANTS[variant])
    assert (not violations) == EXPECTED[relation][variant], violations


def _metrics(variant: str, relation: str) -> set[str]:
    return {v["metric"] for v in gr.RELATIONS[relation](gr.VARIANTS[variant])}


def test_grader_c_counts_infra_trials_as_wrong_decisions():
    """Names the behaviour: C turns infra_error into passed=False, so pass rate drops 0.75 -> 0.5625."""
    metrics = _metrics("grader_c", "infra_errors_do_not_move_pass_rate")
    assert {"pass_rate", "graded_trials"} <= metrics
    fixture = gr.load_fixture("infra")
    a = gr.grader_c.summarize(fixture["a"])["workflow"]["pass_rate"]
    b = gr.grader_c.summarize(fixture["b"])["workflow"]["pass_rate"]
    assert (a, b) == (0.75, 0.5625)


def test_grader_a_double_counts_first_trial_cost_per_claim():
    """Names the behaviour: A adds the cost of the first graded trial of every claim a second time."""
    assert {"cost_per_success_vnd", "total_simulated_cost_vnd (x2)"} <= _metrics(
        "grader_a", "duplicated_list_keeps_rates_doubles_totals"
    )
    rows = gr.load_fixture("duplicate")["a"]
    plain = gr.official_summarize(rows)["workflow"]["total_simulated_cost_vnd"]
    first_per_claim = {}
    for row in rows:
        first_per_claim.setdefault(row["claim_id"], row["cost_estimate"])
    assert gr.grader_a.summarize(rows)["workflow"]["total_simulated_cost_vnd"] == plain + sum(first_per_claim.values())


def test_grader_a_cost_depends_on_trial_order():
    """Same trials in another order give another cost, because 'first seen' per claim changes."""
    assert "cost_per_success_vnd (reversed)" in _metrics("grader_a", "permutation_invariance")


def test_grader_b_only_fails_where_the_official_summarize_fails_too():
    """B matches the official metric except that it leaves infra trials out of graded counts."""
    dup = _metrics("grader_b", "duplicated_list_keeps_rates_doubles_totals")
    assert dup == {"pass_5"}  # inherited from lab8.metrics: len(claim_rows) == len(seeds) rejects duplicates
    assert _metrics("official", "duplicated_list_keeps_rates_doubles_totals") == {"pass_5"}


def test_delay_2_vs_3_flips_the_business_decision():
    fixture = gr.load_fixture("claim_delay")
    amounts = [quote(fixture[s]["order"], fixture["policies"], as_of=fixture["as_of"]).amount_vnd for s in ("a", "b")]
    assert amounts == [0, fixture["b"]["order"]["shipping_fee_vnd"]]
    assert gr.check_delay_relation()["flips_to_shipping_fee"] is True


def test_new_relation_expected_value_is_computed_without_summarize():
    """a: 4 of 6 claims pass every seed. b: one trial of a passing claim is infra, so 3 of 5 evaluable."""
    a, b, victim = gr.build_infra_replace_case()
    assert gr.expected_pass5(a) == pytest.approx(4 / 6)
    assert gr.expected_pass5(b) == pytest.approx(3 / 5)
    assert victim == "C-01"
    # B reports 0.5: it still counts the victim claim in the denominator and as a failure.
    assert gr.grader_b.summarize(b)["workflow"]["pass_5"] == pytest.approx(0.5)


def test_new_relation_catches_what_the_three_given_relations_do_not():
    """grader_b passes the given infra relation but still fails the new one."""
    assert gr.check_infra(gr.VARIANTS["grader_b"]) == []
    assert gr.check_infra_replace(gr.VARIANTS["grader_b"]) != []
