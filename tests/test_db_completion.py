import os
import sqlite3
import tempfile
import unittest

from db import DDL, INDEXES, OntinuityDB, now_utc


class CompletionPersistenceMuseum(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.db = OntinuityDB(self.path)
        self.db.init()

    def tearDown(self):
        self.db.close()
        os.unlink(self.path)

    def test_fresh_schema_defaults_to_in_progress_and_has_end_reason(self):
        columns = {
            row[1]: row for row in self.db.connect().execute(
                "PRAGMA table_info(sessions)"
            )
        }
        self.assertEqual(columns["status"][4], "'in_progress'")
        self.assertIn("end_reason", columns)

    def test_writer_never_defaults_to_complete(self):
        user_id = self.db.insert_user("Museum")
        project_id = self.db.insert_project(user_id, "B3")
        branch_id = self.db.insert_branch(project_id, user_id, "main")
        self.db.insert_session({
            "session_id": "missing-status",
            "user_id": user_id,
            "project_id": project_id,
            "branch_id": branch_id,
            "created_at": now_utc(),
        })
        row = self.db.connect().execute(
            "SELECT status, end_reason FROM sessions WHERE session_id = ?",
            ("missing-status",),
        ).fetchone()
        self.assertEqual(row["status"], "in_progress")
        self.assertIsNone(row["end_reason"])

    def test_database_rejects_uncertified_complete(self):
        user_id = self.db.insert_user("Museum")
        project_id = self.db.insert_project(user_id, "B3")
        branch_id = self.db.insert_branch(project_id, user_id, "main")
        specimen = {
            "session_id": "asserted-complete",
            "user_id": user_id,
            "project_id": project_id,
            "branch_id": branch_id,
            "status": "complete",
            "created_at": now_utc(),
        }
        with self.assertRaisesRegex(
                sqlite3.IntegrityError, "complete requires certified_close"):
            self.db.insert_session(specimen)

        specimen["end_reason"] = "certified_close"
        self.db.insert_session(specimen)
        row = self.db.connect().execute(
            "SELECT status, end_reason FROM sessions WHERE session_id = ?",
            ("asserted-complete",),
        ).fetchone()
        self.assertEqual(tuple(row), ("complete", "certified_close"))

    def test_existing_database_receives_additive_end_reason_column(self):
        self.db.close()
        os.unlink(self.path)
        connection = sqlite3.connect(self.path)
        legacy_ddl = DDL.replace(
            "status                  TEXT NOT NULL DEFAULT 'in_progress',",
            "status                  TEXT NOT NULL DEFAULT 'complete',",
        ).replace("    end_reason              TEXT,\n", "")
        connection.executescript(legacy_ddl)
        connection.executescript(INDEXES)
        connection.commit()
        connection.close()

        migrated = OntinuityDB(self.path)
        migrated.init()
        columns = {
            row[1] for row in migrated.connect().execute(
                "PRAGMA table_info(sessions)"
            )
        }
        self.assertIn("end_reason", columns)
        migrated.close()


if __name__ == "__main__":
    unittest.main()
