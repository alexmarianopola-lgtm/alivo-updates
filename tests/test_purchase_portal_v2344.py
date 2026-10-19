import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "source" / "v0.23.44" / "main.patch"


class PurchasePortalV2344Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = PATCH.read_text(encoding="utf-8")

    def test_exact_portal_url_is_used(self):
        self.assertIn(
            'PURCHASE_PORTAL_URL = "https://somaforce.com.br/pedewilliam/"',
            self.source,
        )

    def test_purchase_profile_is_separate_and_persistent(self):
        self.assertIn('PURCHASE_PROFILE_DIR = ALIYVO_USER_DIR / "pedidos_compras_profile"', self.source)
        self.assertIn("user_data_folder=str(PURCHASE_PROFILE_DIR)", self.source)
        self.assertIn("no_local_storage=False", self.source)

    def test_portal_opens_large_with_browser_fallback(self):
        self.assertIn("class PurchasePortalWindow(QMainWindow):", self.source)
        self.assertIn("self.showMaximized()", self.source)
        self.assertIn("webbrowser.open(self.URL)", self.source)
        self.assertIn("webbrowser.open(PURCHASE_PORTAL_URL)", self.source)

    def test_top_and_quick_buttons_are_connected(self):
        self.assertIn('self.purchase_toggle=QPushButton("🛒  Pedido ao comprador")', self.source)
        self.assertIn('self.quick_purchase=QPushButton("🛒  Pedido ao comprador")', self.source)
        self.assertIn("self.purchase_toggle.clicked.connect(self._open_purchase_portal)", self.source)
        self.assertIn("self.quick_purchase.clicked.connect(self._open_purchase_portal)", self.source)

    def test_integration_does_not_call_ai(self):
        portal = self.source.split("class PurchasePortalWindow", 1)[1].split("class MainWindow", 1)[0]
        self.assertNotIn("OpenAI", portal)
        self.assertNotIn("api_key", portal.lower())
        self.assertNotIn("requests.", portal)
        self.assertIn("sem consumo de API", portal)

    def test_close_keeps_portal_ready(self):
        self.assertIn("def closeEvent(self,event):", self.source)
        self.assertIn("event.ignore()", self.source)
        self.assertIn("self.hide()", self.source)


if __name__ == "__main__":
    unittest.main()
