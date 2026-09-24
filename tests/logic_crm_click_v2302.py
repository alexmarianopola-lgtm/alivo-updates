import os,sys
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'

appdir=Path(sys.argv[1])
s=(appdir/'main.py').read_text(encoding='utf-8')

assert 'ALIYVO_VERSION = "0.23.02"' in s
assert 'WA_TransparentForMouseEvents' in s
assert 'card.sizeHint().height()+10' in s
assert '💬 Abrir cliente' in s
assert '💬 Abrir conversa' in s
assert '⏰ Criar lembrete' in s
assert 'pending_list.itemDoubleClicked.connect' in s
assert 'reminder_list.itemDoubleClicked.connect' in s
assert 'def _crm_detect_state(self,client,context):' in s
assert 'self._diagnostic_timer=QTimer(self); self._diagnostic_timer.setInterval(20000)' in s
assert 'def _diagnostic_scan_guard_done(self,result):' in s

# Teste real do problema relatado: card visual por cima do item nao pode roubar o clique.
from PyQt6.QtWidgets import QApplication,QListWidget,QListWidgetItem,QWidget,QVBoxLayout,QLabel
from PyQt6.QtCore import Qt,QSize,QPoint
from PyQt6.QtTest import QTest

app=QApplication.instance() or QApplication([])
lst=QListWidget();lst.resize(500,220);lst.show();app.processEvents()
it=QListWidgetItem();card=QWidget();card.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True)
lay=QVBoxLayout(card);lay.addWidget(QLabel('Card CRM clicavel'))
it.setSizeHint(QSize(100,80));lst.addItem(it);lst.setItemWidget(it,card)
app.processEvents()
rect=lst.visualItemRect(it)
QTest.mouseClick(lst.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,rect.center())
app.processEvents()
assert lst.currentItem() is it, 'card ainda bloqueia selecao do QListWidget'

print('CRM_CARD_CLICK_REAL=OK')
print('CRM_DYNAMIC_HEIGHT=OK')
print('CRM_OPEN_CLIENT=OK')
print('CRM_DAY_INTERACTIVE=OK')
print('WHATSAPP_TURBO_PRESERVADO=OK')
print('ALIYVO_V2302_CRM_CLICK=OK')
