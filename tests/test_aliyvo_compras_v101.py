from pathlib import Path
import os
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path(os.environ.get("ALIYVO_TEST_APP_DIR", ROOT / "work" / "buyer_v1" / "_app"))
SOURCE = APP_DIR / "main.py"


class AliyvoComprasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")

    def test_separate_product_and_storage(self):
        self.assertIn('ALIYVO_VERSION = "1.0.1"', self.source)
        self.assertIn('ALIYVO_EDITION = "COMPRAS"', self.source)
        self.assertIn('/ "ALIYVO_COMPRAS"', self.source)
        self.assertIn('self.setWindowTitle("ALIYVO COMPRAS")', self.source)

    def test_buyer_portals(self):
        self.assertIn('PURCHASE_PORTAL_URL = "https://somaforce.com.br/pedewilliam/"', self.source)
        self.assertIn('ASANA_PORTAL_URL = "https://app.asana.com/"', self.source)
        self.assertIn('class AsanaPortalWindow', self.source)
        self.assertIn('self.purchase_toggle=QPushButton("🛒  Pedidos de compra")', self.source)

    def test_sales_only_tools_removed_from_navigation(self):
        nav = self.source.split("# ========== CORPO ==========", 1)[0]
        self.assertNotIn("nav_lay.addWidget(self.plate_toggle)", nav)
        self.assertNotIn("nav_lay.addWidget(self.radar_toggle)", nav)
        self.assertNotIn("nav_lay.addWidget(self.calls_ai_toggle)", nav)
        self.assertIn('self.reminder_toggle=QPushButton("📅  Agenda de compras")', nav)


if __name__ == "__main__":
    unittest.main()

