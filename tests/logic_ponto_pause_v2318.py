from pathlib import Path
import ast,sys
root=Path(sys.argv[1])
s=(root/'aliyvo_ponto.py').read_text(encoding='utf-8')
ast.parse(s)
for needle in [
    'POINT_MODULE_VERSION = "0.23.18"',
    'def _point_alerts_paused_today(self) -> bool:',
    'def pause_point_alerts_today(self) -> None:',
    'PAUSAR AVISOS DE PONTO HOJE',
    'Não altera nenhuma batida no Ahgora',
    'REATIVAR AVISOS',
]:
    assert needle in s, needle
print('LOGIC_PONTO_PAUSE_V2318=OK')
