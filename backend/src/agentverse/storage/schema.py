"""Numbered, transactional SQLite migrations. Reject unknown future schemas."""
import sqlite3

MIGRATIONS = ("""
CREATE TABLE runs (
    id TEXT PRIMARY KEY, scenario TEXT NOT NULL, seed INTEGER NOT NULL,
    parent TEXT REFERENCES runs(id), fork_version INTEGER,
    head INTEGER NOT NULL, head_hash TEXT NOT NULL, state_hash TEXT NOT NULL);
CREATE TABLE events (
    run TEXT NOT NULL REFERENCES runs(id), seq INTEGER NOT NULL, schema INTEGER NOT NULL,
    command TEXT NOT NULL, payload TEXT NOT NULL, chain TEXT NOT NULL, PRIMARY KEY (run, seq));
CREATE TABLE snapshots (
    run TEXT NOT NULL REFERENCES runs(id), seq INTEGER NOT NULL, schema INTEGER NOT NULL,
    payload TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY (run, seq));
CREATE TABLE commands (
    run TEXT NOT NULL REFERENCES runs(id), key TEXT NOT NULL, request TEXT NOT NULL,
    result INTEGER NOT NULL, PRIMARY KEY (run, key));
""",)


def migrate(db: sqlite3.Connection) -> None:
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version > len(MIGRATIONS):
        raise ValueError("unsupported database schema")
    for index in range(version, len(MIGRATIONS)):
        for statement in MIGRATIONS[index].split(";"):
            if statement.strip():
                db.execute(statement)
        db.execute(f"PRAGMA user_version={index + 1}")
