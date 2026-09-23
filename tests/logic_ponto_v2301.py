import os,sys,tempfile
from pathlib import Path
os.environ["QT_QPA_PLATFORM"]="offscreen"
os.environ["LOCALAPPDATA"]=str(Path(tempfile.gettempdir())/"aliyvo-v2301-test")
appdir=Path(sys.argv[1]); sys.path.insert(0,str(appdir))
import aliyvo_ponto as p
assert p.POINT_MODULE_VERSION=="0.23.01"
source=(appdir/"aliyvo_ponto.py").read_text(encoding="utf-8")
assert "SendInput" in source
assert "GetForegroundWindow" in source
assert "BringWindowToTop" in source
assert "kernel32.Sleep(450)" in source
assert "ahgora_chrome_hotkey_sent" in source
assert "keybd_event" not in source
print("ALIYVO_02301_SHORTCUT_FIX=OK")
