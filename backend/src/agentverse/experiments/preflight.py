"""Estimate live reservations over two offline reference trajectories before approval."""
from agentverse.agents.gemini import Limits, request_for
from agentverse.agents.policy import RulePolicy
from agentverse.simulation.kernel import Kernel
from agentverse.simulation.runner import step


def preflight(parent: Kernel, limits: Limits) -> dict:
    totals = []
    for public_record in (False, True):
        k = Kernel(parent.state.scenario, parent.state.seed, run_id="preview")
        for event in parent.events:
            k.replay_event(event)
        if public_record:
            k.grant_evidence("evidence-harvest", grantee=None)
        while k.state.stage != "finished":
            if k.state.stage == "acting":
                _, reservation = request_for(k.observe(k.turn.actor), limits)
                totals.append(reservation)
            step(k, RulePolicy())
    cost = sum(totals) * limits.price_per_million / 1000000 if limits.price_per_million else None
    cost_fits = limits.max_cost is None or cost <= limits.max_cost
    return {"mode": "offline_budget_preview", "provider_calls": 0,
            "reference_decisions": len(totals), "reference_token_reservations": sum(totals),
            "reference_estimated_cost_bound": cost, "largest_primary_reservation": max(totals), "configured_calls": limits.calls,
            "configured_tokens": limits.tokens,
            "reference_primary_attempts_fit": len(totals) <= limits.calls and sum(totals) <= limits.tokens and cost_fits}
