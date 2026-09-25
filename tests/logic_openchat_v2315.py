from pathlib import Path
import sys
s=(Path(sys.argv[1])/"main.py").read_text(encoding="utf-8")
for x in [
 'ALIYVO_VERSION = "0.23.15"',
 'self._attendance_open_chat(client)',
 'QTimer.singleShot(300,dlg.accept)',
 'def _attendance_open_chat_name_result(self,name):',
 'open_chat_name_stage2',
 'result_not_found'
]:
    assert x in s,x
a=s.index('self._attendance_open_chat(client)')
b=s.index('QTimer.singleShot(300,dlg.accept)',a)
assert a<b
print('OPEN_BEFORE_CLOSE=OK')
print('NAME_SECOND_STAGE_CLICK=OK')
print('ALIYVO_V2315=OK')
