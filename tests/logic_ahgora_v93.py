import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["LOCALAPPDATA"] = str(Path(tempfile.gettempdir()) / "aliyvo-ponto-v93-test")

appdir = Path(sys.argv[1])
sys.path.insert(0, str(appdir))

import aliyvo_ponto as p
from PyQt6.QtWidgets import QApplication, QPushButton, QWidget

assert p.POINT_MODULE_VERSION == "0.22.93"
assert [x["time"] for x in p.POINT_SLOTS] == ["07:50", "12:08", "13:30", "18:00"]

now = datetime(2026, 9, 22, 12, 30)
fixture = {
    "dias": {
        "2026-09-22": {
            "batidas": [
                {"hora":"0751","tipo":"O","equipamento":"WEB"},
                {"hora":"12:09","tipo":"O","equipamento":"WEB"},
            ],
            "resultado": [],
        }
    }
}
punches = p.extract_today_punches(fixture, now)
assert punches == ["07:51", "12:09"], punches

state = p.normalize_state({}, now)
state["slots"]["entrada"] = {
    "status":"confirmed","actual_time":"12:30","source":"manual_fallback"
}
state = p.reconcile_real_punches(state, punches, now)
assert state["slots"]["entrada"]["actual_time"] == "07:51"
assert state["slots"]["entrada"]["source"] == "ahgora_sync"
assert state["slots"]["saida_almoco"]["actual_time"] == "12:09"
assert "volta_almoco" not in state["slots"]
# 12:30 é antes de 13:30, então não existe pendência da volta.
assert p.pending_slot_for(now, state) is None
assert p.next_future_slot_for(now, state)["id"] == "volta_almoco"

late = datetime(2026, 9, 22, 14, 5)
assert p.pending_slot_for(late, state)["id"] == "volta_almoco"

# DPAPI: a senha não pode aparecer no arquivo em texto puro.
secret = "SenhaTeste-Ahgora-987"
encoded = p._dpapi_protect(secret)
assert secret not in encoded
assert p._dpapi_unprotect(encoded) == secret

app = QApplication.instance() or QApplication([])
owner = QWidget()
button = QPushButton()
ctrl = p.AliyvoPontoController(owner, button)

ctrl._credentials_file.parent.mkdir(parents=True, exist_ok=True)
ctrl._save_credentials({
    "registration":"12345",
    "password":secret,
    "company_id":"empresa123",
    "identity":"token456",
})
raw = ctrl._credentials_file.read_text(encoding="ascii")
assert secret not in raw
cfg = ctrl._load_credentials()
assert cfg["registration"] == "12345"
assert cfg["password"] == secret
assert cfg["company_id"] == "empresa123"
assert cfg["identity"] == "token456"

source = (appdir / "aliyvo_ponto.py").read_text(encoding="utf-8")
assert "AHGORA_MIRROR_URL" in source
assert "AHGORA_PUNCH_URL" in source
assert "BATER PONTO AGORA NO AHGORA" in source
assert "QMessageBox.question" in source
assert "self._timer.setSingleShot(True)" in source
assert "setInterval(" not in source
assert "runJavaScript" not in source
assert "evaluate_js" not in source
assert "document." not in source
assert "senha" not in "\n".join(
    line for line in source.splitlines()
    if "_log(" in line and "credentials_saved" not in line
).lower()

print("AHGORA_REAL_PUNCH_RECONCILIATION=OK")
print("AHGORA_DPAPI_CREDENTIALS=OK")
print("AHGORA_DIRECT_PUNCH_REQUIRES_CONFIRMATION=OK")
print("PONTO_NO_PERMANENT_TIMER=OK")
print("ALIYVO_V93_AHGORA_LOGIC=OK")
