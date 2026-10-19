import sys
import unittest
from pathlib import Path


APP = Path(__file__).resolve().parents[1] / "source" / "v0.23.43"
sys.path.insert(0, str(APP))

from aliyvo_freight import (  # noqa: E402
    city_choices,
    quote_freight,
    resolve_city,
    services_for_uf,
)


class FreightV2343Tests(unittest.TestCase):
    def assert_quote(self, city, service, value, status, fee=None):
        result = quote_freight(city, service, value)
        self.assertTrue(result.get("ok"), result)
        self.assertEqual(status, result["status"])
        if fee is not None:
            self.assertEqual(str(fee), str(result["fee"]))
        return result

    def test_city_lookup_accepts_accents_and_missing_accents(self):
        self.assertEqual("SC", resolve_city("Araranguá")["uf"])
        self.assertEqual("SC", resolve_city("Ararangua")["uf"])
        self.assertEqual("RS", resolve_city("Porto Alegre")["uf"])
        self.assertGreaterEqual(len(city_choices()), 790)

    def test_duplicate_city_requires_state(self):
        self.assertFalse(resolve_city("Bom Jesus")["ok"])
        self.assertEqual("SC", resolve_city("Bom Jesus - SC")["uf"])
        self.assertEqual("RS", resolve_city("Bom Jesus / RS")["uf"])

    def test_matriz_sao_miguel_sc_boundaries(self):
        self.assert_quote("Araranguá", "matriz_sao_miguel", "799,99", "paid", 65)
        self.assert_quote("Araranguá", "matriz_sao_miguel", "800,00", "paid", 45)
        self.assert_quote("Araranguá", "matriz_sao_miguel", "1.199,99", "paid", 45)
        self.assert_quote("Araranguá", "matriz_sao_miguel", "1.200,00", "free", 0)
        self.assert_quote("Araranguá", "matriz_sao_miguel", "1.200", "free", 0)

    def test_matriz_sao_miguel_rs_boundaries(self):
        self.assert_quote("Torres", "matriz_sao_miguel", "499,99", "paid", 75)
        self.assert_quote("Torres", "matriz_sao_miguel", "500,00", "paid", 65)
        self.assert_quote("Torres", "matriz_sao_miguel", "1.000,00", "paid", 50)
        self.assert_quote("Torres", "matriz_sao_miguel", "1.500,00", "free", 0)

    def test_matriz_fabris_and_leomar(self):
        self.assert_quote("Criciúma", "matriz_fabris", 700, "paid", 65)
        self.assert_quote("Criciúma", "matriz_fabris", 1200, "free", 0)
        self.assert_quote("Porto Alegre", "matriz_leomar", 699, "paid", 70)
        self.assert_quote("Porto Alegre", "matriz_leomar", 700, "paid", 55)
        self.assert_quote("Porto Alegre", "matriz_leomar", 1200, "paid", 40)
        self.assert_quote("Porto Alegre", "matriz_leomar", 2000, "free", 0)

    def test_tres_cachoeiras_rules(self):
        self.assert_quote("Torres", "tres_sao_miguel", 499, "paid", 65)
        self.assert_quote("Torres", "tres_sao_miguel", 500, "paid", 55)
        self.assert_quote("Torres", "tres_sao_miguel", 1000, "paid", 40)
        self.assert_quote("Torres", "tres_sao_miguel", 1500, "free", 0)
        self.assert_quote("Torres", "tres_leomar", 699, "paid", 65)
        self.assert_quote("Torres", "tres_leomar", 700, "paid", 55)

    def test_itajai_sao_miguel_rs_boundaries(self):
        self.assert_quote("Porto Alegre", "itajai_sao_miguel", 799, "paid", 120)
        self.assert_quote("Porto Alegre", "itajai_sao_miguel", 800, "paid", 95)
        self.assert_quote("Porto Alegre", "itajai_sao_miguel", 1500, "paid", 75)
        self.assert_quote("Porto Alegre", "itajai_sao_miguel", 2000, "paid", 60)
        self.assert_quote("Porto Alegre", "itajai_sao_miguel", 2500, "free", 0)

    def test_negotiated_carriers_are_never_invented(self):
        self.assert_quote("Araranguá", "matriz_sao_joao", 5000, "negotiated")
        self.assert_quote("Araranguá", "tres_sao_joao", 5000, "negotiated")
        self.assert_quote("Itajaí", "itajai_sao_joao", 1199, "negotiated")
        self.assert_quote("Itajaí", "itajai_sao_joao", 1200, "free", 0)

    def test_services_are_filtered_by_state(self):
        sc = {item.key for item in services_for_uf("SC")}
        rs = {item.key for item in services_for_uf("RS")}
        self.assertIn("matriz_fabris", sc)
        self.assertNotIn("matriz_fabris", rs)
        self.assertIn("matriz_leomar", rs)
        self.assertNotIn("matriz_leomar", sc)

    def test_invalid_data_returns_guidance(self):
        self.assertFalse(quote_freight("", "matriz_sao_miguel", 1000)["ok"])
        self.assertFalse(quote_freight("Araranguá", "", 1000)["ok"])
        self.assertFalse(quote_freight("Araranguá", "matriz_sao_miguel", "x")["ok"])


if __name__ == "__main__":
    unittest.main()

