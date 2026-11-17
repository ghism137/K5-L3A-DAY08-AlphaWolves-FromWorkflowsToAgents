"""B7: metamorphic relations applied to every `summarize` candidate.

The three provided relations come from `grader_audit/fixtures/`. Two more are ours:

* `infra_replace_keeps_pass5` (new relation N1): turn ONE passing trial of a claim into an
  infrastructure error. That claim no longer has full-seed evidence, so it must leave the
  pass^5 denominator the same way infra trials already leave the pass-rate denominator.
* `permutation_invariance` (control N2): shuffling the trial list must not change the report.

Nothing in `grader_audit/` or `lab8/metrics.py` is modified.
"""

from __future__ import annotations

import copy
import json
import math
import random
from pathlib import Path
from typing import Any, Callable

from grader_audit import grader_a, grader_b, grader_c
from lab8.compensation import quote
from lab8.metrics import summarize as official_summarize

FIXTURES = Path(__file__).resolve().parents[1] / "grader_audit" / "fixtures"

VARIANTS: dict[str, Callable[[list[dict[str, Any]]], dict[str, Any]]] = {
    "official": official_summarize,
    "grader_a": grader_a.summarize,
    "grader_b": grader_b.summarize,
    "grader_c": grader_c.summarize,
}

# Ratios and means: must not move when the sample is duplicated.
RATE_KEYS = (
    "pass_rate",
    "pass_5",
    "seed_pass_rates",
    "seed_variance",
    "seed_min",
    "seed_max",
    "cost_per_success_vnd",
    "mean_steps",
    "p95_steps",
    "mean_model_calls",
    "mean_tool_calls",
)
# Totals: must double when the sample is duplicated.
TOTAL_KEYS = ("trials", "graded_trials", "successes", "total_simulated_cost_vnd")
# Everything computed from graded trials only: must not move when infra trials are added.
GRADED_KEYS = RATE_KEYS + ("graded_trials", "successes", "total_simulated_cost_vnd")


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / f"metamorphic_{name}.json").read_text(encoding="utf-8"))


def _same(x: Any, y: Any) -> bool:
    if isinstance(x, dict) and isinstance(y, dict):
        return x.keys() == y.keys() and all(_same(x[k], y[k]) for k in x)
    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
        return math.isclose(x, y, rel_tol=1e-9, abs_tol=1e-12)
    return x == y


def _violation(metric: str, expected: Any, actual: Any) -> dict[str, Any]:
    return {"metric": metric, "expected": expected, "actual": actual}


def _shape_stats(summarize, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return summarize(copy.deepcopy(rows))["workflow"]


def check_duplicate(summarize) -> list[dict[str, Any]]:
    fixture = load_fixture("duplicate")
    a = _shape_stats(summarize, fixture["a"])
    b = _shape_stats(summarize, fixture["b"])
    out = [_violation(k, a[k], b[k]) for k in RATE_KEYS if not _same(a[k], b[k])]
    out += [_violation(k + " (x2)", 2 * a[k], b[k]) for k in TOTAL_KEYS if not _same(2 * a[k], b[k])]
    return out


def check_infra(summarize) -> list[dict[str, Any]]:
    fixture = load_fixture("infra")
    a = _shape_stats(summarize, fixture["a"])
    b = _shape_stats(summarize, fixture["b"])
    return [_violation(k, a[k], b[k]) for k in GRADED_KEYS if not _same(a[k], b[k])]


def expected_pass5(rows: list[dict[str, Any]], *, exclude_claims: set[str] = frozenset()) -> float:
    """Independent pass^5: share of evaluable claims that pass on every seed. Not via summarize."""
    seeds = {r["seed"] for r in rows if not r.get("infra_error")}
    by_claim: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r["claim_id"] not in exclude_claims:
            by_claim.setdefault(r["claim_id"], []).append(r)
    evaluable = {c: rs for c, rs in by_claim.items() if not any(r.get("infra_error") for r in rs)}
    ok = sum(1 for rs in evaluable.values() if len(rs) == len(seeds) and all(r["passed"] for r in rs))
    return ok / len(evaluable) if evaluable else 0.0


def build_infra_replace_case() -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    """a = duplicate fixture's `a`; b = a with one trial of a fully passing claim turned into infra."""
    rows = copy.deepcopy(load_fixture("duplicate")["a"])
    claims = sorted({r["claim_id"] for r in rows})
    victim = next(c for c in claims if all(r["passed"] for r in rows if r["claim_id"] == c))
    b = copy.deepcopy(rows)
    target = [r for r in b if r["claim_id"] == victim][-1]
    target.update(passed=False, reason="timeout", infra_error=True)
    return rows, b, victim


def check_infra_replace(summarize) -> list[dict[str, Any]]:
    _, b, _victim = build_infra_replace_case()
    expected = expected_pass5(b)  # victim claim is unevaluable, so it is left out of the denominator
    actual = _shape_stats(summarize, b)["pass_5"]
    return [] if _same(expected, actual) else [_violation("pass_5", expected, actual)]


def check_permutation(summarize) -> list[dict[str, Any]]:
    rows = load_fixture("infra")["b"]
    base = _shape_stats(summarize, rows)
    out: list[dict[str, Any]] = []
    for label, order in (("reversed", list(reversed(rows))), ("shuffled", random.Random(7).sample(rows, len(rows)))):
        stats = _shape_stats(summarize, order)
        out += [_violation(f"{k} ({label})", base[k], stats[k]) for k in base if k != "reasons" and not _same(base[k], stats[k])]
    return out


RELATIONS: dict[str, Callable[[Any], list[dict[str, Any]]]] = {
    "infra_errors_do_not_move_pass_rate": check_infra,
    "duplicated_list_keeps_rates_doubles_totals": check_duplicate,
    "infra_replace_keeps_pass5": check_infra_replace,
    "permutation_invariance": check_permutation,
}


def check_delay_relation() -> dict[str, Any]:
    """delay_days 2 vs 3 with min_delay_days 3: decision must flip from 0 to the shipping fee."""
    fixture = load_fixture("claim_delay")
    amounts = {
        side: quote(fixture[side]["order"], fixture["policies"], as_of=fixture["as_of"]).amount_vnd
        for side in ("a", "b")
    }
    fee = fixture["b"]["order"]["shipping_fee_vnd"]
    return {
        "amount_delay_2": amounts["a"],
        "amount_delay_3": amounts["b"],
        "flips_to_shipping_fee": amounts["a"] == 0 and amounts["b"] == fee,
    }


def audit() -> dict[str, Any]:
    """Run every relation on every variant. Used by tests and by the JSON report."""
    matrix: dict[str, dict[str, Any]] = {}
    for variant, fn in VARIANTS.items():
        matrix[variant] = {}
        for relation, check in RELATIONS.items():
            violations = check(fn)
            matrix[variant][relation] = {"holds": not violations, "violations": violations}
    return {"delay_relation": check_delay_relation(), "matrix": matrix}
