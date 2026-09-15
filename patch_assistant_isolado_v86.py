from pathlib import Path
import re, sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
text=main.read_text(encoding='utf-8')

text,n=re.subn(r'ALIYVO_VERSION\s*=\s*["\']0\.22\.85["\']','ALIYVO_VERSION = "0.22.86"',text,count=1)
if n!=1:
    raise SystemExit(f'Versao 0.22.85 nao encontrada exatamente; ocorrencias={n}')

start=text.find('class ChatGPTWebView(QtWebView2Widget):')
end=text.find('class ChatGPTPanel(QWidget):', start)
if start<0 or end<0:
    raise SystemExit('Classe ChatGPTWebView/ChatGPTPanel nao encontrada')
text=text[:start]+text[end:]

old='''        self.web=ChatGPTWebView()\n'''
new='''        self.web=QWebEngineView(self)\n\n        try:\n            self.web.page().profile().downloadRequested.connect(self._handle_download)\n        except Exception:\n            pass\n'''
if old not in text:
    raise SystemExit('Criacao ChatGPTWebView nao encontrada')
text=text.replace(old,new,1)

old_back='''        try:\n            if hasattr(web,"go_back") and web.go_back():\n                self.status.setText("Voltando...")\n            else:\n                self._go_home()\n        except Exception:\n            self._go_home()\n'''
new_back='''        try:\n            if web.history().canGoBack():\n                web.back()\n                self.status.setText("Voltando...")\n            else:\n                self._go_home()\n        except Exception:\n            self._go_home()\n'''
if old_back not in text:
    raise SystemExit('Bloco voltar WebView2 nao encontrado')
text=text.replace(old_back,new_back,1)

main.write_text(text,encoding='utf-8')
print('patched 0.22.86: Assistente voltou a QWebEngine e ficou isolado do WhatsApp WebView2')
