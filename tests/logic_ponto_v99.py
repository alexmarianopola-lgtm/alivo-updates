import os,sys,tempfile
from pathlib import Path

os.environ["QT_QPA_PLATFORM"]="offscreen"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"]="--disable-gpu --no-sandbox"
os.environ["LOCALAPPDATA"]=str(Path(tempfile.gettempdir())/"aliyvo-v99-test")
appdir=Path(sys.argv[1]); sys.path.insert(0,str(appdir))
import aliyvo_ponto as p

assert p.POINT_MODULE_VERSION=="0.22.99"
source=(appdir/"aliyvo_ponto.py").read_text(encoding="utf-8")
assert 'AHGORA_OFFICIAL_PUNCH_PAGE = "https://www.ahgora.com.br/externo/batidas"' in source
assert "JÁ BATI NO AHGORA — SINCRONIZAR" in source
assert "portal OFICIAL do Ahgora" in source
assert "view.setUrl(QUrl(AHGORA_OFFICIAL_PUNCH_PAGE))" in source

start=source.index("    def punch_ahgora(self) -> None:")
end=source.index("    def _on_punch_finished",start)
block=source[start:end]
assert "_modern_punch(" not in block
assert "_legacy_modern_punch_unused(" not in block
assert "threading.Thread" not in block
assert "verifyIdentification" not in block
assert "activateDeviceOnLineByLoginAndPassword" not in block
assert "_sync_using_view(" in block

print("PONTO_V99_OFFICIAL_PAGE=OK")
print("PONTO_V99_NO_DEVICE_API=OK")
print("ALIYVO_V99_PUNCH_FLOW=OK")
