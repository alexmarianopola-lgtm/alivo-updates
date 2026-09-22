import json
import os
import sys
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["LOCALAPPDATA"] = str(Path(tempfile.gettempdir()) / "aliyvo-ponto-v92-test")

appdir = Path(sys.argv[1])
sys.path.insert(0, str(appdir))

import aliyvo_ponto as p
from PyQt6.QtWidgets import QApplication, QPushButton, QWidget

assert p.POINT_MODULE_VERSION == "0.22.92"
assert [x["time"] for x in p.POINT_SLOTS] == ["07:50", "12:08", "13:30", "18:00"]

monday_early = datetime(2026, 9, 21, 7, 40)
monday_late = datetime(2026, 9, 21, 8, 27)
monday_lunch = datetime(2026, 9, 21, 12, 20)
saturday = datetime(2026, 9, 26, 10, 0)

state = p.normalize_state({}, monday_early)
assert p.pending_slot_for(monday_early, state) is None
assert p.next_future_slot_for(monday_early, state)["id"] == "entrada"

state = p.normalize_state({}, monday_late)
assert p.pending_slot_for(monday_late, state)["id"] == "entrada", "atraso deve continuar pendente"

state["slots"]["entrada"] = {"status":"confirmed"}
assert p.pending_slot_for(monday_late, state) is None
assert p.next_future_slot_for(monday_late, state)["id"] == "saida_almoco"

assert p.pending_slot_for(saturday, p.normalize_state({}, saturday)) is None

state_lunch = p.normalize_state({}, monday_lunch)
state_lunch["slots"]["entrada"] = {"status":"confirmed"}
assert p.pending_slot_for(monday_lunch, state_lunch)["id"] == "saida_almoco"
state_lunch["slots"]["saida_almoco"] = {"status":"missed"}
assert p.pending_slot_for(monday_lunch, state_lunch) is None
assert len(p.missed_slots_for(state_lunch)) == 1

source = (appdir / "aliyvo_ponto.py").read_text(encoding="utf-8")
assert "setSingleShot(True)" in source
assert "ThreadingHTTPServer((\"127.0.0.1\", POINT_API_PORT)" in source
assert "document" not in source.lower(), "módulo de ponto não deve consultar DOM do WhatsApp"
assert "senha" in source.lower()  # texto de privacidade, sem armazenamento de senha
assert "password" not in source.lower()

app = QApplication.instance() or QApplication([])
owner = QWidget()
button = QPushButton()
ctrl = p.AliyvoPontoController(owner, button)
ctrl._state = p.normalize_state({}, datetime.now())
ctrl._update_snapshot()

req = urllib.request.Request(
    "http://127.0.0.1:17892/health",
    headers={p.POINT_API_HEADER:p.POINT_API_SECRET},
)
ctrl._start_api()
with urllib.request.urlopen(req, timeout=2) as response:
    health = json.loads(response.read().decode("utf-8"))
assert health["ok"] is True
assert health["module_version"] == "0.22.92"

print("PONTO_LATE_ARRIVAL=OK")
print("PONTO_PERSISTENCE_MODEL=OK")
print("PONTO_SINGLE_SHOT_TIMER=OK")
print("PONTO_LOCAL_BRIDGE=OK")
print("ALIYVO_V92_PONTO_LOGIC=OK")
