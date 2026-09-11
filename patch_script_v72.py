from pathlib import Path
import sys,re
p=Path(sys.argv[1])
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"','ALIYVO_VERSION = "0.22.77"',text,count=1)
old='QTimer.singleShot(500,self.close)'
new='QTimer.singleShot(500,QApplication.instance().quit)'
if old not in text:
    raise SystemExit('gatilho antigo de fechamento nao encontrado')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('patched 0.22.77 updater shutdown')
