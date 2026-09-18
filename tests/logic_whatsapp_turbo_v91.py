import importlib.util, os, sys, tempfile, types
from pathlib import Path

appdir=Path(sys.argv[1])
os.environ['LOCALAPPDATA']=str(Path(tempfile.gettempdir())/'aliyvo-v91-logic')
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QTWEBENGINE_DISABLE_SANDBOX']='1'

from PyQt6.QtWidgets import QWidget

class _Signal:
    def connect(self,*a,**k): return None
    def emit(self,*a,**k): return None
class _Bridge:
    def __init__(self):
        self.domContentLoaded=_Signal(); self.initialization_done=_Signal()
class DummyWebView2(QWidget):
    def __init__(self,*a,parent=None,**k):
        super().__init__(parent); self.bridge=_Bridge(); self.is_ready=False; self._webview=None
    def evaluate_js(self,*a,**k): return None
    def load_url(self,*a,**k): return None
    def reload(self): return None

mod=types.ModuleType('qtwebview2'); mod.QtWebView2Widget=DummyWebView2; sys.modules['qtwebview2']=mod

class DummyEngineView(QWidget):
    def __init__(self,*a,**k): super().__init__(k.get('parent'))
class DummyPage:
    def __init__(self,*a,**k): pass
    def chooseFiles(self,*a,**k): return []
wm=types.ModuleType('PyQt6.QtWebEngineWidgets'); wm.QWebEngineView=DummyEngineView; sys.modules['PyQt6.QtWebEngineWidgets']=wm
cm=types.ModuleType('PyQt6.QtWebEngineCore'); cm.QWebEnginePage=DummyPage; sys.modules['PyQt6.QtWebEngineCore']=cm

spec=importlib.util.spec_from_file_location('aliyvo_v91_logic',appdir/'main.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

source=(appdir/'main.py').read_text(encoding='utf-8')
assert m.ALIYVO_VERSION=='0.22.91'
assert 'self._diagnostic_timer=QTimer(self); self._diagnostic_timer.setInterval(20000)' in source
assert 'self._diagnostic_timer=QTimer(self); self._diagnostic_timer.setInterval(5000)' not in source
assert 'QTimer.singleShot(4000,self._diagnostic_scan)' in source
assert '_diagnostic_guard_script' in source
assert 'def _diagnostic_scan_guard_done(self,result):' in source
assert 'script=getattr(self,"_diagnostic_extract_script","") or self._attendance_extract_js()' in source
assert 'a.isContentEditable' in source
assert "document.visibilityState==='hidden'" in source
assert 'class WhatsAppView(QtWebView2Widget)' in source
assert 'self.web=QWebEngineView(self)' in source
assert 'WEB_RENDER_02290.jsonl' in source
assert '_aliyvo_download_hook_attempts<8' in source

class FakePage:
    def __init__(self,guard_result):
        self.guard_result=guard_result
        self.calls=[]
    def runJavaScript(self,script,callback=None):
        self.calls.append(script)
        if callback is None:return
        if len(self.calls)==1:
            callback(self.guard_result)
        else:
            callback({'ok':False})

class FakeWeb:
    def __init__(self,page): self._page=page
    def page(self): return self._page

class Host:
    pass

def host_for(guard_result):
    h=Host()
    h._diagnostic_busy=False
    h._diagnostic_guard_script='GUARD_SCRIPT'
    h._diagnostic_extract_script='CACHED_EXTRACT'
    h.web=FakeWeb(FakePage(guard_result))
    h._attendance_extract_js=lambda: (_ for _ in ()).throw(AssertionError('extrator nao deveria ser reconstruido'))
    h._diagnostic_scan=types.MethodType(m.MainWindow._diagnostic_scan,h)
    h._diagnostic_scan_guard_done=types.MethodType(m.MainWindow._diagnostic_scan_guard_done,h)
    h._diagnostic_scan_done=types.MethodType(m.MainWindow._diagnostic_scan_done,h)
    return h

# Digitando: somente o guard leve roda; o DOM pesado nao e consultado.
h=host_for({'typing':True,'hidden':False})
h._diagnostic_scan()
assert h.web._page.calls==['GUARD_SCRIPT'],h.web._page.calls
assert h._diagnostic_busy is False

# Pagina oculta: mesmo comportamento, preservando CPU.
h=host_for({'typing':False,'hidden':True})
h._diagnostic_scan()
assert h.web._page.calls==['GUARD_SCRIPT'],h.web._page.calls
assert h._diagnostic_busy is False

# Usuario ocioso: guard + extrator em cache, sem reconstruir a string grande.
h=host_for({'typing':False,'hidden':False})
h._diagnostic_scan()
assert h.web._page.calls==['GUARD_SCRIPT','CACHED_EXTRACT'],h.web._page.calls
assert h._diagnostic_busy is False

print('WHATSAPP_TURBO_GUARD=OK')
print('WHATSAPP_TURBO_CACHE=OK')
print('WHATSAPP_TURBO_INTERVAL_20S=OK')
print('ALIYVO_V91_WHATSAPP_TURBO=OK')
