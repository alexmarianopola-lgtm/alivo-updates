import json,sys
from pathlib import Path
root=Path(sys.argv[1])
main=(root/"_app"/"main.py").read_text(encoding="utf-8")
mod=(root/"_app"/"aliyvo_ponto.py").read_text(encoding="utf-8")
assert 'ALIYVO_VERSION = "0.22.96"' in main
assert 'POINT_MODULE_VERSION = "0.22.96"' in mod
assert "VINCULAR / REABRIR AHGORA" in mod
assert "QWebEngineProfile" in mod
assert "ahgora_browser_profile" in mod
manifest=json.loads((root/"EXTENSAO_PONTO_SANKHYA"/"manifest.json").read_text(encoding="utf-8"))
assert manifest["version"]=="2.3.0"
bg=(root/"EXTENSAO_PONTO_SANKHYA"/"background.js").read_text(encoding="utf-8")
assert "aliyvo-ponto-02296" in bg
assert "aliyvo-ponto-02295" not in bg
print("ALIYVO_V96_PACKAGE=OK")
