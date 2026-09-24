from pathlib import Path
import sys

appdir=Path(sys.argv[1])
s=(appdir/'main.py').read_text(encoding='utf-8')

assert 'ALIYVO_VERSION = "0.22.93"' in s
assert '📊 ALIYVO CRM — Lembretes e Oportunidades' in s
assert 'ALIYVO CRM' in s
assert 'VENCIDOS' in s
assert 'HOJE' in s
assert 'ESPERANDO' in s
assert 'PENDÊNCIAS IA' in s
assert '🤖 Pendências da IA' in s
assert 'CRM: {st}' in s
assert 'Próxima ação: {action}' in s
assert 'self._crm_state_for_client(client)' in s
assert 'self._crm_states_payload(100,True)' in s

# Mantém o CRM assistido e o WhatsApp Turbo da versão anterior.
assert 'def _crm_detect_state(self,client,context):' in s
assert 'def _crm_update_state_from_context(self,client,context):' in s
assert 'self._diagnostic_timer=QTimer(self); self._diagnostic_timer.setInterval(20000)' in s
assert 'def _diagnostic_scan_guard_done(self,result):' in s
assert 'class WhatsAppView(QtWebView2Widget)' in s

print('CRM_VISUAL_DASHBOARD=OK')
print('CRM_STATUS_NOS_CARTOES=OK')
print('CRM_PENDENCIAS_IA_VISIVEL=OK')
print('WHATSAPP_TURBO_PRESERVADO=OK')
print('ALIYVO_V93_CRM_VISUAL=OK')
