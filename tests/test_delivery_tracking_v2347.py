import ast
import os
import unittest
from pathlib import Path


APP_DIR = Path(os.environ["ALIYVO_TEST_APP_DIR"])
MAIN = APP_DIR / "main.py"


class DeliveryTrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MAIN.read_text(encoding="utf-8")
        ast.parse(cls.source)

    def test_version_and_internal_url(self):
        self.assertIn('ALIYVO_VERSION = "0.23.47"', self.source)
        self.assertIn(
            'DELIVERY_TRACKING_URL = "https://somaforce.com.br/entregas/painel"',
            self.source,
        )

    def test_top_button_was_replaced(self):
        nav = self.source[
            self.source.index("class MainWindow"):
            self.source.index("# ========== CORPO ==========")
        ]
        self.assertIn('QPushButton("🏍️  Rastrear moto")', nav)
        self.assertNotIn('QPushButton("🔎  Buscar peça")', nav)
        self.assertIn(
            "self.radar_toggle.clicked.connect(self._open_delivery_tracking)", nav
        )

    def test_tracking_uses_internal_persistent_window(self):
        self.assertIn("class DeliveryTrackingWindow(PurchasePortalWindow)", self.source)
        self.assertIn("PROFILE_DIR = DELIVERY_TRACKING_PROFILE_DIR", self.source)
        self.assertIn("self._tracking_window.open_portal()", self.source)
        self.assertIn("webbrowser.open(DELIVERY_TRACKING_URL)", self.source)

    def test_existing_parts_search_and_purchase_portal_are_preserved(self):
        self.assertIn("def _parts_search_dialog(self):", self.source)
        self.assertIn("class PurchasePortalWindow(QMainWindow):", self.source)
        self.assertIn("self.purchase_toggle.clicked.connect(self._open_purchase_portal)", self.source)


if __name__ == "__main__":
    unittest.main()
