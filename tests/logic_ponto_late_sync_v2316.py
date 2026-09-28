from pathlib import Path
import ast, sys

root=Path(sys.argv[1])
p=root/'aliyvo_ponto.py'
s=p.read_text(encoding='utf-8')
ast.parse(s)

required=[
    'POINT_MODULE_VERSION = "0.23.16"',
    'def _browser_session_available(self) -> bool:',
    'def _can_sync_ahgora(self) -> bool:',
    'view.loadFinished.connect(maybe_auto_sync_after_login)',
    'self._state = reconcile_real_punches(self._state, punches, datetime.now())',
    'late = f" • atrasado {delay} min"',
]
for x in required:
    assert x in s, x

# Verifica semanticamente a reconciliacao de batida tardia sem carregar a UI.
mod=ast.parse(s)
fn=next(n for n in mod.body if isinstance(n,ast.FunctionDef) and n.name=='reconcile_real_punches')
helper_names={'normalize_state','POINT_SLOTS'}
# Funcao deve continuar marcando a primeira batida real como confirmed e guardar actual_time.
src=ast.get_source_segment(s,fn)
assert '"status": "confirmed"' in src
assert '"actual_time": punches[index]' in src
assert 'index < len(punches)' in src

# Garante que os pontos automaticos usam a nova fonte de sincronizacao.
for needle in [
    'if self._can_sync_ahgora():',
    'if self._can_sync_ahgora() and self._sync_is_stale(60):',
    'if self._can_sync_ahgora() and self._sync_is_stale(55) and not self._sync_busy:',
]:
    assert needle in s, needle

print('LOGIC_PONTO_V2316=OK')
