import json,sys
from pathlib import Path
root=Path(sys.argv[1])
main=(root/"_app"/"main.py").read_text(encoding="utf-8")
mod=(root/"_app"/"aliyvo_ponto.py").read_text(encoding="utf-8")
assert 'ALIYVO_VERSION = "0.22.95"' in main
assert 'POINT_MODULE_VERSION = "0.22.95"' in mod
assert "externo/getApuracao" not in mod
assert 'https://app.ahgora.com.br/api-espelho/apuracao/' in mod
assert 'https://app.ahgora.com.br/batidaonline' in mod
assert "activateDeviceOnLineByLoginAndPassword" in mod
assert "getDefaultExternalInfo" in mod
assert "getPublicKey" in mod
assert "verifyIdentification" in mod
assert "CryptProtectData" in mod and "CryptUnprotectData" in mod
manifest=json.loads((root/"EXTENSAO_PONTO_SANKHYA"/"manifest.json").read_text(encoding="utf-8"))
assert manifest["version"]=="2.2.0"
bg=(root/"EXTENSAO_PONTO_SANKHYA"/"background.js").read_text(encoding="utf-8")
assert "aliyvo-ponto-02295" in bg
assert "aliyvo-ponto-02294" not in bg
print("ALIYVO_V95_PACKAGE=OK")
