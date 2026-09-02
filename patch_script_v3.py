from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v3.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# Preserve capture log across page navigations/reinjections.
text=text.replace('save([]); log("capture_start",{title:document.title||""});','if(!read().length){ save([]); log("capture_start",{title:document.title||""}); }')

# Start a short-lived rearm loop while diagnostic mode is active.
old='''    def _catalog_capture_start(self):\n        browser=self._get_catalog_window(False)'''
new='''    def _catalog_capture_start(self):\n        browser=self._get_catalog_window(False)\n        browser._capture_started=True\n        browser._capture_rounds=0'''
if old in text:
    text=text.replace(old,new,1)

needle='''        browser.start_network_capture(started)'''
replacement='''        browser.start_network_capture(started)\n        QTimer.singleShot(300,lambda b=browser:self._catalog_capture_keepalive(b))'''
if needle in text and '_catalog_capture_keepalive' not in text:
    text=text.replace(needle,replacement,1)

marker='''    def _catalog_capture_read(self,browser):'''
method='''    def _catalog_capture_keepalive(self,browser):\n        try:\n            if not getattr(browser,"_capture_started",False):\n                return\n            browser._capture_rounds=int(getattr(browser,"_capture_rounds",0))+1\n            if browser._capture_rounds>140:\n                browser._capture_started=False\n                return\n            # Reinstala os hooks após qualquer navegação sem apagar o histórico.\n            browser.start_network_capture()\n        except Exception:\n            pass\n        QTimer.singleShot(300,lambda b=browser:self._catalog_capture_keepalive(b))\n\n'''
if marker in text and '_catalog_capture_keepalive' not in text:
    text=text.replace(marker,method+marker,1)

# Enrich diagnostic screen with GraphQL hint if resources mention it.
oldline='''            if useful: self.plate_panel.status.setText(f"✅ Diagnóstico capturou {useful} chamada(s).")'''
newline='''            if any("gateway/graphql" in str(x) for x in lines):\n                lines.insert(4,"PISTA: endpoint GraphQL detectado: https://bff.catalogofraga.com.br/gateway/graphql")\n                self.plate_panel.capture.setPlainText("\\n".join(lines))\n            if useful: self.plate_panel.status.setText(f"✅ Diagnóstico capturou {useful} chamada(s).")'''
if oldline in text:
    text=text.replace(oldline,newline,1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched',version)
