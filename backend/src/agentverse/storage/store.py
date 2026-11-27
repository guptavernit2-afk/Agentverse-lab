"""Verified event streams, transactional compare-and-swap and independent forks."""
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from pydantic import TypeAdapter

from agentverse.domain.model import Event
from agentverse.experiments.town import TownScenario
from agentverse.simulation.kernel import Kernel, TurnConflict
from .schema import migrate

EVENT = TypeAdapter(Event)
SCHEMA = 1


class IntegrityError(ValueError):
    pass


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(text: str) -> str:
    return sha256(text.encode()).hexdigest()


def chain_hash(previous: str, seq: int, command: str, payload: str) -> str:
    return digest(canonical([SCHEMA, previous, seq, command, payload]))


class Store:
    def __init__(self, path: Path):
        self.path = path
        with self.transaction(write=True) as db:
            migrate(db)

    @contextmanager
    def transaction(self, *, write=False) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield db
            db.commit()
        finally:
            db.close()  # an unfinished transaction rolls back

    @staticmethod
    def _row(db, run):
        row = db.execute("SELECT * FROM runs WHERE id=?", (run,)).fetchone()
        if row is None:
            raise KeyError(run)
        return row

    def create(self, run: str, config: TownScenario, seed: int):
        kernel = Kernel(config, seed, run_id=run)
        with self.transaction(write=True) as db:
            value = kernel.state.canonical()
            initial = digest(value)
            db.execute("INSERT INTO runs VALUES (?,?,?,NULL,NULL,0,?,?)",
                       (run, config.model_dump_json(), seed, initial, initial))
            db.execute("INSERT INTO snapshots VALUES (?,0,?,?,?)", (run, SCHEMA, value, initial))
        return kernel

    def _load(self, db, run: str) -> Kernel:
        row = self._row(db, run)
        kernel = Kernel(TownScenario.model_validate_json(row["scenario"]), row["seed"], run_id=run)
        snapshots = {r["seq"]: r for r in db.execute("SELECT * FROM snapshots WHERE run=?", (run,))}
        chain = kernel.state.digest()

        def verify_checkpoint():
            w = kernel.state
            if w.stage in {"ready", "finished"}:
                snap = snapshots.pop(w.version, None)
                if (snap is None or snap["schema"] != SCHEMA or digest(snap["payload"]) != snap["digest"]
                    or w.canonical() != snap["payload"]):
                    raise IntegrityError("missing, corrupt or unsupported snapshot")

        verify_checkpoint()
        for e in db.execute("SELECT * FROM events WHERE run=? ORDER BY seq", (run,)):
            seq = kernel.state.version + 1
            if e["seq"] != seq or e["schema"] != SCHEMA:
                raise IntegrityError("missing, unordered or unsupported event")
            chain = chain_hash(chain, seq, e["command"], e["payload"])
            if e["chain"] != chain:
                raise IntegrityError("event integrity mismatch")
            try:
                event = EVENT.validate_json(e["payload"], strict=True)
                kernel.replay_event(event)
            except ValueError as exc:
                raise IntegrityError("invalid persisted event") from exc
            verify_checkpoint()
        if (snapshots or kernel.state.version != row["head"] or chain != row["head_hash"]
                or kernel.state.digest() != row["state_hash"]):
            raise IntegrityError("run head or checkpoint set mismatch")
        return kernel

    def load(self, run: str) -> Kernel:
        with self.transaction() as db:
            return self._load(db, run)

    def save(self, kernel: Kernel, expected: int, key: str, request: str) -> int:
        """Commit already computed events. Duplicate requests return their original version."""
        run = kernel.run_id
        request = canonical([expected, request])
        with self.transaction(write=True) as db:
            row = self._row(db, run)
            prior = db.execute("SELECT * FROM commands WHERE run=? AND key=?", (run, key)).fetchone()
            if prior:
                if request != prior["request"]:
                    raise TurnConflict("command key was reused")
                return prior["result"]
            if row["head"] != expected or kernel.world_at(expected).digest() != row["state_hash"]:
                raise TurnConflict("stale or mismatched run state")
            chain = row["head_hash"]
            for e in kernel.events[expected:]:
                raw = canonical(asdict(e))
                chain = chain_hash(chain, e.sequence, key, raw)
                db.execute("INSERT INTO events VALUES (?,?,?,?,?,?)", (run, e.sequence, SCHEMA, key, raw, chain))
                w = kernel.world_at(e.sequence)
                if w.stage in {"ready", "finished"}:
                    raw_world = w.canonical()
                    db.execute("INSERT INTO snapshots VALUES (?,?,?,?,?)",
                               (run, w.version, SCHEMA, raw_world, digest(raw_world)))
            head = kernel.state
            db.execute("UPDATE runs SET head=?,head_hash=?,state_hash=? WHERE id=?",
                       (head.version, chain, head.digest(), run))
            db.execute("INSERT INTO commands VALUES (?,?,?,?)", (run, key, request, head.version))
            return head.version

    def command_result(self, run: str, expected: int, key: str, request: str) -> int | None:
        with self.transaction() as db:
            row = db.execute("SELECT request,result FROM commands WHERE run=? AND key=?", (run, key)).fetchone()
            if row and row["request"] != canonical([expected, request]):
                raise TurnConflict("command key was reused")
            return row["result"] if row else None

    def checkpoints(self, run: str) -> list[dict]:
        with self.transaction() as db:
            self._load(db, run)
            return [dict(r) for r in db.execute("SELECT seq,digest FROM snapshots WHERE run=? ORDER BY seq", (run,))]

    def fork(self, parent: str, seq: int, children: tuple[str, ...]):
        with self.transaction(write=True) as db:
            self.fork_in(db, parent, seq, children)

    def fork_in(self, db, parent: str, seq: int, children: tuple[str, ...]):
        source = self._load(db, parent)
        w = source.world_at(seq)
        if w.stage not in {"ready", "finished"}:
            raise TurnConflict("fork requires settled checkpoint")
        snap = w.digest()
        prior = db.execute("SELECT chain FROM events WHERE run=? AND seq=?", (parent, seq)).fetchone()
        for child in children:
            db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?)",
                       (child, w.scenario.model_dump_json(), w.seed, parent, seq, seq, prior[0] if prior else snap, snap))
            db.execute("INSERT INTO events SELECT ?,seq,schema,command,payload,chain FROM events WHERE run=? AND seq<=?",
                       (child, parent, seq))
            db.execute("INSERT INTO snapshots SELECT ?,seq,schema,payload,digest FROM snapshots WHERE run=? AND seq<=?",
                       (child, parent, seq))
