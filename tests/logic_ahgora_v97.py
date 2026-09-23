import os,sys,tempfile
from datetime import datetime
from pathlib import Path

os.environ["QT_QPA_PLATFORM"]="offscreen"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"]="--disable-gpu --no-sandbox"
os.environ["LOCALAPPDATA"]=str(Path(tempfile.gettempdir())/"aliyvo-v97-test")

appdir=Path(sys.argv[1]); sys.path.insert(0,str(appdir))
import aliyvo_ponto as p

assert p.POINT_MODULE_VERSION=="0.22.97"
source=(appdir/"aliyvo_ponto.py").read_text(encoding="utf-8")
assert "top_level_navigation" in source
assert "view.setUrl(QUrl(AHGORA_MIRROR_API))" in source
assert "toPlainText" in source
assert "credentials:'include'" not in source
assert "fetch(" not in source[source.index("def _sync_using_view"):source.index("def _sync_via_persistent_browser")]
assert "JÁ ENTREI — SINCRONIZAR" in source
assert "ForcePersistentCookies" in source

now=datetime(2026,9,23,12,0)
index={"meses":{"2026-09":{"referencia":"ref1"}}}
detail={"dias":{"2026-09-23":{"batidas":[{"hora":"0750"},{"hora":"1208"}]}}}
v=p.validate_modern_mirror_payload(index,detail,now,"2026-09")
assert v["session_ok"] is True
assert p.extract_today_punches(detail,now)==["07:50","12:08"]

print("AHGORA_V97_DIRECT_NAV=OK")
print("AHGORA_V97_NO_FETCH_CORS=OK")
print("ALIYVO_V97_SYNC_FIX=OK")
