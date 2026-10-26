import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


def load_quota():
    path = Path(os.environ["ALIYVO_TEST_APP_DIR"]) / "aliyvo_call_quota.py"
    spec = importlib.util.spec_from_file_location("quota_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CallQuotaTests(unittest.TestCase):
    def setUp(self):
        self.quota = load_quota()
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "quota.json"

    def tearDown(self):
        self.temp.cleanup()

    def write_usage(self, calls, seconds):
        self.path.write_text(json.dumps({
            "month": self.quota._month(), "calls": calls,
            "seconds": seconds, "operations": []
        }), encoding="utf-8")

    def test_call_started_below_limit_is_allowed_to_finish(self):
        self.write_usage(16, 3599)
        result = self.quota.reserve(self.path, 600, operation_id="call-17")
        self.assertEqual(result["calls"], 17)
        self.assertEqual(result["seconds"], 4199)

    def test_next_call_is_blocked_after_limit(self):
        self.write_usage(17, 4199)
        with self.assertRaises(self.quota.QuotaExceeded):
            self.quota.reserve(self.path, 60, operation_id="call-18")

    def test_retry_does_not_consume_twice(self):
        self.write_usage(16, 3599)
        first = self.quota.reserve(self.path, 600, operation_id="same-call")
        second = self.quota.reserve(self.path, 600, operation_id="same-call")
        self.assertEqual(first["calls"], second["calls"])
        self.assertTrue(second["already_reserved"])


if __name__ == "__main__":
    unittest.main()
