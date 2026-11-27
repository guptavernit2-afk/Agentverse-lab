from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

from agentverse.agents.policy import RulePolicy
from agentverse.simulation.kernel import TurnConflict
from agentverse.simulation.runner import run, step
from agentverse.storage.store import IntegrityError, Store


@pytest.fixture
def saved(town, tmp_path):
    db = Store(tmp_path / "world.sqlite")
    k = db.create("parent", town, 0)
    k.publish_harvest_claim()
    k.issue_harvest_record()
    db.save(k, 0, "setup", "town")
    return db, k


def test_replay_every_checkpoint_and_observation(saved, monkeypatch):
    db, k = saved
    assert run(k, RulePolicy()) == "complete"
    db.save(k, 2, "run", "finish")
    monkeypatch.setattr(RulePolicy, "decide", lambda *_: pytest.fail("policy called during replay"))
    recovered = Store(db.path).load("parent")
    assert recovered.events == k.events
    for seq in range(k.state.version + 1):
        assert recovered.world_at(seq).digest() == k.world_at(seq).digest()
    for snap in db.checkpoints("parent"):
        assert snap["digest"] == k.world_at(snap["seq"]).digest()
    assert recovered.observe("A3", version=3) == k.observe("A3", version=3)


def test_restart_and_lost_response(saved):
    db, k = saved
    k.start_round()
    k.submit(k.turn, {"type": "CREATE_COMMITMENT", "beneficiary_id": "A2", "quantity": 1, "due_round": 2},
             note={"summary": "I promised food"})
    assert db.save(k, 2, "one", "promise") == 4
    restarted = Store(db.path).load("parent")
    assert restarted.turn == k.turn and restarted.state == k.state
    assert db.command_result("parent", 2, "one", "promise") == 4
    assert db.save(k, 2, "one", "promise") == 4
    with pytest.raises(TurnConflict):
        db.save(k, 2, "one", "different")
    with pytest.raises(TurnConflict):
        db.save(k, 2, "other", "promise")
    assert len(db.load("parent").state.social.commitments) == 1


def test_rollback_between_event_and_snapshot(saved):
    db, k = saved
    before = k.state
    run(k, RulePolicy())
    with db.transaction(write=True) as sql:
        sql.execute("CREATE TRIGGER fail BEFORE INSERT ON snapshots BEGIN SELECT RAISE(ABORT, 'power loss'); END")
    with pytest.raises(sqlite3.IntegrityError, match="power loss"):
        db.save(k, before.version, "run", "finish")
    assert Store(db.path).load("parent").state == before
    assert db.command_result("parent", before.version, "run", "finish") is None


@pytest.mark.parametrize("damage", [
    "UPDATE snapshots SET digest='x' WHERE seq=2", "UPDATE snapshots SET payload='{}' WHERE seq=2",
    "UPDATE snapshots SET schema=9 WHERE seq=0", "UPDATE events SET seq=5 WHERE seq=1",
    "DELETE FROM events WHERE seq=2", "UPDATE events SET schema=2 WHERE seq=2",
    "UPDATE events SET payload='{}' WHERE seq=1", "DELETE FROM snapshots WHERE seq=0",
    "UPDATE runs SET head=0", "UPDATE runs SET head_hash='bad'"
])
def test_corruption_blocks_recovery_and_fork(saved, damage):
    db, _ = saved
    with db.transaction(write=True) as sql:
        sql.execute(damage)
    with pytest.raises(IntegrityError):
        db.load("parent")
    with pytest.raises(IntegrityError):
        db.fork("parent", 2, ("bad",))


def test_fork_isolation_and_atomic_batch(saved):
    db, parent = saved
    db.fork("parent", 2, ("a", "b"))
    a, b = db.load("a"), db.load("b")
    assert parent.state.digest() == a.state.digest() == b.state.digest()
    a.grant_evidence("evidence-harvest", grantee="A1")
    a.start_round()
    a.submit(a.turn, {"type": "CREATE_COMMITMENT", "beneficiary_id": "A2", "quantity": 1, "due_round": 2},
             note={"summary": "private decision", "evidence_ids": ["evidence-harvest"]})
    db.save(a, 2, "commit", "grant and promise")
    assert a.state.social.grants and a.state.social.commitments and a.state.social.notes
    for name in ("parent", "b"):
        other = db.load(name)
        assert other.state == parent.state and other.events == parent.events
        assert "private decision" not in other.observe("A1").policy_context
    with pytest.raises(TurnConflict):
        db.fork("a", a.state.version, ("bad",))
    with pytest.raises(sqlite3.IntegrityError):
        db.fork("parent", 2, ("new", "a"))
    with pytest.raises(KeyError):
        db.load("new")


@pytest.mark.parametrize("same_key", [True, False])
def test_concurrent_retries(saved, same_key):
    db, k = saved
    k.start_round()
    db.save(k, 2, "start", "start")
    def apply(i):
        candidate = db.load("parent")
        if candidate.state.version == 3:
            candidate.submit(candidate.turn, {"type": "GIVE_FOOD", "recipient_id": "A2", "quantity": 1})
        try:
            return db.save(candidate, 3, "give" if same_key else str(i), "gift")
        except TurnConflict:
            return None
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(apply, range(2)))
    state = db.load("parent")
    assert 4 in results and state.state.version == 4 and state.events[-1].kind == "GIVE_FOOD"


def test_inflight_response_lost_on_restart(saved):
    db, k = saved
    k.start_round()
    db.save(k, 2, "start", "start")
    turn = k.turn
    decision = RulePolicy().decide(k.observe(turn.actor))
    # Process dies after deciding and before the event transaction.
    retry = Store(db.path).load("parent")
    assert retry.turn == turn
    step(retry, RulePolicy())
    db.save(retry, turn.version, "take-turn", "decide")
    k.submit(turn, decision.action.model_dump())
    assert db.save(k, turn.version, "take-turn", "decide") == 4
    assert db.load("parent").events == retry.events


def test_future_db_version(saved):
    db, _ = saved
    with db.transaction(write=True) as sql:
        sql.execute("PRAGMA user_version=99")
    with pytest.raises(ValueError, match="unsupported"):
        Store(db.path)
