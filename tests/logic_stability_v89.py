import importlib.util, json, os, sys, tempfile, time, types, traceback
from pathlib import Path

appdir=Path(sys.argv[1])
os.environ['LOCALAPPDATA']=str(Path(tempfile.gettempdir())/'aliyvo-v89-logic')
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QTWEBENGINE_DISABLE_SANDBOX']='1'

# O runner do GitHub nao suporta o WebView2 nativo. Para testar a logica Qt que
# estamos alterando, substituimos apenas os dois navegadores por widgets neutros.
from PyQt6.QtWidgets import QWidget, QApplication, QDialog
from PyQt6.QtCore import QTimer, QEventLoop

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

spec=importlib.util.spec_from_file_location('aliyvo_v89_logic',appdir/'main.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
assert m.ALIYVO_VERSION=='0.22.89'
source=(appdir/'main.py').read_text(encoding='utf-8')

# Gate estatico: os loops antigos que varriam todos os widgets nao podem voltar.
for bad in (
    '_aliyvo_plate_override_timer=QTimer()',
    '_aliyvo_plate_ui_cleaner_timer=QTimer()',
    '_aliyvo_plate_v24_timer=QTimer()',
    'QTimer.singleShot(2000, _aliyvo_install_download_hooks)\n        except Exception',
):
    assert bad not in source, bad
assert 'self._diagnostic_timer=QTimer(self); self._diagnostic_timer.setInterval(5000)' in source
assert 'self._diagnostic_backup_timer=QTimer(self); self._diagnostic_backup_timer.setInterval(600000)' in source
assert '_aliyvo_download_hook_attempts<8' in source

# Testa o cache do historico com um arquivo razoavelmente grande.
base=m.USER_DATA_DIR; base.mkdir(parents=True,exist_ok=True)
f=base/'diagnostico_eventos.jsonl'
now=time.time()
with f.open('w',encoding='utf-8') as out:
    for i in range(20000):
        out.write(json.dumps({'ts':now-i,'time':'2026-09-17T12:00:00','event':'message_customer','client':f'C{i%250}','text':f'msg {i}'},ensure_ascii=False)+'\n')

class CacheHost: pass
h=CacheHost(); h._diagnostic_cache_rows=None
h._diagnostic_file=types.MethodType(m.MainWindow._diagnostic_file,h)
h._diagnostic_read=types.MethodType(m.MainWindow._diagnostic_read,h)
h._diagnostic_log=types.MethodType(m.MainWindow._diagnostic_log,h)
rows=h._diagnostic_read(); assert len(rows)==20000, len(rows)
t0=time.perf_counter()
for _ in range(50): h._diagnostic_read()
elapsed=time.perf_counter()-t0
print('CACHE_50_READS_SECONDS=',elapsed,flush=True)
assert elapsed < 1.0, elapsed
before=len(h._diagnostic_read()); h._diagnostic_log('logic_test',client='Teste'); after=len(h._diagnostic_read())
assert after==before+1,(before,after)

# Reproduz exatamente a classe do erro enviado pelo usuario: fecha o dialogo,
# espera alem do intervalo do refresh e falha se qualquer slot usar widget destruido.
app=QApplication.instance() or QApplication([])
uncaught=[]
old_hook=sys.excepthook
def hook(tp,val,tb):
    uncaught.append(''.join(traceback.format_exception(tp,val,tb)))
sys.excepthook=hook

class DialogHost(QWidget):
    def _diagnostic_groups_load(self): return []
    def _diagnostic_waiting_snapshot(self): return []
    def _diagnostic_read(self): return []
    def _diagnostic_whatsapp_overview_text(self): return 'PANORAMA TESTE'
    def _diagnostic_enhanced_text(self,rows): return 'DIAGNOSTICO TESTE'

dh=DialogHost()
def close_diag():
    for w in app.topLevelWidgets():
        try:
            if isinstance(w,QDialog) and 'Diagnóstico do atendimento' in str(w.windowTitle()):
                w.accept(); return
        except Exception: pass
QTimer.singleShot(250,close_diag)
m.MainWindow._diagnostic_show_dialog(dh)
# O refresh da nova versao e 5 s. Espera mais que isso depois da destruicao.
loop=QEventLoop(); QTimer.singleShot(6200,loop.quit); loop.exec()
sys.excepthook=old_hook
if uncaught:
    raise AssertionError('Excecao apos fechar diagnostico: '+'\n'.join(uncaught))
print('DIAGNOSTIC_CLOSE_TIMER_TEST=OK',flush=True)
print('ALIYVO_V89_LOGIC_STABILITY=OK',flush=True)
