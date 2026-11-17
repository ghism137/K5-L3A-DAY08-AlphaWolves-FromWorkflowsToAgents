"""B4 baselines and ablations. Every function has the shape signature
`run_claim(claim_id, *, seed, store_path, crash_at=None) -> RunResult` and is registered at run time
through `--extra-shape`, so it uses the same claims, seeds, prices and evaluator as the four shapes.

Baselines
* rules_only      : workflow with NO model call at all.
* swarm_pruned    : the reference swarm with its peer/parse model calls dropped at random (seeded).

Ablations of the chosen shape (workflow): one component removed at a time
* rules_only          : draft model call removed (same function as the baseline above).
* no_zero_gate        : a quote of 0 is still sent to the host instead of being denied by the shape.
* no_needs_info_gate  : the shape no longer checks for a missing order_id before lookup_order.
Ablation of orchestrator
* orchestrator_no_model_turns : the plan and investigate model turns removed.

Not copied: the REFERENCE_WEAKNESS block of the swarm. swarm_pruned calls the reference swarm and only
wraps its `complete`, so the weakness stays exactly as the reference defines it.
"""

from __future__ import annotations

import contextlib
import hashlib
import sqlite3
from typing import Any, Iterator

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete as real_complete
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes import orchestrator, swarm_reference
from lab8.shapes.common import finish
from lab8.tools import compute_compensation, get_claim_view, lookup_order, tool_cost
from lab8.trace import Trace

PRUNE_RATE = 0.5  # probability of dropping one peer/parse model call, decided by hash(seed, purpose, prompt)


def _workflow(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None,
    name: str,
    draft: bool = True,
    zero_gate: bool = True,
    needs_info_gate: bool = True,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _workflow_run(
            conn, claim_id, seed=seed, crash_at=crash_at, name=name,
            draft=draft, zero_gate=zero_gate, needs_info_gate=needs_info_gate,
        )
    finally:
        conn.close()


def _workflow_run(
    conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None, name: str,
    draft: bool, zero_gate: bool, needs_info_gate: bool,
) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id(name, claim_id, seed))

    def say(prompt: str) -> None:
        if draft:
            real_complete(budget, seed=seed, purpose="draft", prompt=prompt)

    def done(status: str, amount: int, reason: str | None) -> RunResult:
        trace.add("decision", {"status": status, "proposal_amount": int(amount), "reason": reason})
        return finish(conn, shape=name, claim_id=claim_id, seed=seed, status=status,
                      proposal_amount=amount, budget=budget, trace=trace, error_reason=reason)

    budget.add_tool(tool_cost())
    claim = get_claim_view(conn, claim_id)
    if not claim["found"]:
        return done("failed", 0, "unknown_claim")
    if needs_info_gate and not claim["order_id"]:
        say("needs_info")
        return done("needs_info", 0, "missing_order_id")

    budget.add_tool(tool_cost())
    order_view = lookup_order(conn, claim["order_id"], claim["principal_id"])
    if not order_view["visible"]:
        say("escalated")
        return done("escalated", 0, order_view["reason"])
    budget.add_tool(tool_cost())
    quote = compute_compensation(conn, order_view["order"])
    trace.add("quote", quote)
    amount = int(quote["amount_vnd"])
    if amount <= 0 and zero_gate:
        say("denied")
        return done("denied", 0, quote["reason"])

    try:
        outcome = issue_refund(conn, claim_id, amount, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise
    say(f"proposal={amount}")
    if not outcome["ok"]:
        return done("failed" if outcome["conflict"] else "denied", amount, outcome["reason"])
    return done("resolved", amount, None)


def rules_only(claim_id: str, *, seed: int, store_path: str, crash_at: str | None = None) -> RunResult:
    return _workflow(claim_id, seed=seed, store_path=store_path, crash_at=crash_at, name="rules_only", draft=False)


def no_zero_gate(claim_id: str, *, seed: int, store_path: str, crash_at: str | None = None) -> RunResult:
    return _workflow(claim_id, seed=seed, store_path=store_path, crash_at=crash_at, name="no_zero_gate", zero_gate=False)


def no_needs_info_gate(claim_id: str, *, seed: int, store_path: str, crash_at: str | None = None) -> RunResult:
    return _workflow(claim_id, seed=seed, store_path=store_path, crash_at=crash_at, name="no_needs_info_gate", needs_info_gate=False)


def _dropped(seed: int, purpose: str, prompt: str) -> bool:
    digest = hashlib.sha256(f"prune|{seed}|{purpose}|{prompt}".encode()).digest()
    return digest[0] / 255 < PRUNE_RATE


@contextlib.contextmanager
def _patched_complete(module: Any, drop) -> Iterator[None]:
    """Replace module.complete for the duration of one run. Single-threaded benchmark only."""
    original = module.complete

    def wrapper(budget: Budget, *, seed: int, purpose: str, prompt: str) -> str:
        if drop(seed, purpose, prompt):
            return ""  # call skipped: nothing is added to the budget
        return original(budget, seed=seed, purpose=purpose, prompt=prompt)

    module.complete = wrapper
    try:
        yield
    finally:
        module.complete = original


def swarm_pruned(claim_id: str, *, seed: int, store_path: str, crash_at: str | None = None) -> RunResult:
    with _patched_complete(swarm_reference, lambda s, p, pr: p in ("peer", "parse") and _dropped(s, p, pr)):
        return swarm_reference.run_claim(claim_id, seed=seed, store_path=store_path, crash_at=crash_at)


def orchestrator_no_model_turns(claim_id: str, *, seed: int, store_path: str, crash_at: str | None = None) -> RunResult:
    with _patched_complete(orchestrator, lambda s, p, pr: p in ("plan", "investigate")):
        return orchestrator.run_claim(claim_id, seed=seed, store_path=store_path, crash_at=crash_at)
