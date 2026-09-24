from pathlib import Path
import sys,ast,textwrap,datetime

app=Path(sys.argv[1])
src=(app/'main.py').read_text(encoding='utf-8')

assert 'ALIYVO_VERSION = "0.23.04"' in src
assert 'self.radar_toggle=QPushButton("🎯  Radar da Carteira")' in src
assert 'self.radar_toggle.clicked.connect(self._radar_show_dialog)' in src
assert 'def _radar_show_dialog(self):' in src
assert 'HISTÓRICO — ÚLTIMOS 12 MESES' in src
assert 'RECORRÊNCIA / RECOMPRA' in src
assert 'Atualize mensalmente' in src
assert 'Atualize semanalmente' in src
assert 'RADAR DA CARTEIRA' in src
assert 'ALIYVO_ORIGIN_ID = "ALIYVO-ORIGIN-20260924-2302-6F91D2C4A8E73B5C"' in src
assert 'setInterval(20000)' in src
assert (app/'vendor'/'xlrd').exists(), 'xlrd embarcado nao encontrado'

# Executa os próprios métodos de parsing do main.py, sem instanciar a interface.
tree=ast.parse(src)
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='MainWindow')
wanted={'_radar_norm','_radar_num','_radar_date','_radar_header_row','_radar_find_col',
        '_radar_parse_history_rows','_radar_parse_recurrence_rows'}
methods=[n for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in wanted]
assert len(methods)==len(wanted), (len(methods),wanted-{n.name for n in methods})
mini=ast.Module(body=[ast.ClassDef(name='Dummy',bases=[],keywords=[],decorator_list=[],body=methods)],type_ignores=[])
ast.fix_missing_locations(mini)
ns={}
exec(compile(mini,'<radar-methods>','exec'),ns)
d=ns['Dummy']()

hist=[
 ["CODPARC","CLIENTE","OUT/25","NOV/25","DEZ/25","JAN/26","FEV/26","MAR/26","ABR/26","MAI/26","JUN/26","JUL/26","AGO/26","SET/26"],
 ["100","AUTO PEÇAS TESTE",10000,10000,10000,9000,9000,9000,7000,6500,6000,5500,5000,4500],
 ["200","CLIENTE CRESCENDO",1000,1200,1500,1800,2100,2400,3000,3500,4000,4500,5000,5500],
]
clients,diag=d._radar_parse_history_rows(hist)
assert len(clients)==2,clients
assert clients['100']['trend_pct'] < 0,clients['100']
assert clients['200']['trend_pct'] > 0,clients['200']
assert len(clients['100']['month_labels'])==12

rec=[
 ["CODPARC","CLIENTE","CODPROD","PRODUTO","QTD COMPRAS","MEDIA DIAS","ULTIMA COMPRA","PROXIMA COMPRA","ALERTA"],
 ["100","AUTO PEÇAS TESTE","32218","ROLAMENTO 32218",6,20,"01/09/2026","21/09/2026","ALERTA"],
 ["200","CLIENTE CRESCENDO","RET01","RETENTOR",4,30,"15/09/2026","15/10/2026",""],
]
items,rdiag=d._radar_parse_recurrence_rows(rec)
assert len(items)==2,items
a=items[0]
assert a['client_code']=='100'
assert a['product']=='ROLAMENTO 32218'
assert a['avg_days']==20
assert a['alert']=='ALERTA'
assert a['score']>=55

for token in ['radar_carteira.json','radar_fontes','sha256','Vincular conversa atual','Selecionar planilha .XLS']:
    assert token in src,token

print('RADAR_DUAS_FONTES_VISIVEIS=OK')
print('RADAR_HISTORICO_12_MESES=OK')
print('RADAR_RECOMPRA=OK')
print('RADAR_PARSER_REAL=OK')
print('RADAR_VINCULO_WHATSAPP=OK')
print('RADAR_ASSISTENCIA_CLIENTE=OK')
print('PROVENIENCIA_PRESERVADA=OK')
print('WHATSAPP_TURBO_PRESERVADO=OK')
print('ALIYVO_V2304_RADAR=OK')
