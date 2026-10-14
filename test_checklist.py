import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "checklist.py"


def run_cmd(args, env):
    cmd = [sys.executable, str(SCRIPT)] + args
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)


class ChecklistCLITest(unittest.TestCase):
    def setUp(self):
        # Create isolated HOME so the app uses a temp data file location
        self.tmpdir = tempfile.TemporaryDirectory()
        self.env = os.environ.copy()
        self.env["HOME"] = self.tmpdir.name

    def tearDown(self):
        self.tmpdir.cleanup()

    def data_path(self):
        return Path(self.tmpdir.name) / ".local" / "share" / "hackathon-checklist" / "tasks.json"

    def test_crud_and_persistence_and_stable_ids(self):
        # Add two tasks
        r = run_cmd(["add", "First task"], self.env)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("1", r.stdout.strip())

        r = run_cmd(["add", "Second task"], self.env)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("2", r.stdout.strip())

        # List should show both
        r = run_cmd(["list"], self.env)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        out = r.stdout.strip().splitlines()
        self.assertTrue(any("1. [ " in line and "First task" in line for line in out))
        self.assertTrue(any("2. [ " in line and "Second task" in line for line in out))

        # Mark first done
        r = run_cmd(["done", "1"], self.env)
        self.assertEqual(r.returncode, 0, msg=r.stderr)

        r = run_cmd(["list"], self.env)
        out = r.stdout.strip().splitlines()
        self.assertTrue(any("1. [x] First task" in line for line in out))

        # Remove first
        r = run_cmd(["remove", "1"], self.env)
        self.assertEqual(r.returncode, 0, msg=r.stderr)

        # Add third and ensure ID is stable (should be 3)
        r = run_cmd(["add", "Third task"], self.env)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("3", r.stdout.strip())

        r = run_cmd(["list"], self.env)
        out = r.stdout.strip().splitlines()
        # 1 should be gone
        self.assertFalse(any(line.startswith("1.") for line in out))
        self.assertTrue(any(line.startswith("2.") for line in out))
        self.assertTrue(any(line.startswith("3.") for line in out))

        # Confirm data file contains expected structure
        data_file = self.data_path()
        self.assertTrue(data_file.exists())
        with data_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("next_id", data)
        self.assertIn("tasks", data)
        ids = [t["id"] for t in data["tasks"]]
        self.assertIn(2, ids)
        self.assertIn(3, ids)
        self.assertNotIn(1, ids)

    def test_invalid_input_and_missing_id(self):
        # Empty add should fail
        r = run_cmd(["add", ""], self.env)
        self.assertNotEqual(r.returncode, 0)
        # done with missing ID
        r = run_cmd(["done"], self.env)
        self.assertNotEqual(r.returncode, 0)
        # remove with missing ID
        r = run_cmd(["remove"], self.env)
        self.assertNotEqual(r.returncode, 0)
        # done with non-existent ID
        r = run_cmd(["done", "9999"], self.env)
        self.assertNotEqual(r.returncode, 0)

    def test_malformed_json_is_preserved_and_not_overwritten(self):
        data_file = self.data_path()
        data_file.parent.mkdir(parents=True, exist_ok=True)
        # Write malformed content
        with data_file.open("w", encoding="utf-8") as f:
            f.write("not a json")
        # Attempt to add should fail and preserve file
        r = run_cmd(["add", "Should not be added"], self.env)
        self.assertNotEqual(r.returncode, 0)
        # File should still contain the original malformed content
        with data_file.open("r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, "not a json")

    def test_unexpected_arguments_are_rejected(self):
        for args in (["list", "extra"], ["done", "1", "extra"],
                     ["remove", "1", "extra"], ["add", "--unknown"],
                     ["done", "abc"], ["unknown"]):
            with self.subTest(args=args):
                self.assertNotEqual(run_cmd(args, self.env).returncode, 0)

    def test_invalid_schema_is_preserved(self):
        path = self.data_path()
        path.parent.mkdir(parents=True)
        for content in (
            {"next_id": True, "tasks": []},
            {"next_id": 1, "tasks": [{"id": 1, "text": "task", "done": False}]},
            {"next_id": 2, "tasks": [{"id": True, "text": "task", "done": False}]},
        ):
            original = json.dumps(content)
            path.write_text(original)
            with self.subTest(content=content):
                self.assertNotEqual(run_cmd(["add", "new"], self.env).returncode, 0)
                self.assertEqual(path.read_text(), original)


if __name__ == "__main__":
    unittest.main()
