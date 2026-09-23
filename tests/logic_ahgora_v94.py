import os, sys, tempfile
from datetime import datetime
from pathlib import Path

os.environ["QT_QPA_PLATFORM"]="offscreen"
os.environ["LOCALAPPDATA"]=str(Path(tempfile.gettempdir())/"aliyvo-v94-test")
appdir=Path(sys.argv[1]); sys.path.insert(0,str(appdir))
import aliyvo_ponto as p

assert p.POINT_MODULE_VERSION=="0.22.94"
now=datetime(2026,9,23,9,45)

valid={
  "empresa":{"empresa":"EMP1","nome":"Teste","inicia_dia":"01"},
  "funcionario":{"matricula":"123","nome":"Teste"},
  "dias":{"2026-09-23":{"batidas":[{"hora":"0752","tipo":"L"}],"resultado":[]}}
}
v=p.validate_mirror_payload(valid,now,"123","EMP1")
assert v["registration_match"] and v["company_match"]
assert v["punch_count"]==1
assert p.extract_today_punches(valid,now)==["07:52"]

for bad in [
  {"error":"not_found"},
  {"empresa":{},"funcionario":{},"dias":{}},
  {"empresa":{"empresa":"X"},"funcionario":{"matricula":"123"},"dias":{"2026-09-23":{"batidas":[]}}},
  {"empresa":{"empresa":"EMP1"},"funcionario":{"matricula":"999"},"dias":{"2026-09-23":{"batidas":[]}}},
]:
  try:
    p.validate_mirror_payload(bad,now,"123","EMP1")
  except RuntimeError:
    pass
  else:
    raise AssertionError("payload invalido aceito: "+repr(bad))

# stale missed from RC1/RC2 must be cleared by real sync
state=p.normalize_state({},now)
state["slots"]["entrada"]={"status":"missed","actual_time":"09:00","source":"aliyvo_dialog"}
state=p.reconcile_real_punches(state,["07:52"],now)
assert state["slots"]["entrada"]["status"]=="confirmed"
assert state["slots"]["entrada"]["actual_time"]=="07:52"
assert state["slots"]["entrada"]["source"]=="ahgora_sync"
assert "saida_almoco" not in state["slots"]

# Valid zero-punch mirror must clear stale local statuses.
zero={
  "empresa":{"empresa":"EMP1"},
  "funcionario":{"matricula":"123"},
  "dias":{"2026-09-23":{"batidas":[],"resultado":[]}}
}
p.validate_mirror_payload(zero,now,"123","EMP1")
state=p.normalize_state({},now)
state["slots"]["entrada"]={"status":"missed","source":"aliyvo_dialog"}
state=p.reconcile_real_punches(state,[],now)
assert state["slots"]=={}

source=(appdir/"aliyvo_ponto.py").read_text(encoding="utf-8")
assert "DIAGNÓSTICO DA SINCRONIZAÇÃO" in source
assert "0 batidas encontradas hoje" in source
assert "configured and ah.get(\"last_sync_ok\")" in source
assert "setInterval(" not in source
assert "runJavaScript" not in source
assert "evaluate_js" not in source

print("AHGORA_V94_PAYLOAD_VALIDATION=OK")
print("AHGORA_V94_STALE_STATE_CLEAR=OK")
print("AHGORA_V94_ZERO_PUNCH_VALIDATION=OK")
print("AHGORA_V94_DIRECT_PUNCH_GATED=OK")
print("ALIYVO_V94_AHGORA_FIX=OK")
