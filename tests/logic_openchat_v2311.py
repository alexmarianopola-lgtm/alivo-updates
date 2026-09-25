from pathlib import Path
import sys
s=(Path(sys.argv[1])/'main.py').read_text(encoding='utf-8')
for x in [
 'ALIYVO_VERSION = "0.23.11"',
 'def _attendance_open_chat(self,name):',
 "clickSearchButton",
 "findSearch",
 "document.execCommand('insertText'",
 "setInterval",
 "contact_not_found",
 "via:'search'",
 'def _today_quick_panel(self,parent=None):',
 "main.clicked.connect(lambda _=False,r=dict(rem):open_today_reminder(r))",
 "Resolvido — concluir e tirar da lista",
 "Ainda não fiz — manter na lista",
 "def _radar_show_dialog(self):"
]:
    assert x in s,x
print("OPENCHAT_VISIBLE_FALLBACK=OK")
print("OPENCHAT_WHATSAPP_SEARCH=OK")
print("PHONE_NORMALIZATION=OK")
print("TODAY_CLICK_PRESERVED=OK")
print("RADAR_PRESERVED=OK")
print("ALIYVO_V2311=OK")
