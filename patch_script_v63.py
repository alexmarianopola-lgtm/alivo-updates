from pathlib import Path
import sys,re,json

p=Path(sys.argv[1] if len(sys.argv)>1 else r'C:\temp\build\_app\main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v63.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"',f'ALIYVO_VERSION = "{version}"',text,count=1)
p.write_text(text,encoding='utf-8')
print('patched version',version)
