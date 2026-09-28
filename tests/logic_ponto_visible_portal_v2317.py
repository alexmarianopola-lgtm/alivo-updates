from pathlib import Path
import ast,sys,re
root=Path(sys.argv[1])
s=(root/'aliyvo_ponto.py').read_text(encoding='utf-8')
ast.parse(s)

required=[
 'POINT_MODULE_VERSION = "0.23.17"',
 'def _sync_from_visible_ahgora_portal',
 'roundedPunchAncestor',
 'saldo de banco de horas',
 'horas previstas',
 'self._sync_from_visible_ahgora_portal(',
 '"visible_portal": True',
 'Leitura da tela oficial:',
]
for x in required:
    assert x in s,x

# garante que continua reconciliando a 1a batida encontrada com a entrada
fn=next(n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name=='reconcile_real_punches')
src=ast.get_source_segment(s,fn)
assert '"status": "confirmed"' in src
assert '"actual_time": punches[index]' in src

# start_sync precisa preferir tela visivel antes da API
m=re.search(r'def start_sync\(\):(.{0,1200})',s,re.S)
assert m and '_sync_from_visible_ahgora_portal' in m.group(1)
print('LOGIC_PONTO_VISIBLE_PORTAL_V2317=OK')
