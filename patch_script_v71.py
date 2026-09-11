from pathlib import Path
import sys,re

p=Path(sys.argv[1])
text=p.read_text(encoding='utf-8')
new_text,n=re.subn(r'ALIYVO_VERSION\s*=\s*"[^"]+"','ALIYVO_VERSION = "0.22.76"',text,count=1)
if n!=1:
    raise SystemExit('ALIYVO_VERSION nao encontrado exatamente uma vez')
p.write_text(new_text,encoding='utf-8')
print('version patched to 0.22.76')
