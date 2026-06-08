#!/usr/bin/env python3
"""EXPERIMENT_MODE migration (deploy 32, certified protocol receipt #13).
Adds computed_signal, injected_signal, randomized_flag to behavioral_observations.
Idempotent: duplicate-column errors are the already-migrated case. Run on the
VPS against the live workspace database, then restart the workspace endpoint.
Usage: python3 migrate_experiment_mode.py /path/to/ontinuity.db"""
import sqlite3, sys

db_path = sys.argv[1] if len(sys.argv) > 1 else "ontinuity.db"
conn = sqlite3.connect(db_path)
for col in ("computed_signal", "injected_signal", "randomized_flag"):
    try:
        conn.execute(f"ALTER TABLE behavioral_observations ADD COLUMN {col} INTEGER")
        print(f"added {col}")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print(f"{col} already present — skipped")
        else:
            raise
conn.commit()
cols = [r[1] for r in conn.execute("PRAGMA table_info(behavioral_observations)")]
assert all(c in cols for c in ("computed_signal", "injected_signal", "randomized_flag"))
print("migration verified:", len(cols), "columns total")
