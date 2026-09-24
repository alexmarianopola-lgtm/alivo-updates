from pathlib import Path
import sys,ast
app=Path(sys.argv[1]);s=(app/'main.py').read_text(encoding='utf-8')
assert 'ALIYVO_VERSION = "0.23.07"' in s
for token in [
 'a carteira oficial vem SOMENTE do histórico de 12 meses',
 'Um mesmo cliente pode ter vários compradores/contatos do WhatsApp.',
 'def _radar_links_label(self,key):',
 'def _radar_offer_items_for_key(self,key,limit=8):',
 '🎯 O QUE OFERECER AGORA',
 'self.radar_offer_card=QLabel',
 'self.radar_offer_button.clicked.connect(self._radar_current_offer_dialog)',
 'try:self._radar_refresh_offer_panel(name)',
 'CLIENTES PARA CHAMAR',
 'def _radar_current_offer_dialog(self):'
]: assert token in s,token
# A carteira não pode mais ser criada pela recorrência.
tree=ast.parse(s)
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='MainWindow')
m=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_radar_all_clients')
src=ast.get_source_segment(s,m)
assert 'recurrence' not in src.lower(),src
# Vários contatos: salvar um novo contato não remove os demais do mesmo key.
bulk=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_radar_bulk_link_dialog')
bs=ast.get_source_segment(s,bulk)
assert 'links.pop(wa,None);links[wa]=key' in bs
assert 'if str(oldkey)==key' not in bs
assert 'ALIYVO_ORIGIN_ID = "ALIYVO-ORIGIN-20260924-2302-6F91D2C4A8E73B5C"' in s
assert 'setInterval(20000)' in s
print('CARTEIRA_SOMENTE_HISTORICO=OK')
print('RECORRENCIA_FILTRADA_PELA_CARTEIRA=OK')
print('MULTIPLOS_WHATSAPP_POR_CLIENTE=OK')
print('PAINEL_OFERECER_AGORA=OK')
print('RADAR_PRESERVADO=OK')
print('PROVENIENCIA_PRESERVADA=OK')
print('ALIYVO_V2307=OK')
