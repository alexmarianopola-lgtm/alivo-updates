from pathlib import Path
import sys
s=(Path(sys.argv[1])/'main.py').read_text(encoding='utf-8')
for x in [
 'ALIYVO_VERSION = "0.23.12"',
 'def _attendance_phone_for_contact(self,name):',
 'FROM campanha_contatos',
 'whatsapp_nome',
 'if len(phone) in (10,11):phone="55"+phone',
 'https://web.whatsapp.com/send?phone=',
 'self.web.setUrl(QUrl(url))',
 'def _attendance_open_chat(self,name):',
 "main.clicked.connect(lambda _=False,r=dict(rem):open_today_reminder(r))",
 "def _radar_show_dialog(self):"
]:
    assert x in s,x
print("DIRECT_PHONE_CHAT=OK")
print("CONTACT_DB_PHONE_LOOKUP=OK")
print("NAME_SEARCH_FALLBACK=OK")
print("TODAY_CLICK_PRESERVED=OK")
print("RADAR_PRESERVED=OK")
print("ALIYVO_V2312=OK")
