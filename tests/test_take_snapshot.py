"""Logger regression tests; tmutil is mocked, so no snapshots are created."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "take-snapshot"
LIMIT = 1024 * 1024


class SnapshotLoggingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        home = Path(self.temp.name)
        mock_bin = home / "bin"
        mock_bin.mkdir()
        tmutil = mock_bin / "tmutil"
        tmutil.write_text(
            '#!/bin/bash\n'
            '[[ "$*" == localsnapshot ]] || exit 99\n'
            'printf "first line\\nsecond line\\n"\n'
            'printf "diagnostic\\n" >&2\n'
            'exit "${MOCK_EXIT_CODE:-0}"\n'
        )
        tmutil.chmod(0o755)
        self.env = {**os.environ, "HOME": str(home),
                    "PATH": f"{mock_bin}:/usr/bin:/bin:/usr/sbin:/sbin",
                    "MOCK_EXIT_CODE": "0"}
        self.log = home / "Library/Logs/mbp-backups/snapshots.log"
        self.archive = self.log.with_name("snapshots.log.1")

    def seed(self, data):
        self.log.parent.mkdir(parents=True, exist_ok=True)
        self.log.write_bytes(data)

    def run_snapshot(self, fail=False):
        result = subprocess.run(
            ["/bin/bash", str(SCRIPT)],
            env={**self.env, "MOCK_EXIT_CODE": "1" if fail else "0"},
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1 if fail else 0, result.stderr)
        return self.log.read_text()

    def test_initial_success_flattens_output_into_one_line(self):
        text = self.run_snapshot()
        self.assertRegex(text, r"^\d{4}-\d{2}-\d{2} .* OK   first line; second line; diagnostic\n$")
        self.assertFalse(self.archive.exists())

    def test_appends_without_replacing_or_replaying_history(self):
        old = b"old heartbeat\n" * 500
        self.seed(old)
        inode = self.log.stat().st_ino
        text = self.run_snapshot()
        self.assertEqual(self.log.stat().st_ino, inode)
        self.assertTrue(text.startswith(old.decode()))
        self.assertEqual(len(text.splitlines()), 501)
        self.assertFalse(self.archive.exists())
        self.run_snapshot()
        self.assertEqual(self.log.stat().st_ino, inode)
        self.assertEqual(len(self.log.read_text().splitlines()), 502)

    def test_failure_appends_and_returns_nonzero(self):
        self.seed(b"old heartbeat\n")
        inode = self.log.stat().st_ino
        text = self.run_snapshot(fail=True)
        self.assertEqual(self.log.stat().st_ino, inode)
        self.assertTrue(text.startswith("old heartbeat\n"))
        self.assertIn(" FAIL first line; second line; diagnostic\n", text)

    def test_no_rotation_below_limit(self):
        self.seed(b"x" * (LIMIT - 1))
        inode = self.log.stat().st_ino
        self.run_snapshot()
        self.assertEqual(self.log.stat().st_ino, inode)
        self.assertFalse(self.archive.exists())

    def test_rotation_preserves_old_file_and_replaces_single_archive(self):
        for fail in (False, True):
            with self.subTest(fail=fail):
                old = b"x" * LIMIT
                self.seed(old)
                inode = self.log.stat().st_ino
                self.archive.write_text("previous archive")
                text = self.run_snapshot(fail=fail)
                self.assertEqual(self.archive.read_bytes(), old)
                self.assertEqual(self.archive.stat().st_ino, inode)
                self.assertNotEqual(self.log.stat().st_ino, inode)
                self.assertEqual(len(text.splitlines()), 1)
                self.assertIn(" FAIL " if fail else " OK ", text)
                self.assertEqual(sorted(p.name for p in self.log.parent.iterdir()),
                                 ["snapshots.log", "snapshots.log.1"])


if __name__ == "__main__":
    unittest.main()
