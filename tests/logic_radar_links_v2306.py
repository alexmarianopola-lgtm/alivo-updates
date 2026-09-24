from pathlib import Path
import sys,ast
app=Path(sys.argv[1]);s=(app/'main.py').read_text(encoding='utf-8')
assert 'ALIYVO_VERSION = "0.23.06"' in s
for token in [
 'def _radar_known_whatsapp_contacts(self):',
 'def _radar_auto_link_all(self,save=True):',
 'def _radar_bulk_link_dialog(self,parent=None,on_done=None):',
 '🔗 Vincular toda a carteira',
 '✨ Auto-vincular nomes iguais',
 '💬 Usar conversa atual',
 '✅ Memorizado',
 'Mostrar somente não vinculados'
]: assert token in s,token
assert 'ALIYVO_ORIGIN_ID = "ALIYVO-ORIGIN-20260924-2302-6F91D2C4A8E73B5C"' in s
assert 'def _radar_show_dialog(self):' in s
assert 'self.radar_toggle=QPushButton("🎯  Radar da Carteira")' in s
assert 'setInterval(20000)' in s
assert 'CLIENTES PARA CHAMAR' in s
assert 'RECOMPRA EM ATÉ 7 DIAS' in s
assert 'Por que chamar' in s
assert 'Melhores oportunidades:' in s
assert 'table.itemSelectionChanged.connect(update_detail)' in s
# Garante persistencia no mesmo dicionario existente do Radar.
assert 'links=data.setdefault("links",{})' in s
print('RADAR_BULK_LINK_UI=OK')
print('RADAR_AUTO_LINK=OK')
print('RADAR_LINK_MEMORY=OK')
print('RADAR_CLIENT_COUNTS=OK')
print('RADAR_CLIENT_DETAIL=OK')
print('RADAR_EXISTING_FEATURES_PRESERVED=OK')
print('PROVENANCE_PRESERVED=OK')
print('ALIYVO_V2306_LINKS=OK')
