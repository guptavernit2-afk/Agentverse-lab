"""Call the policy outside the kernel lock, then commit against the observed turn."""
from agentverse.agents.policy import BudgetExhausted, DecisionError, DecisionPolicy
from agentverse.domain.model import Event
from .kernel import Kernel


def step(kernel: Kernel, policy: DecisionPolicy) -> Event:
    if kernel.state.stage == "ready":
        return kernel.start_round()
    if kernel.state.stage == "settlement":
        return kernel.settle_round()
    turn = kernel.turn
    observation = kernel.observe(turn.actor, version=turn.version)
    try:
        decision = policy.decide(observation)
    except DecisionError as failure:
        return kernel.reject_turn(turn, str(failure))
    note = decision.note.model_dump() if decision.note else None
    return kernel.submit(turn, decision.action.model_dump(), note=note)


def run(kernel: Kernel, policy: DecisionPolicy) -> str:
    try:
        while kernel.state.stage != "finished":
            step(kernel, policy)
    except BudgetExhausted:
        return "incomplete_budget"
    return "complete"
