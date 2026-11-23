#!/usr/bin/env python3
"""I apply my SQL files in name order. I can run this more than once."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import load_environment
from app.core import connect


def statements(sql):
    chunks = []
    buffer = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            text = "\n".join(buffer).strip()
            if text:
                chunks.append(text)
            buffer = []
    leftover = "\n".join(buffer).strip()
    if leftover:
        chunks.append(leftover)
    return chunks


def apply_migrations():
    load_environment()
    folder = ROOT / "migrations"
    files = sorted(
        path for path in folder.glob("*.sql") if not path.name.startswith(".")
    )
    if not files:
        raise SystemExit(f"No SQL files in {folder}")

    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.commit()
        applied = {
            row["version"]
            for row in conn.execute("SELECT version FROM schema_migrations")
        }
        for path in files:
            if path.name in applied:
                print(f"skip {path.name}")
                continue
            with conn.transaction():
                for statement in statements(path.read_text()):
                    conn.execute(statement)
                conn.execute(
                    """
                    INSERT INTO schema_migrations (version)
                    VALUES (%s)
                    ON CONFLICT (version) DO NOTHING
                    """,
                    (path.name,),
                )
            print(f"applied {path.name}")


if __name__ == "__main__":
    apply_migrations()
