from pathlib import Path
import sys
s=(Path(sys.argv[1])/'main.py').read_text(encoding='utf-8')
for x in [
 'ALIYVO_VERSION = "0.23.10"',
 "def open_today_reminder(rem):",
 "m=re.search",
 "self._attendance_open_chat(c)",
 "Clique para abrir a conversa deste cliente no WhatsApp",
 "main.setCursor(Qt.CursorShape.PointingHandCursor)",
 "main.clicked.connect(lambda _=False,r=dict(rem):open_today_reminder(r))",
 "Resolvido — concluir e tirar da lista",
 "Ainda não fiz — manter na lista",
 "def _radar_show_dialog(self):"
]:
    assert x in s,x
print("TODAY_CARD_CLICK_OPEN_CHAT=OK")
print("OLD_REMINDER_CLIENT_FALLBACK=OK")
print("TODAY_ACTIONS_PRESERVED=OK")
print("RADAR_PRESERVED=OK")
print("ALIYVO_V2310=OK")
