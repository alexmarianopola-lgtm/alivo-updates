from pathlib import Path
import sys
root=Path(sys.argv[1])
main=root/'_app'/'main.py'
s=main.read_text(encoding='utf-8')
if 'ALIYVO_VERSION = "0.23.18"' not in s:
    raise SystemExit('base 0.23.18 nao encontrada')
s=s.replace('ALIYVO_VERSION = "0.23.18"','ALIYVO_VERSION = "0.23.20"',1)
s=s.replace('aliyvo_version="0.23.18"','aliyvo_version="0.23.20"')
main.write_text(s,encoding='utf-8')
print('RESTORE_FROM_02318_TO_02320=OK')
