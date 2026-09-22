import json
import sys
from pathlib import Path

root=Path(sys.argv[1])
ext=root/"EXTENSAO_PONTO_SANKHYA"
manifest=json.loads((ext/"manifest.json").read_text(encoding="utf-8"))

assert manifest["manifest_version"]==3
assert "http://somaforce.nuvemdatacom.com.br/*" in manifest["host_permissions"]
assert "http://127.0.0.1/*" in manifest["host_permissions"]
matches=manifest["content_scripts"][0]["matches"]
assert matches==["http://somaforce.nuvemdatacom.com.br/*"]
assert all(":7075" not in x for x in matches), "Chrome match patterns não aceitam porta no host"

content=(ext/"content.js").read_text(encoding="utf-8")
background=(ext/"background.js").read_text(encoding="utf-8")
assert 'location.port !== "7075"' in content
assert "setInterval(checkNow,15000)" in content
assert "127.0.0.1:17892" in background
assert "ponto-confirm" in background and "ponto-missed" in background
assert "aliyvoPontoForceTest" in content

print("EXTENSION_MANIFEST=OK")
print("EXTENSION_SANKHYA_PORT_GUARD=OK")
print("EXTENSION_ALIYVO_BRIDGE=OK")
print("ALIYVO_V92_EXTENSION=OK")
