import json,sys
from pathlib import Path
root=Path(sys.argv[1])
main=(root/"_app"/"main.py").read_text(encoding="utf-8")
mod=(root/"_app"/"aliyvo_ponto.py").read_text(encoding="utf-8")
assert 'ALIYVO_VERSION = "0.22.94"' in main
assert 'POINT_MODULE_VERSION = "0.22.94"' in mod
assert 'validate_mirror_payload' in mod
assert 'DIAGNÓSTICO DA SINCRONIZAÇÃO' in mod
manifest=json.loads((root/"EXTENSAO_PONTO_SANKHYA"/"manifest.json").read_text(encoding="utf-8"))
assert manifest["version"]=="2.1.1"
bg=(root/"EXTENSAO_PONTO_SANKHYA"/"background.js").read_text(encoding="utf-8")
assert "aliyvo-ponto-02294" in bg
assert "aliyvo-ponto-02293" not in bg
print("ALIYVO_V94_PACKAGE=OK")
