from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v11.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# Limpa textos antigos visíveis do protótipo antes da distribuição.
text=text.replace('QLabel("COPILOTO SOMAFORCE")','QLabel("ALIYVO — Assistente Comercial")')
text=text.replace('tabs.addTab(tab2, "Base Somaforce")','tabs.addTab(tab2, "Base Soma")')

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('version and commercial branding updated',version)
