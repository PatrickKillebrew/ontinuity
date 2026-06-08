#!/usr/bin/env python3
"""EXPERIMENT_MODE modal-touch durability migration.
Adds modal_touched to behavioral_observations and backfills block-1 touched
sessions from the committed manifest (commit 43dd5f91). Idempotent. Run on the
VPS against the live workspace DB, then restart the workspace endpoint."""
import sqlite3, sys
db = sqlite3.connect(sys.argv[1] if len(sys.argv) > 1 else "ontinuity.db")
try:
    db.execute("ALTER TABLE behavioral_observations ADD COLUMN modal_touched INTEGER")
    print("added modal_touched")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e).lower():
        print("modal_touched already present")
    else:
        raise
# default 0 for all experiment rows (computed_signal populated); NULL stays for legacy rows
db.execute("UPDATE behavioral_observations SET modal_touched = 0 "
           "WHERE computed_signal IS NOT NULL AND modal_touched IS NULL")
# backfill block-1 touched sessions, session granularity (cycle index not in block-1 log)
for sid in ("2026-06-08_02-35-05_farm",
            "2026-06-08_02-38-19_farm",
            "2026-06-08_02-44-48_farm"):
    db.execute("UPDATE behavioral_observations SET modal_touched = 1 WHERE session_id = ?", (sid,))
db.commit()
r = db.execute("SELECT COUNT(*), COALESCE(SUM(modal_touched),0) "
               "FROM behavioral_observations WHERE computed_signal IS NOT NULL").fetchone()
print(f"experiment rows: {r[0]}, modal_touched=1: {r[1]} (expect 9)")
