from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from sc.trust_db import TrustDB


class TrustDBLeaseTests(unittest.TestCase):
    def test_upgrades_temporary_write_lease_to_permanent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = TrustDB(Path(tmpdir) / "trust.db")
            repo = "/tmp/repo"
            file_path = "demo/feature.py"

            db.add_leases(repo, [file_path], ttl_hours=24, source="temp")
            db.add_permanent_leases(repo, [file_path], source="perm")

            leases = [lease for lease in db.list_active_leases(repo) if lease.lease_type == "write"]
            self.assertEqual(len(leases), 1)
            self.assertEqual(leases[0].file_path, file_path)
            self.assertIsNone(leases[0].expires_at)

    def test_temporary_write_lease_never_overwrites_permanent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = TrustDB(Path(tmpdir) / "trust.db")
            repo = "/tmp/repo"
            file_path = "demo/feature.py"

            db.add_permanent_leases(repo, [file_path], source="perm")
            db.add_leases(repo, [file_path], ttl_hours=24, source="temp")

            leases = [lease for lease in db.list_active_leases(repo) if lease.lease_type == "write"]
            self.assertEqual(len(leases), 1)
            self.assertIsNone(leases[0].expires_at)

    def test_permanent_read_lease_overwrites_temporary_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = TrustDB(Path(tmpdir) / "trust.db")
            repo = "/tmp/repo"
            file_path = "demo/feature.py"

            now = 100
            with db._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO read_leases (repo_root, file_path, created_at, expires_at, source)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (repo, file_path, now, now + 3600, "temp"),
                )
            db.add_permanent_read_leases(repo, [file_path], source="perm")

            leases = [lease for lease in db.list_active_leases(repo) if lease.lease_type == "read"]
            self.assertEqual(len(leases), 1)
            self.assertIsNone(leases[0].expires_at)

    def test_migration_dedupes_existing_duplicate_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "trust.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                """
                CREATE TABLE leases (
                    id INTEGER PRIMARY KEY,
                    repo_root TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER,
                    source TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE read_leases (
                    id INTEGER PRIMARY KEY,
                    repo_root TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER,
                    source TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "INSERT INTO leases (repo_root, file_path, created_at, expires_at, source) VALUES (?, ?, ?, ?, ?)",
                ("/tmp/repo", "demo/feature.py", 100, 200, "temp"),
            )
            conn.execute(
                "INSERT INTO leases (repo_root, file_path, created_at, expires_at, source) VALUES (?, ?, ?, NULL, ?)",
                ("/tmp/repo", "demo/feature.py", 101, "perm"),
            )
            conn.commit()
            conn.close()

            db = TrustDB(db_path)
            leases = [lease for lease in db.list_active_leases("/tmp/repo") if lease.lease_type == "write"]
            self.assertEqual(len(leases), 1)
            self.assertIsNone(leases[0].expires_at)


if __name__ == "__main__":
    unittest.main()
