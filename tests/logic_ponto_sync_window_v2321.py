from pathlib import Path
import sys
from datetime import datetime

root=Path(sys.argv[1])
sys.path.insert(0,str(root))

import aliyvo_ponto as p

now=datetime(2026,9,29,9,5,0)

# BUG PRINCIPAL: 29/09 nunca pode priorizar outubro.
assert p._mirror_month_candidates(now)[:3] == ["2026-09","2026-10","2026-08"], p._mirror_month_candidates(now)
assert p._mirror_month_key(now) == "2026-09"

payload={
    "dias":{
        "2026-09-29":{
            "batidas":[{"hora":"08:16"}]
        }
    }
}
assert p.extract_today_punches(payload,now)==["08:16"]

base={
    "date":"2026-09-29",
    "slots":{},
    "updated_at":None,
    "ahgora":{"last_sync_at":None,"last_sync_ok":False,"last_error":"","punches_today":[]},
}

# 08:16 deve confirmar a entrada 07:50: atraso de 26 min.
r=p.reconcile_real_punches(dict(base),["08:16"],now)
assert r["slots"]["entrada"]["status"]=="confirmed"
assert r["slots"]["entrada"]["actual_time"]=="08:16"
assert "saida_almoco" not in r["slots"]

# Limites exatos de +/- 60 min contam.
for t in ("06:50","08:50"):
    m=p._match_punches_to_slots([t])
    assert m.get("entrada")==t,(t,m)

# Fora de 60 min NAO conta como entrada.
assert "entrada" not in p._match_punches_to_slots(["08:51"])
assert "entrada" not in p._match_punches_to_slots(["06:49"])

# Quatro batidas dentro da janela devem casar com o horario mais proximo.
m=p._match_punches_to_slots(["08:16","12:35","13:25","18:55"])
assert m=={
    "entrada":"08:16",
    "saida_almoco":"12:35",
    "volta_almoco":"13:25",
    "saida_final":"18:55",
},m

# Uma batida no meio entre almoco/retorno vai ao horario mais proximo.
m=p._match_punches_to_slots(["13:00"])
assert m.get("volta_almoco")=="13:00",m

# Validacao nao pode aceitar periodo errado sem o dia atual como "0 batidas".
index={"meses":{"2026-10":{"referencia":"abc"},"2026-09":{"referencia":"def"}}}
wrong={"dias":{"2026-10-01":{"batidas":[]}}}
try:
    p.validate_modern_mirror_payload(index,wrong,now,"2026-10")
except RuntimeError:
    pass
else:
    raise AssertionError("periodo errado foi aceito como zero batidas")

print("LOGIC_PONTO_SYNC_WINDOW_V2321=OK")
