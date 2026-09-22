import json
import sys
from pathlib import Path

root=Path(sys.argv[1])
main=(root/"_app"/"main.py").read_text(encoding="utf-8")
module=(root/"_app"/"aliyvo_ponto.py").read_text(encoding="utf-8")
ext=root/"EXTENSAO_PONTO_SANKHYA"

assert 'ALIYVO_VERSION = "0.22.93"' in main
assert 'POINT_MODULE_VERSION = "0.22.93"' in module
assert 'AHGORA_MIRROR_URL = "https://www.ahgora.com.br/externo/getApuracao"' in module
assert 'AHGORA_PUNCH_URL = "https://www.ahgora.com.br/batidaonline/verifyIdentification"' in module
assert "CryptProtectData" in module and "CryptUnprotectData" in module
assert "BATER PONTO AGORA NO AHGORA" in module

manifest=json.loads((ext/"manifest.json").read_text(encoding="utf-8"))
assert manifest["version"]=="2.1.0"
bg=(ext/"background.js").read_text(encoding="utf-8")
assert 'aliyvo-ponto-02293' in bg
assert 'aliyvo-ponto-02292' not in bg

print("V93_MAIN_VERSION=OK")
print("V93_AHGORA_ENDPOINTS=OK")
print("V93_EXTENSION_BRIDGE_SECRET=OK")
print("ALIYVO_V93_PACKAGE=OK")
