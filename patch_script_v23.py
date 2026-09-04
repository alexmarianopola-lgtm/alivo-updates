from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v23.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.37 - fluxo limpo de busca por placa:
# 1) remove o botao lateral duplicado criado nas versoes antigas;
# 2) o botao Busca placa abre um dialogo proprio com campo de placa;
# 3) somente depois de validar a placa abre o app Android e inicia a automacao ADB.

if 'class AliyvoPlateLookupDialog(QDialog):' not in text:
    main_block=re.search(r'(?m)^if\s+__name__\s*==\s*["\']__main__["\']\s*:',text)
    if not main_block:
        raise SystemExit('main block not found')

    code=r'''

# -----------------------------------------------------------------------------
# ALIYVO - Dialogo simples de placa/chassi
# -----------------------------------------------------------------------------
class AliyvoPlateLookupDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Busca por placa")
        self.setModal(True)
        self.setMinimumWidth(430)
        self.setStyleSheet("""
            QDialog{background:#F8FAFC;color:#0F172A;}
            QLabel{color:#0F172A;background:transparent;}
            QLineEdit{background:#FFFFFF;color:#0F172A;border:1px solid #94A3B8;border-radius:7px;padding:11px;font-size:18px;font-weight:700;}
            QPushButton{background:#0A2236;color:#F8FAFC;border:1px solid #173B52;border-radius:7px;padding:10px;font-weight:700;}
            QPushButton:hover{border-color:#20E983;background:#0D303B;}
        """)
        lay=QVBoxLayout(self)
        lay.setContentsMargins(18,18,18,18)
        lay.setSpacing(10)

        title=QLabel("🚚 Buscar chassi pela placa")
        title.setStyleSheet("font-size:18px;font-weight:800;color:#073B4C;")
        lay.addWidget(title)

        info=QLabel("Digite a placa. O ALIYVO vai abrir o app Android, fazer a consulta e tentar copiar o chassi automaticamente.")
        info.setWordWrap(True)
        info.setStyleSheet("color:#475569;font-size:11px;")
        lay.addWidget(info)

        self.plate=QLineEdit()
        self.plate.setPlaceholderText("Ex.: IVP1C22")
        self.plate.setMaxLength(8)
        self.plate.returnPressed.connect(self._search)
        lay.addWidget(self.plate)

        self.status=QLabel("")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color:#B45309;font-size:10px;font-weight:700;")
        lay.addWidget(self.status)

        row=QHBoxLayout()
        self.cancel_btn=QPushButton("Fechar")
        self.search_btn=QPushButton("🔎 Consultar chassi")
        self.cancel_btn.clicked.connect(self.reject)
        self.search_btn.clicked.connect(self._search)
        row.addStretch(1)
        row.addWidget(self.cancel_btn)
        row.addWidget(self.search_btn)
        lay.addLayout(row)

        QTimer.singleShot(80,self.plate.setFocus)

    def _search(self):
        compact=re.sub(r"[^A-Z0-9]","",str(self.plate.text() or "").upper())
        # Padrao brasileiro: 3 letras + 4 posicoes alfanumericas, aceitando antiga e Mercosul.
        if not re.fullmatch(r"[A-Z]{3}[0-9][A-Z0-9][0-9]{2}",compact):
            self.status.setText("Digite uma placa valida, por exemplo IVP1C22 ou ABC1D23.")
            self.plate.setFocus()
            self.plate.selectAll()
            return
        try:
            QApplication.clipboard().setText(compact)
        except Exception:
            pass
        self.accept()
        try:
            _aliyvo_open_plate_lookup_app(self.parentWidget())
        except Exception:
            pass
        try:
            _aliyvo_start_android_plate_automation(compact,self.parentWidget())
        except Exception as e:
            try:
                QMessageBox.information(self.parentWidget(),"Busca por placa","O app foi aberto e a placa ficou copiada. A automacao nao iniciou: "+str(e)[:160])
            except Exception:
                pass


def _aliyvo_show_plate_dialog(parent=None):
    try:
        dlg=AliyvoPlateLookupDialog(parent)
        dlg.exec()
    except Exception as e:
        try: QMessageBox.warning(parent,"Busca por placa","Nao consegui abrir a busca por placa: "+str(e)[:180])
        except Exception: pass


_aliyvo_plate_ui_cleaner_timer=None

def _aliyvo_clean_plate_ui():
    """Remove o launcher lateral duplicado e liga o Busca placa principal ao novo dialogo."""
    global _aliyvo_plate_ui_cleaner_timer
    try:
        app=QApplication.instance()
        if not app: return
        for w in app.allWidgets():
            try:
                if not isinstance(w,QPushButton):
                    continue
                obj=str(w.objectName() or "")
                label=str(w.text() or "").strip().lower()

                # Botao que foi adicionado artificialmente na lateral em v0.22.32.
                if obj=="aliyvoPlateLookupButton":
                    w.hide()
                    w.setEnabled(False)
                    continue

                # Qualquer botao principal/toolbar chamado Busca placa recebe o novo dialogo.
                normalized=re.sub(r"[^a-z]","",label)
                if normalized in ("buscaplaca","buscarplaca"):
                    if not bool(w.property("ALIYVO_PLATE_DIALOG_V23")):
                        try: w.clicked.disconnect()
                        except Exception: pass
                        w.clicked.connect(lambda checked=False,b=w:_aliyvo_show_plate_dialog(b.window()))
                        w.setProperty("ALIYVO_PLATE_DIALOG_V23",True)
                        try: w.setToolTip("Digite a placa e consulte o chassi pelo app Android")
                        except Exception: pass
            except Exception:
                pass
    except Exception:
        pass

    try:
        if _aliyvo_plate_ui_cleaner_timer is None:
            _aliyvo_plate_ui_cleaner_timer=QTimer()
            _aliyvo_plate_ui_cleaner_timer.setInterval(1200)
            _aliyvo_plate_ui_cleaner_timer.timeout.connect(_aliyvo_clean_plate_ui)
            _aliyvo_plate_ui_cleaner_timer.start()
    except Exception:
        pass

'''
    text=text[:main_block.start()]+code+text[main_block.start():]

    m=re.search(r'(?m)^(?P<indent>[ \t]*)(?P<var>[A-Za-z_]\w*)\s*=\s*QApplication\s*\([^\n]*\)\s*$',text)
    if not m:
        raise SystemExit('QApplication creation not found')
    indent=m.group('indent'); pos=m.end()
    text=text[:pos]+'\n'+indent+'QTimer.singleShot(1000, _aliyvo_clean_plate_ui)'+text[pos:]

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched clean plate dialog',version)
