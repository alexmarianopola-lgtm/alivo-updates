from pathlib import Path
import sys
s=(Path(sys.argv[1])/'main.py').read_text(encoding='utf-8')
checks=[
 'ALIYVO_VERSION = "0.23.09"',
 'def finish_today_reminder(rid):',
 'def open_today_reminder(rem):',
 'def add_today_card(rem,bg,fg):',
 "self._attendance_open_chat(c)",
 "self._reminder_save();self._reminder_update_button()",
 "Resolvido — concluir e tirar da lista",
 "Ainda não fiz — manter na lista",
 "def _radar_show_dialog(self):",
 'ALIYVO_ORIGIN_ID = "ALIYVO-ORIGIN-20260924-2302-6F91D2C4A8E73B5C"'
]
for x in checks:
    assert x in s,x
print("TODAY_OPEN_CHAT=OK")
print("TODAY_DONE=OK")
print("TODAY_KEEP=OK")
print("RADAR_PRESERVED=OK")
print("PROVENANCE_PRESERVED=OK")
print("ALIYVO_V2309=OK")
