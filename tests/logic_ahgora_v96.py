import os,sys,tempfile
from datetime import datetime
from pathlib import Path

os.environ["QT_QPA_PLATFORM"]="offscreen"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"]="--disable-gpu --no-sandbox"
os.environ["LOCALAPPDATA"]=str(Path(tempfile.gettempdir())/"aliyvo-v96-test")

appdir=Path(sys.argv[1])
sys.path.insert(0,str(appdir))
import aliyvo_ponto as p

assert p.POINT_MODULE_VERSION=="0.22.96"
assert p.POINT_API_SECRET=="aliyvo-ponto-02296"

source=(appdir/"aliyvo_ponto.py").read_text(encoding="utf-8")
assert "QWebEngineProfile" in source
assert "QWebEngineView" in source
assert "show_ahgora_browser_link" in source
assert "_sync_using_view" in source
assert "_sync_via_persistent_browser" in source
assert "VINCULAR / REABRIR AHGORA" in source
assert "JÁ ENTREI — SINCRONIZAR" in source
assert "ahgora_browser_profile" in source
assert "setPersistentCookiesPolicy" in source
assert "api-espelho/apuracao" in source

# O sync normal agora deve usar a sessao do navegador, não o login HTTP reproduzido.
start=source.index('    def sync_ahgora_async(self, reason: str = "manual") -> None:')
end=source.index('    def _on_sync_finished',start)
sync_block=source[start:end]
assert "_sync_via_persistent_browser" in sync_block
assert "_login_and_fetch_modern_mirror" not in sync_block

# Funções puras do espelho continuam corretas.
now=datetime(2026,9,23,10,40)
index={"meses":{"2026-09":{"referencia":"abc"}}}
detail={"dias":{"2026-09-23":{"batidas":[{"hora":"0749"},{"hora":"1209"}]}}}
v=p.validate_modern_mirror_payload(index,detail,now,"2026-09")
assert v["session_ok"] is True
assert p.extract_today_punches(detail,now)==["07:49","12:09"]

state=p.normalize_state({},now)
state["slots"]["entrada"]={"status":"missed","source":"old"}
state=p.reconcile_real_punches(state,["07:49","12:09"],now)
assert state["slots"]["entrada"]["actual_time"]=="07:49"
assert state["slots"]["saida_almoco"]["actual_time"]=="12:09"
assert state["slots"]["entrada"]["source"]=="ahgora_sync"

# O modulo de ponto pode usar JS apenas no webview Ahgora; não deve tocar DOM do WhatsApp.
assert "WhatsApp" not in source or "DOM do WhatsApp" not in source
assert "runJavaScript(js" in source
assert "https://app.ahgora.com.br/api-espelho/apuracao/" in source

print("AHGORA_V96_BROWSER_SESSION=OK")
print("AHGORA_V96_PERSISTENT_COOKIES=OK")
print("AHGORA_V96_SYNC_RECONCILE=OK")
print("ALIYVO_V96_AHGORA_BROWSER=OK")
