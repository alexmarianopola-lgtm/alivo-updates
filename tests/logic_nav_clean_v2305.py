from pathlib import Path
import sys
app=Path(sys.argv[1])
s=(app/'main.py').read_text(encoding='utf-8')

assert 'ALIYVO_VERSION = "0.23.05"' in s
assert 'self.prazo_toggle=QPushButton("▣  Prazos")' in s
assert 'self.chat_toggle=QPushButton("◉  Assistente")' in s
assert 'self.nav_lens_toggle=QPushButton("🔎  Busca por imagem")' in s
assert 'self.prazo_toggle.hide()' in s
assert 'self.chat_toggle.hide()' in s
assert 'self.nav_lens_toggle.hide()' in s

# Duplicados do topo não podem mais ser adicionados ao layout.
assert 'nav_lay.addWidget(self.prazo_toggle)' not in s
assert 'nav_lay.addWidget(self.chat_toggle)' not in s
assert 'nav_lay.addWidget(self.nav_lens_toggle)' not in s

# Laterais continuam existindo.
assert 'self.quick_prazo=QPushButton("▣  Prazos")' in s
assert 'self.quick_chat=QPushButton("◉  Assistente")' in s
assert 'self.lens_toggle=QPushButton("🔎  Busca por imagem")' in s

# Demais botões principais preservados.
for token in [
  'self.campaign_toggle=QPushButton("➤  Disparo de mensagens")',
  'self.plate_toggle=QPushButton("🚚  Busca placa")',
  'self.attendance_toggle=QPushButton("📊  Diagnóstico")',
  'self.reminder_toggle=QPushButton("⏰  Lembretes")',
  'self.radar_toggle=QPushButton("🎯  Radar da Carteira")',
  'self.ponto_toggle=QPushButton("🕒  Ponto")'
]:
    assert token in s, token

assert 'ALIYVO_ORIGIN_ID = "ALIYVO-ORIGIN-20260924-2302-6F91D2C4A8E73B5C"' in s
assert 'def _radar_show_dialog(self):' in s
assert 'setInterval(20000)' in s

print('TOPO_SEM_PRAZOS=OK')
print('TOPO_SEM_ASSISTENTE=OK')
print('TOPO_SEM_BUSCA_IMAGEM=OK')
print('BOTOES_LATERAIS_PRESERVADOS=OK')
print('RADAR_PRESERVADO=OK')
print('PROVENIENCIA_PRESERVADA=OK')
print('ALIYVO_V2305_NAV_CLEAN=OK')
