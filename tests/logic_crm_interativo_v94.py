from pathlib import Path
import sys
appdir=Path(sys.argv[1])
s=(appdir/'main.py').read_text(encoding='utf-8')
assert 'ALIYVO_VERSION = "0.22.94"' in s
assert 'card_over=QPushButton()' in s
assert 'card_today=QPushButton()' in s
assert 'card_wait=QPushButton()' in s
assert 'card_ai=QPushButton()' in s
assert 'WA_TransparentForMouseEvents' in s
assert '96 if has_crm else 64' in s
assert '💬 Abrir conversa' in s
assert 'def do_open_chat():' in s
assert 'PENDÊNCIAS DETECTADAS PELO OBSERVADOR' in s
assert '💬 Abrir WhatsApp' in s
assert '⏰ Criar lembrete' in s
assert '✅ Marcar resolvido' in s
assert 'lst.itemDoubleClicked.connect(lambda _it:open_chat())' in s
assert 'self._crm_states_save()' in s
assert 'self._diagnostic_timer=QTimer(self); self._diagnostic_timer.setInterval(20000)' in s
assert 'def _diagnostic_scan_guard_done(self,result):' in s
print('CRM_CARDS_CLICAVEIS=OK')
print('CRM_LEMBRETES_CLICAVEIS=OK')
print('CRM_IA_INTERATIVO=OK')
print('CRM_ALTURA_DINAMICA=OK')
print('WHATSAPP_TURBO_PRESERVADO=OK')
print('ALIYVO_V94_CRM_INTERATIVO=OK')
