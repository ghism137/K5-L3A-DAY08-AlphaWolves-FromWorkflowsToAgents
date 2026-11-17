"""B4 statistics, standard library only.

* bootstrap_ci   : percentile bootstrap 95% CI for a pass rate, resampling CLAIMS (all seeds of a claim move
                   together, because trials of one claim are not independent).
* wilson_ci      : Wilson score interval on trials, shown next to the bootstrap because a bootstrap CI collapses
                   to a point when every trial passes.
* mcnemar_exact  : exact two-sided McNemar test on paired (claim, seed) outcomes of two shapes.
* sign_test      : the same discordant pairs, reported as a sign test (identical p-value, listed for clarity).
"""

from __future__ import annotations

import math
import random
from typing import Sequence


def bootstrap_ci(
    outcomes_by_claim: dict[str, Sequence[bool]],
    *,
    resamples: int = 10000,
    seed: int = 20261117,
    level: float = 0.95,
) -> tuple[float, float]:
    claims = sorted(outcomes_by_claim)
    rng = random.Random(seed)
    rates = []
    for _ in range(resamples):
        picked = [outcomes_by_claim[rng.choice(claims)] for _ in claims]
        total = sum(len(o) for o in picked)
        rates.append(sum(sum(o) for o in picked) / total)
    rates.sort()
    lo = rates[int(((1 - level) / 2) * resamples)]
    hi = rates[min(resamples - 1, int((1 - (1 - level) / 2) * resamples))]
    return lo, hi


def paired_bootstrap_diff_ci(
    a_by_claim: dict[str, Sequence[bool]],
    b_by_claim: dict[str, Sequence[bool]],
    *,
    resamples: int = 10000,
    seed: int = 20261117,
    level: float = 0.95,
) -> tuple[float, float]:
    """CI of pass_rate(a) - pass_rate(b), resampling the same claims for both shapes."""
    claims = sorted(set(a_by_claim) & set(b_by_claim))
    rng = random.Random(seed)
    diffs = []
    for _ in range(resamples):
        picked = [rng.choice(claims) for _ in claims]
        ta = sum(len(a_by_claim[c]) for c in picked)
        tb = sum(len(b_by_claim[c]) for c in picked)
        diffs.append(sum(sum(a_by_claim[c]) for c in picked) / ta - sum(sum(b_by_claim[c]) for c in picked) / tb)
    diffs.sort()
    return diffs[int(((1 - level) / 2) * resamples)], diffs[min(resamples - 1, int((1 - (1 - level) / 2) * resamples))]


def wilson_ci(successes: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def mcnemar_exact(only_a: int, only_b: int) -> float:
    """Two-sided exact p-value. only_a = pairs where a passed and b failed, only_b = the reverse."""
    n = only_a + only_b
    if n == 0:
        return 1.0
    k = min(only_a, only_b)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def sign_test(only_a: int, only_b: int) -> float:
    return mcnemar_exact(only_a, only_b)
