import importlib.util
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = [
    Path(os.environ["ALIYVO_TEST_APP_DIR"]) if os.environ.get("ALIYVO_TEST_APP_DIR") else None,
    ROOT / "work2344" / "base" / "_app",
    ROOT / "build" / "_app",
]
APP = next((path for path in CANDIDATES if path and (path / "aliyvo_freight.py").is_file()), None)
if APP is None:
    raise RuntimeError("Pasta do aplicativo para teste não encontrada")

spec = importlib.util.spec_from_file_location("aliyvo_freight_v2345", APP / "aliyvo_freight.py")
freight = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = freight
spec.loader.exec_module(freight)


class FreightPaymentV2345Tests(unittest.TestCase):
    def test_payment_ranges_keep_every_commercial_boundary(self):
        cases = [
            ("0", "30", ["30", "20/40"]),
            ("950", "35", ["35", "28/42"]),
            ("1.100", "37,50", ["25/50"]),
            ("1.200", "40", ["20/40/60", "35/45"]),
            ("1.300", "42", ["28/42/56", "28/56"]),
            ("1.400", "45", ["30/60", "30/45/60"]),
            ("1.800", "50", ["25/50/75", "30/50/70", "20/40/60/80"]),
            ("2.800", "55/56", ["28/56/84", "28/42/56/70/84", "30/55/80"]),
            ("3.000", "60", ["30/60/90", "20/40/60/80/100", "30/50/70/90", "25/45/65/90"]),
            ("4.000", "62,50", ["25/50/75/100"]),
            ("6.000", "67,50", ["30/45/60/75/90/105"]),
            ("8.000", "70", ["20/40/60/80/100/120", "28/56/84/112", "30/50/70/90/110"]),
        ]
        for value, average, options in cases:
            with self.subTest(value=value):
                terms = freight.payment_terms(value)
                self.assertTrue(terms["ok"])
                self.assertEqual(average, terms["average_days"])
                self.assertEqual(options, terms["options"])

    def test_paid_freight_message_has_fee_and_no_cutoff(self):
        quote = freight.quote_freight("Rio Grande - RS", "matriz_sao_miguel", "700")
        self.assertEqual("paid", quote["status"])
        self.assertEqual("65", str(quote["fee"]))
        text = freight.copy_message(quote, freight.payment_terms(quote["value"]))
        self.assertIn("Frete: R$ 65,00", text)
        self.assertIn("Opções de pagamento", text)
        self.assertIn("• 30 dias", text)
        self.assertIn("• 20/40 dias", text)
        self.assertNotIn("corte", text.lower())
        self.assertNotIn("faltam", text.lower())

    def test_free_freight_message_has_only_free_status_and_payment(self):
        quote = freight.quote_freight("Rio Grande - RS", "matriz_sao_miguel", "2.000")
        self.assertEqual("free", quote["status"])
        text = freight.copy_message(quote, freight.payment_terms(quote["value"]))
        self.assertIn("Frete grátis", text)
        self.assertIn("25/50/75 dias", text)
        self.assertNotIn("Horário", text)
        self.assertNotIn("17:00", text)

    def test_main_has_one_combined_panel_and_review_before_send(self):
        main = (APP / "main.py").read_text(encoding="utf-8")
        panel = main[main.index("class PrazoPanel"):main.index("class ChatGPTPanel")]
        whatsapp = main[
            main.index("def _place_freight_message_in_whatsapp"):
            main.index("def _set_prazo_focus_guard")
        ]
        self.assertIn('ALIYVO_VERSION = "0.23.45"', main)
        self.assertIn("Frete e pagamento", panel)
        self.assertIn("Calcular frete + pagamento", panel)
        self.assertIn("Colocar no WhatsApp", panel)
        self.assertIn("freight_payment_terms", panel)
        self.assertNotIn("prazo_tabs", panel)
        self.assertNotIn("payment_tab", panel)
        self.assertNotIn("quote['cutoff']", panel)
        self.assertNotIn("Corte:", panel)
        self.assertNotIn("Faltam", panel)
        self.assertIn("insertText", whatsapp)
        self.assertNotIn("send.click", whatsapp)


if __name__ == "__main__":
    unittest.main()
