import argparse, importlib.util, json, os, sys, time, traceback, types
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--appdir', required=True)
parser.add_argument('--localappdata', required=True)
parser.add_argument('--stub-webview2', action='store_true')
parser.add_argument('--events', type=int, default=20000)
args=parser.parse_args()

os.environ['LOCALAPPDATA']=args.localappdata
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu --disable-software-rasterizer')
os.environ.setdefault('QTWEBENGINE_DISABLE_SANDBOX','1')

print('STAGE 01 prepare data', flush=True)
base=Path(args.localappdata)/'ALIYVO'/'dados'
base.mkdir(parents=True,exist_ok=True)
logf=base/'diagnostico_eventos.jsonl'
now=time.time()
with logf.open('w',encoding='utf-8') as f:
    for i in range(args.events):
        row={'ts':now-i,'time':'2026-09-17T12:00:00','event':'message_customer','client':'Cliente '+str(i%300),'text':'teste '+str(i)}
        f.write(json.dumps(row,ensure_ascii=False)+'\n')

if args.stub_webview2:
    print('STAGE 02 install WebView2 stub', flush=True)
    from PyQt6.QtWidgets import QWidget
    class _Sig:
        def connect(self,*a,**k): return None
        def emit(self,*a,**k): return None
    class _Bridge:
        def __init__(self):
            self.domContentLoaded=_Sig(); self.initialization_done=_Sig()
    class DummyQtWebView2Widget(QWidget):
        def __init__(self,*a,parent=None,**k):
            super().__init__(parent); self.bridge=_Bridge(); self.is_ready=False; self._webview=None; self._stub_url=str(k.get('url') or '')
        def evaluate_js(self,code,callback=None):
            if callable(callback): callback(None)
            return None
        def load_url(self,url): self._stub_url=str(url)
        def reload(self): return None
    mod=types.ModuleType('qtwebview2'); mod.QtWebView2Widget=DummyQtWebView2Widget
    sys.modules['qtwebview2']=mod

print('STAGE 03 import main', flush=True)
appdir=Path(args.appdir)
sys.path.insert(0,str(appdir))
spec=importlib.util.spec_from_file_location('aliyvo_runtime_test',appdir/'main.py')
m=importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
except BaseException:
    print('IMPORT FAILED',flush=True); traceback.print_exc(); raise

print('STAGE 04 QApplication', flush=True)
app=m.QApplication([])
errors=[]

def fail(msg):
    errors.append(str(msg)); print('FAIL:',msg,flush=True)

print('STAGE 05 MainWindow construct', flush=True)
try:
    win=m.MainWindow(); win.show()
except BaseException:
    print('MAINWINDOW FAILED',flush=True); traceback.print_exc(); raise
print('STAGE 06 MainWindow alive', flush=True)

# Reproduce relevant startup hooks without invoking __main__.
m.QTimer.singleShot(700,m._aliyvo_install_download_hooks)
m.QTimer.singleShot(900,m._aliyvo_override_old_plate_search)
m.QTimer.singleShot(1000,m._aliyvo_clean_plate_ui)
m.QTimer.singleShot(4500,m._aliyvo_clean_plate_ui)
m.QTimer.singleShot(5000,m._aliyvo_override_old_plate_search)

def test_cache():
    print('STAGE 07 cache test',flush=True)
    try:
        rows=win._diagnostic_read()
        if len(rows)<args.events: fail('cache nao carregou historico: '+str(len(rows)))
        t=time.perf_counter()
        for _ in range(40): win._diagnostic_read()
        elapsed=time.perf_counter()-t
        print('CACHE40_SECONDS=%.6f'%elapsed,flush=True)
        if elapsed>1.5: fail('leituras cacheadas lentas %.3fs'%elapsed)
        before=len(win._diagnostic_read())
        win._diagnostic_log('stability_runtime_test',client='Teste')
        after=len(win._diagnostic_read())
        if after!=before+1: fail('novo evento nao entrou no cache')
    except BaseException:
        fail(traceback.format_exc())

def close_diag():
    try:
        for w in app.topLevelWidgets():
            if 'Diagnóstico do atendimento' in str(w.windowTitle() or ''):
                print('STAGE 09 closing diagnostic',flush=True); w.accept(); return
        fail('janela de diagnostico nao encontrada')
    except BaseException: fail(traceback.format_exc())

def test_diag():
    print('STAGE 08 open diagnostic',flush=True)
    try:
        m.QTimer.singleShot(900,close_diag)
        win._diagnostic_show_dialog()
        print('STAGE 10 diagnostic returned',flush=True)
    except BaseException: fail(traceback.format_exc())

hook_counts={}
def snap():
    hook_counts['t18']=int(getattr(m,'_aliyvo_download_hook_attempts',0) or 0)
    print('STAGE 11 hook count',hook_counts['t18'],flush=True)

def finish():
    print('STAGE 12 finish assertions',flush=True)
    try:
        if getattr(m,'_aliyvo_plate_override_timer',None) is not None: fail('timer permanente plate override criado')
        if getattr(m,'_aliyvo_plate_v24_timer',None) is not None: fail('timer permanente plate v24 criado')
        if getattr(m,'_aliyvo_plate_ui_cleaner_timer',None) is not None: fail('timer legado plate cleaner criado')
        a=hook_counts.get('t18',-1); b=int(getattr(m,'_aliyvo_download_hook_attempts',0) or 0)
        print('DOWNLOAD_HOOK_FINAL=',b,flush=True)
        if b>8: fail('download hook continuou indefinidamente')
        if a>=0 and b!=a: fail('download hook ainda aumentou depois do limite')
        # User-reported failure must not happen after dialog close.
        err_candidates=[
            Path(args.localappdata)/'ALIYVO'/'logs'/'ALIYVO_RUNTIME_ERRO.txt',
            appdir/'ALIYVO_RUNTIME_ERRO.txt',
        ]
        for err in err_candidates:
            if err.exists() and err.read_text(encoding='utf-8',errors='ignore').strip():
                fail('runtime error log criado em '+str(err)+': '+err.read_text(encoding='utf-8',errors='ignore')[:1000])
    except BaseException: fail(traceback.format_exc())
    try: win.close()
    except BaseException: pass
    app.quit()

m.QTimer.singleShot(2500,test_cache)
m.QTimer.singleShot(5500,test_diag)
m.QTimer.singleShot(18000,snap)
m.QTimer.singleShot(22000,finish)
print('STAGE 06b event loop start',flush=True)
app.exec()
print('STAGE 13 event loop ended',flush=True)
if errors:
    print('ERROR_COUNT=',len(errors),flush=True)
    for e in errors: print(e,flush=True)
    sys.exit(1)
print('RUNTIME STABILITY TEST: OK',flush=True)
