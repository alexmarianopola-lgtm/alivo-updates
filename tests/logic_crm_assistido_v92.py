import importlib.util, os, sys, tempfile, types
from pathlib import Path

appdir=Path(sys.argv[1])
os.environ['LOCALAPPDATA']=str(Path(tempfile.gettempdir())/'aliyvo-v92-crm-test')
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

spec=importlib.util.spec_from_file_location('aliyvo_v92_logic',appdir/'main.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
source=(appdir/'main.py').read_text(encoding='utf-8')

assert m.ALIYVO_VERSION=='0.22.92'
assert 'def _crm_detect_state(self,client,context):' in source
assert 'def _crm_update_state_from_context(self,client,context):' in source
assert 'commercial_state' in source and 'commercial_pending' in source
assert 'PENDÊNCIAS DETECTADAS PELO OBSERVADOR' in source
assert 'SITUAÇÃO CRM' in source
assert 'self._crm_update_state_from_context(name,context)' in source

# Garantia de desempenho: o novo CRM nao cria timer nem nova leitura do DOM.
a=source.index('    def _crm_state_file(self):')
b=source.index('    def _smart_reminder_parse_message(self,message,client):',a)
crm_segment=source[a:b]
assert 'QTimer' not in crm_segment
assert 'runJavaScript' not in crm_segment
assert 'setInterval' not in crm_segment

# WhatsApp Turbo 0.22.91 continua preservado.
assert 'self._diagnostic_timer=QTimer(self); self._diagnostic_timer.setInterval(20000)' in source
assert 'def _diagnostic_scan_guard_done(self,result):' in source
assert 'a.isContentEditable' in source
assert "document.visibilityState==='hidden'" in source
assert 'class WhatsAppView(QtWebView2Widget)' in source
assert 'self.web=QWebEngineView(self)' in source

class Host:
    pass
h=Host()
h._crm_norm=types.MethodType(m.MainWindow._crm_norm,h)
h._crm_detect_state=types.MethodType(m.MainWindow._crm_detect_state,h)

def detect(rows):
    return h._crm_detect_state('Cliente Teste',rows)

x=detect([{'side':'customer','text':'Bom dia, quanto fica esse rolamento?'}])
assert x['status_key']=='cliente_aguarda_resposta',x
assert x['pending'] is True and x['owner']=='vendedor',x

x=detect([
    {'side':'customer','text':'Quanto fica esse kit?'},
    {'side':'seller','text':'Fica 580,00 e prazo 28 dias.'},
])
assert x['status_key']=='cotacao_enviada',x
assert x['owner']=='cliente',x

x=detect([
    {'side':'seller','text':'Consigo fazer 580,00.'},
    {'side':'customer','text':'Vou ver aqui e te aviso.'},
])
assert x['status_key']=='aguardando_cliente',x
assert x['confidence']=='alta',x

x=detect([{'side':'seller','text':'Me passa a placa ou chassi para eu conferir.'}])
assert x['status_key']=='aguardando_informacao',x
assert x['owner']=='cliente',x

x=detect([{'side':'customer','text':'Pode separar pra mim.'}])
assert x['status_key']=='possivel_fechamento',x
assert x['owner']=='vendedor',x

x=detect([{'side':'seller','text':'Esse não temos no estoque.'}])
assert x['status_key']=='sem_produto',x
assert x['owner']=='vendedor',x

x=detect([{'side':'customer','text':'Obrigado!'}])
assert x['status_key']=='sem_pendencia',x
assert x['pending'] is False,x

print('CRM_STATUS_COMERCIAL=OK')
print('CRM_PROXIMA_ACAO=OK')
print('CRM_PENDENCIA=OK')
print('CRM_SEM_NOVO_SCANNER=OK')
print('WHATSAPP_TURBO_PRESERVADO=OK')
print('ALIYVO_V92_CRM_ASSISTIDO=OK')
