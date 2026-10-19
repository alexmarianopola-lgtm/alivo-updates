import importlib
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


APP_DIR = Path(os.environ["ALIYVO_TEST_APP_DIR"])
sys.path.insert(0, str(APP_DIR))
quota = importlib.import_module("aliyvo_call_quota")


class CallQuotaTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "cota.json"
        self.now = datetime(2026, 10, 19, 12, 0)

    def tearDown(self):
        self.folder.cleanup()

    def test_retry_of_same_call_is_idempotent(self):
        first = quota.reserve(self.path, 180, operation_id="call-001", now=self.now)
        retry = quota.reserve(self.path, 180, operation_id="call-001", now=self.now)
        self.assertEqual(first["calls"], 1)
        self.assertEqual(retry["calls"], 1)
        self.assertEqual(retry["seconds"], 180)
        self.assertTrue(retry["already_reserved"])

    def test_limit_has_specific_non_api_exception_and_keeps_ledger(self):
        self.path.write_text(json.dumps({
            "month": "2026-10", "calls": 30, "seconds": 900,
            "operations": [f"call-{i}" for i in range(30)],
        }), encoding="utf-8")
        with self.assertRaises(quota.QuotaExceeded):
            quota.reserve(self.path, 30, operation_id="new-call", now=self.now)
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(saved["calls"], 30)
        self.assertNotIn("new-call", saved["operations"])

    def test_month_change_resets_local_allowance(self):
        self.path.write_text(json.dumps({
            "month": "2026-09", "calls": 30, "seconds": 3600,
            "operations": ["old"],
        }), encoding="utf-8")
        data = quota.reserve(self.path, 60, operation_id="october", now=self.now)
        self.assertEqual(data["calls"], 1)
        self.assertEqual(data["seconds"], 60)
        self.assertEqual(data["operations"], ["october"])


if __name__ == "__main__":
    unittest.main()
