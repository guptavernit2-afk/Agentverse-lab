import pytest


def advance(kernel, actor, round_number):
    while kernel.state.stage != "finished":
        if kernel.state.stage == "ready":
            kernel.start_round()
        elif kernel.state.stage == "settlement":
            kernel.settle_round()
        elif kernel.turn.actor == actor and kernel.turn.round == round_number:
            return
        else:
            kernel.submit(kernel.turn, {"type": "WAIT"})
    pytest.fail("requested turn was never reached")
