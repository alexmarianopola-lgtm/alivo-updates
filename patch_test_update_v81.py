from pathlib import Path
import re, sys
root = Path(sys.argv[1])
main = root / '_app' / 'main.py'
text = main.read_text(encoding='utf-8')
text2, n = re.subn(r'ALIYVO_VERSION\s*=\s*["\']0\.22\.80["\']', 'ALIYVO_VERSION = "0.22.81"', text, count=1)
if n != 1:
    raise SystemExit(f'Nao encontrei exatamente a versao 0.22.80 em {main}; ocorrencias={n}')
main.write_text(text2, encoding='utf-8')
print('patched test version 0.22.81')
