import os
import unittest
from pathlib import Path


class UpdateChannelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = (Path(os.environ["ALIYVO_TEST_APP_DIR"]) / "main.py").read_text(encoding="utf-8")

    def test_sales_has_own_channel(self):
        self.assertIn('ALIYVO_VERSION = "0.23.51"', self.main)
        self.assertIn("channels/vendas.json", self.main)
        self.assertNotIn("releases/latest", self.main)
        self.assertNotIn("channels/compras.json", self.main)

    def test_notice_uses_configured_channel(self):
        self.assertIn('globals().get("ALIYVO_OFFICIAL_UPDATE_CHANNEL")', self.main)
        self.assertIn('d.get("version") or d.get("tag_name")', self.main)


if __name__ == "__main__":
    unittest.main()
