from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v10.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# Marca o canal gratuito desde já para permitir licenciamento futuro sem refazer a arquitetura.
if 'ALIYVO_PLAN = ' not in text:
    vm=re.search(r'(?m)^ALIYVO_VERSION\s*=.*$',text)
    if vm:
        text=text[:vm.end()]+'\nALIYVO_PLAN = "BETA_FREE"'+text[vm.end():]

# Imports isolados para o módulo de feedback. Duplicidade com imports existentes é inofensiva.
imports='''\nfrom PyQt6.QtWidgets import QDialog, QComboBox, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QMessageBox, QApplication\nfrom PyQt6.QtCore import QTimer\n'''
if 'class AliyvoFeedbackDialog(QDialog):' not in text:
    # insere imports depois do primeiro bloco de imports
    pos=0
    for mm in re.finditer(r'(?m)^(?:from\s+\S+\s+import\s+.+|import\s+.+)$',text):
        pos=mm.end()
        if pos>3000: break
    text=text[:pos]+imports+text[pos:]

    feedback_code=r'''

# -----------------------------------------------------------------------------
# ALIYVO BETA - Feedback voluntário
# Não envia conversa do WhatsApp, nome do cliente, telefone, cookies ou credenciais.
# Envia apenas versão, plano, ID anônimo da instalação, Windows, categoria e texto.
# -----------------------------------------------------------------------------
ALIYVO_FEEDBACK_TOPIC = "aliyvo-feedback-e1494dc4feb783399bebb12316120cda"


def _aliyvo_feedback_install_id():
    try:
        base=globals().get("USER_DATA_DIR")
        if base:
            folder=Path(base)
        else:
            import os as _os
            folder=Path(_os.environ.get("LOCALAPPDATA") or Path.home())/"ALIYVO"/"dados"
        folder.mkdir(parents=True,exist_ok=True)
        f=folder/"install_id.txt"
        if f.exists():
            value=f.read_text(encoding="utf-8").strip()
            if value: return value[:40]
        import uuid as _uuid
        value=_uuid.uuid4().hex[:16]
        f.write_text(value,encoding="utf-8")
        return value
    except Exception:
        return "anonimo"


class AliyvoFeedbackDialog(QDialog):
    def __init__(self,parent=None,preset_category=None,preset_text=""):
        super().__init__(parent)
        self.setWindowTitle("Enviar observação — ALIYVO Beta Grátis")
        self.resize(520,420)
        self.setStyleSheet("""
          QDialog{background:#F8FAFC;color:#0F172A;}
          QLabel{color:#0F172A;}
          QTextEdit,QComboBox{background:white;color:#0F172A;border:1px solid #CBD5E1;border-radius:6px;padding:6px;}
          QPushButton{background:#0A2236;color:white;border:1px solid #173B52;border-radius:6px;padding:9px;font-weight:700;}
          QPushButton:hover{border-color:#20E983;background:#0D303B;}
        """)
        lay=QVBoxLayout(self)
        title=QLabel("💬 Ajude a melhorar o ALIYVO")
        title.setStyleSheet("font-size:18px;font-weight:800;color:#073B4C;")
        lay.addWidget(title)
        info=QLabel("Escreva o que aconteceu ou o que deveria ter aparecido. Por privacidade, o ALIYVO não envia sua conversa do WhatsApp automaticamente.")
        info.setWordWrap(True)
        info.setStyleSheet("color:#475569;")
        lay.addWidget(info)
        lay.addWidget(QLabel("Tipo da observação"))
        self.category=QComboBox()
        options=["Sugestão","Erro","Busca/peça incorreta","Peça não encontrada","WhatsApp/ligação","Atualização/download","Outro"]
        self.category.addItems(options)
        if preset_category in options:
            self.category.setCurrentText(preset_category)
        lay.addWidget(self.category)
        lay.addWidget(QLabel("Observação"))
        self.message=QTextEdit()
        self.message.setPlaceholderText("Ex.: cliente pediu calço de mola 8x20. O correto era Soma 6387, mas o painel mostrou outras molas.")
        if preset_text: self.message.setPlainText(str(preset_text))
        lay.addWidget(self.message,1)
        self.meta=QLabel(f"Será enviado: ALIYVO {globals().get('ALIYVO_VERSION','')} • Beta Grátis • ID anônimo da instalação • versão do Windows.")
        self.meta.setWordWrap(True)
        self.meta.setStyleSheet("font-size:10px;color:#64748B;")
        lay.addWidget(self.meta)
        self.status=QLabel("")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        row=QHBoxLayout()
        self.copy_btn=QPushButton("📋 Copiar")
        self.send_btn=QPushButton("📨 Enviar observação")
        self.cancel_btn=QPushButton("Fechar")
        self.copy_btn.clicked.connect(self.copy_feedback)
        self.send_btn.clicked.connect(self.send_feedback)
        self.cancel_btn.clicked.connect(self.reject)
        row.addWidget(self.copy_btn); row.addStretch(1); row.addWidget(self.cancel_btn); row.addWidget(self.send_btn)
        lay.addLayout(row)

    def _payload_text(self):
        import platform as _platform
        from datetime import datetime as _datetime
        msg=self.message.toPlainText().strip()
        return "\n".join([
            "ALIYVO BETA - OBSERVACAO",
            "Categoria: "+self.category.currentText(),
            "Versao: "+str(globals().get("ALIYVO_VERSION","")),
            "Plano: "+str(globals().get("ALIYVO_PLAN","BETA_FREE")),
            "Instalacao: "+_aliyvo_feedback_install_id(),
            "Windows: "+str(_platform.system())+" "+str(_platform.release()),
            "Data: "+_datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "",
            "OBSERVACAO:",
            msg,
        ])

    def copy_feedback(self):
        try:
            QApplication.clipboard().setText(self._payload_text())
            self.status.setText("✅ Observação copiada. Você pode colar no WhatsApp se precisar.")
        except Exception as e:
            self.status.setText("Não consegui copiar: "+str(e))

    def send_feedback(self):
        msg=self.message.toPlainText().strip()
        if len(msg)<3:
            QMessageBox.information(self,"Observação","Escreva uma observação antes de enviar.")
            return
        self.send_btn.setEnabled(False)
        self.status.setText("Enviando...")
        QApplication.processEvents()
        try:
            import urllib.request as _ur
            data=self._payload_text().encode("utf-8")
            req=_ur.Request(
                "https://ntfy.sh/"+ALIYVO_FEEDBACK_TOPIC,
                data=data,
                method="POST",
                headers={
                    "Content-Type":"text/plain; charset=utf-8",
                    "Title":"ALIYVO Beta - Feedback",
                    "Tags":"speech_balloon",
                    "User-Agent":"ALIYVO-Beta/"+str(globals().get("ALIYVO_VERSION","")),
                },
            )
            with _ur.urlopen(req,timeout=7) as resp:
                _=resp.read(512)
            self.status.setText("✅ Observação enviada. Obrigado por ajudar a melhorar o ALIYVO.")
            self.message.clear()
        except Exception as e:
            self.status.setText("⚠ Não consegui enviar agora. Clique em Copiar e envie manualmente. Erro: "+str(e)[:160])
        finally:
            self.send_btn.setEnabled(True)


def _aliyvo_open_feedback(parent=None,preset_category=None,preset_text=""):
    try:
        dlg=AliyvoFeedbackDialog(parent,preset_category,preset_text)
        dlg.exec()
    except Exception as e:
        try: QMessageBox.warning(parent,"ALIYVO", "Não consegui abrir as observações: "+str(e))
        except Exception: pass


_aliyvo_feedback_install_attempts=0

def _aliyvo_install_feedback_button():
    """Instala uma única ação na lateral, sem qualquer monitoramento do WhatsApp."""
    global _aliyvo_feedback_install_attempts
    _aliyvo_feedback_install_attempts+=1
    try:
        app=QApplication.instance()
        if not app: return
        # Não duplica em reaberturas/trocas de painel.
        for w in app.allWidgets():
            try:
                if isinstance(w,QPushButton) and w.objectName()=="aliyvoFeedbackButton":
                    return
            except Exception: pass
        target=None
        for w in app.allWidgets():
            try:
                if isinstance(w,QPushButton) and "atualiza" in str(w.text() or "").lower():
                    target=w; break
            except Exception: pass
        if target is not None and target.parentWidget() is not None:
            parent=target.parentWidget(); layout=parent.layout()
            if layout is not None:
                btn=QPushButton("💬 Enviar observação",parent)
                btn.setObjectName("aliyvoFeedbackButton")
                try: btn.setStyleSheet(target.styleSheet())
                except Exception: pass
                try: btn.setMinimumHeight(target.minimumHeight())
                except Exception: pass
                btn.clicked.connect(lambda checked=False,p=parent:_aliyvo_open_feedback(p))
                inserted=False
                if hasattr(layout,"insertWidget"):
                    for i in range(layout.count()):
                        item=layout.itemAt(i)
                        if item and item.widget() is target:
                            layout.insertWidget(i+1,btn); inserted=True; break
                if not inserted:
                    try: layout.addWidget(btn); inserted=True
                    except Exception: pass
                if inserted: return
    except Exception:
        pass
    if _aliyvo_feedback_install_attempts<8:
        QTimer.singleShot(1000,_aliyvo_install_feedback_button)

'''
    main_block=re.search(r'(?m)^if\s+__name__\s*==\s*["\']__main__["\']\s*:',text)
    if main_block:
        text=text[:main_block.start()]+feedback_code+text[main_block.start():]
    else:
        raise SystemExit('main block not found for feedback code')

    # agenda instalação do botão logo após QApplication ser criado
    m=re.search(r'(?m)^(?P<indent>\s*)(?P<var>[A-Za-z_]\w*)\s*=\s*QApplication\s*\([^\n]*\)\s*$',text)
    if not m:
        raise SystemExit('QApplication creation not found for feedback button')
    pos=m.end(); indent=m.group('indent')
    text=text[:pos]+'\n'+indent+'QTimer.singleShot(1200, _aliyvo_install_feedback_button)'+text[pos:]

# Botão específico no Assistente Técnico para corrigir busca errada.
if 'aliyvoTechnicalFeedbackButton' not in text:
    old='''        lay.addWidget(warn)'''
    new='''        lay.addWidget(warn)\n\n        self.feedback_btn=QPushButton("👎 Informar resultado errado / sugestão")\n        self.feedback_btn.setObjectName("aliyvoTechnicalFeedbackButton")\n        self.feedback_btn.clicked.connect(lambda: _aliyvo_open_feedback(self,"Busca/peça incorreta","O que apareceu:\\n\\nO correto deveria ser:\\n"))\n        lay.addWidget(self.feedback_btn)'''
    if old not in text:
        raise SystemExit('technical warning anchor not found')
    text=text.replace(old,new,1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched ALIYVO Beta feedback',version)
