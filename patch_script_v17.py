from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v17.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.31 - corrige foco de teclado no buscador Somaforce embutido.
# O WhatsApp usa WebView2 nativo; por isso reforçamos o foco do QWebEngineView
# quando o usuário interage com o buscador, sem criar monitoramento contínuo.

old='''        self.browser=QWebEngineView(self)\n        self.browser.setUrl(QUrl(self.URL))\n        lay.addWidget(self.browser,1)'''
if old not in text:
    raise SystemExit('Somaforce browser anchor not found')
new='''        self.browser=QWebEngineView(self)\n        self.browser.setFocusPolicy(Qt.FocusPolicy.StrongFocus)\n        self.browser.installEventFilter(self)\n        try:\n            fp=self.browser.focusProxy()\n            if fp is not None:\n                fp.setFocusPolicy(Qt.FocusPolicy.StrongFocus)\n                fp.installEventFilter(self)\n        except Exception:\n            pass\n        self.browser.setUrl(QUrl(self.URL))\n        lay.addWidget(self.browser,1)'''
text=text.replace(old,new,1)

anchor='''    def _open_external(self):\n        try:\n            QDesktopServices.openUrl(QUrl(self.URL))\n        except Exception:\n            pass\n'''
if anchor not in text:
    raise SystemExit('Somaforce external method anchor not found')
focus_code='''    def _force_browser_focus(self):\n        try:\n            self.browser.activateWindow()\n        except Exception:\n            pass\n        try:\n            self.browser.setFocus(Qt.FocusReason.MouseFocusReason)\n        except Exception:\n            try: self.browser.setFocus()\n            except Exception: pass\n        try:\n            fp=self.browser.focusProxy()\n            if fp is not None:\n                fp.setFocus(Qt.FocusReason.MouseFocusReason)\n        except Exception:\n            pass\n        try:\n            self.browser.page().runJavaScript(\n                \"try{window.focus();if(document.activeElement)document.activeElement.focus();}catch(e){}\"\n            )\n        except Exception:\n            pass\n\n    def eventFilter(self,obj,event):\n        try:\n            et=event.type()\n            if obj is self.browser or obj is self.browser.focusProxy():\n                if et in (QEvent.Type.MouseButtonPress, QEvent.Type.FocusIn):\n                    QTimer.singleShot(0,self._force_browser_focus)\n        except Exception:\n            pass\n        return super().eventFilter(obj,event)\n\n'''
text=text.replace(anchor,focus_code+anchor,1)

# Também reforça foco ao abrir o painel, mas sem roubar o teclado do WhatsApp depois.
old_method='''    def _technical_open_and_analyze(self):\n        self._open_quick_tool("technical")\n        try:\n            if hasattr(self.technical_panel,"browser") and not self.technical_panel.browser.url().isValid():\n                self.technical_panel.browser.setUrl(QUrl(self.technical_panel.URL))\n        except Exception:\n            pass'''
if old_method not in text:
    raise SystemExit('technical open method v16 not found')
new_method='''    def _technical_open_and_analyze(self):\n        self._open_quick_tool("technical")\n        try:\n            if hasattr(self.technical_panel,"browser") and not self.technical_panel.browser.url().isValid():\n                self.technical_panel.browser.setUrl(QUrl(self.technical_panel.URL))\n            if hasattr(self.technical_panel,"_force_browser_focus"):\n                QTimer.singleShot(120,self.technical_panel._force_browser_focus)\n        except Exception:\n            pass'''
text=text.replace(old_method,new_method,1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched Somaforce keyboard focus',version)
