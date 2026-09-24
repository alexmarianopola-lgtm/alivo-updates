from pathlib import Path
import sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
text=main.read_text(encoding='utf-8')

def one(old,new,label):
    global text
    n=text.count(old)
    if n!=1:
        raise SystemExit(f'{label}: esperado 1, encontrado {n}')
    text=text.replace(old,new,1)

one('ALIYVO_VERSION = "0.22.93"','ALIYVO_VERSION = "0.22.94"','version')

old='''        cards=QHBoxLayout();cards.setSpacing(8)
        card_over=QLabel();card_today=QLabel();card_wait=QLabel();card_ai=QLabel()
        for c in (card_over,card_today,card_wait,card_ai):
            c.setMinimumHeight(72);c.setWordWrap(True);c.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cards.addWidget(c,1)
        lay.addLayout(cards)
'''
new='''        cards=QHBoxLayout();cards.setSpacing(8)
        # 0.22.94: estes cards agora sao botoes reais, nao apenas indicadores visuais.
        card_over=QPushButton();card_today=QPushButton();card_wait=QPushButton();card_ai=QPushButton()
        for c in (card_over,card_today,card_wait,card_ai):
            c.setMinimumHeight(72);c.setCursor(Qt.CursorShape.PointingHandCursor)
            cards.addWidget(c,1)
        lay.addLayout(cards)
'''
one(old,new,'dashboard cards clickable')

old='''            card=QWidget();card.setStyleSheet(f"QWidget{{background:{bg};border-radius:9px;}}")
            vl=QVBoxLayout(card);vl.setContentsMargins(12,8,12,8);vl.setSpacing(3)
'''
new='''            card=QWidget();card.setStyleSheet(f"QWidget{{background:{bg};border-radius:9px;}}")
            # Deixa o clique atravessar o card customizado e chegar ao QListWidgetItem.
            # Sem isso o card parece clicavel, mas bloqueia selecao/duplo clique.
            card.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True)
            vl=QVBoxLayout(card);vl.setContentsMargins(12,8,12,8);vl.setSpacing(3)
'''
one(old,new,'cards pass mouse events')

old='''            card_over.setText(f"🔴\\n{len(overdue)}\\nVENCIDOS")
            card_over.setStyleSheet("background:#FFD9DE;color:#9E1027;border-radius:10px;font-size:13px;font-weight:900;padding:7px;")
            card_today.setText(f"🟡\\n{today_count}\\nHOJE")
            card_today.setStyleSheet("background:#FFF2B7;color:#6A5600;border-radius:10px;font-size:13px;font-weight:900;padding:7px;")
            card_wait.setText(f"💬\\n{waiting_count}\\nESPERANDO")
            card_wait.setStyleSheet("background:#DDEEFF;color:#155B8A;border-radius:10px;font-size:13px;font-weight:900;padding:7px;")
            card_ai.setText(f"🤖\\n{ai_pending}\\nPENDÊNCIAS IA")
            card_ai.setStyleSheet("background:#DFF5E8;color:#176B3A;border-radius:10px;font-size:13px;font-weight:900;padding:7px;")
'''
new='''            card_over.setText(f"🔴\\n{len(overdue)}\\nVENCIDOS")
            card_over.setStyleSheet("QPushButton{background:#FFD9DE;color:#9E1027;border:1px solid #F4B7C0;border-radius:10px;font-size:13px;font-weight:900;padding:7px;} QPushButton:hover{background:#FFC9D1;}")
            card_today.setText(f"🟡\\n{today_count}\\nHOJE")
            card_today.setStyleSheet("QPushButton{background:#FFF2B7;color:#6A5600;border:1px solid #F1DE84;border-radius:10px;font-size:13px;font-weight:900;padding:7px;} QPushButton:hover{background:#FFECA0;}")
            card_wait.setText(f"💬\\n{waiting_count}\\nESPERANDO")
            card_wait.setStyleSheet("QPushButton{background:#DDEEFF;color:#155B8A;border:1px solid #BDD9F4;border-radius:10px;font-size:13px;font-weight:900;padding:7px;} QPushButton:hover{background:#CDE5FA;}")
            card_ai.setText(f"🤖\\n{ai_pending}\\nPENDÊNCIAS IA")
            card_ai.setStyleSheet("QPushButton{background:#DFF5E8;color:#176B3A;border:1px solid #BFE5CE;border-radius:10px;font-size:13px;font-weight:900;padding:7px;} QPushButton:hover{background:#CEF0DC;}")
'''
one(old,new,'dashboard hover styles')

old='''            for r in rows:
                it=QListWidgetItem();it.setData(Qt.ItemDataRole.UserRole,str(r.get('id') or ''));it.setSizeHint(QSize(100,60));lst.addItem(it);lst.setItemWidget(it,make_card(r,now))
'''
new='''            for r in rows:
                it=QListWidgetItem();it.setData(Qt.ItemDataRole.UserRole,str(r.get('id') or ''))
                client=str(r.get('client') or '').strip()
                try:has_crm=bool(client and self._crm_state_for_client(client))
                except Exception:has_crm=False
                # Cartoes com status CRM precisam de mais altura para nao cortar a proxima acao.
                it.setSizeHint(QSize(100,96 if has_crm else 64))
                lst.addItem(it);lst.setItemWidget(it,make_card(r,now))
'''
one(old,new,'dynamic reminder card height')

old='''        refresh();filt.currentIndexChanged.connect(refresh)
        bar=QHBoxLayout();add_current=QPushButton("⏰ Desta conversa");add=QPushButton("＋ Novo");edit=QPushButton("✏ Editar");complete=QPushButton("✅ Concluir");reopen=QPushButton("↩ Reabrir");delete=QPushButton("🗑 Excluir");close=QPushButton("Fechar")
'''
new='''        refresh();filt.currentIndexChanged.connect(refresh)
        # Cards-resumo agora executam acoes.
        card_over.clicked.connect(lambda:filt.setCurrentText("Vencidos"))
        card_today.clicked.connect(lambda:self._today_quick_panel(dlg))
        card_wait.clicked.connect(lambda:self._today_quick_panel(dlg))
        card_ai.clicked.connect(lambda:self._ai_crm_reminders_dialog(dlg))

        bar=QHBoxLayout();add_current=QPushButton("⏰ Desta conversa");add=QPushButton("＋ Novo");edit=QPushButton("✏ Editar");complete=QPushButton("✅ Concluir");reopen=QPushButton("↩ Reabrir");delete=QPushButton("🗑 Excluir");open_chat=QPushButton("💬 Abrir conversa");close=QPushButton("Fechar")
'''
one(old,new,'summary card actions and open chat button')

old='''        for b in (add_current,add,edit,complete,reopen,delete):bar.addWidget(b)
        bar.addStretch(1);bar.addWidget(close);lay.addLayout(bar)
'''
new='''        for b in (add_current,add,edit,complete,reopen,delete,open_chat):bar.addWidget(b)
        bar.addStretch(1);bar.addWidget(close);lay.addLayout(bar)
'''
one(old,new,'add open chat to toolbar')

old='''        def do_edit():
            rid=selected()
            if rid:self._reminder_edit(rid,dlg,refresh)
        add_current.clicked.connect(lambda:self._reminder_add_from_current(dlg,refresh));add.clicked.connect(lambda:self._reminder_add(dlg,refresh));edit.clicked.connect(do_edit);complete.clicked.connect(finish);reopen.clicked.connect(do_reopen);delete.clicked.connect(remove);close.clicked.connect(dlg.accept);lst.itemDoubleClicked.connect(lambda _it:do_edit())
'''
new='''        def do_edit():
            rid=selected()
            if rid:self._reminder_edit(rid,dlg,refresh)
        def do_open_chat():
            rid=selected()
            if not rid:return
            client=""
            for r in self._reminders:
                if str(r.get('id') or '')==rid:
                    client=str(r.get('client') or '').strip();break
            if not client:
                QMessageBox.information(dlg,"CRM","Este lembrete não está vinculado a um cliente.")
                return
            dlg.accept()
            QTimer.singleShot(120,lambda client=client:self._attendance_open_chat(client))
        add_current.clicked.connect(lambda:self._reminder_add_from_current(dlg,refresh));add.clicked.connect(lambda:self._reminder_add(dlg,refresh));edit.clicked.connect(do_edit);complete.clicked.connect(finish);reopen.clicked.connect(do_reopen);delete.clicked.connect(remove);open_chat.clicked.connect(do_open_chat);close.clicked.connect(dlg.accept);lst.itemDoubleClicked.connect(lambda _it:do_edit())
'''
one(old,new,'open selected reminder chat')

# Substitui o CRM do dia somente-texto por uma lista interativa.
start=text.index('    def _ai_crm_reminders_dialog(self,parent=None):')
end=text.index('    def _today_quick_panel(self,parent=None):',start)
old_block=text[start:end]
new_block=r'''    def _ai_crm_reminders_dialog(self,parent=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QListWidget,QListWidgetItem,QPushButton,QMessageBox
        from PyQt6.QtCore import Qt,QTimer
        import datetime,time,uuid

        dlg=QDialog(parent or self);dlg.setWindowTitle("🤖 CRM do dia — Pendências da IA");dlg.resize(900,650)
        lay=QVBoxLayout(dlg)
        title=QLabel("PENDÊNCIAS DETECTADAS PELO OBSERVADOR")
        title.setStyleSheet("font-size:18px;font-weight:900;color:#0B3349;")
        sub=QLabel("Selecione um cliente. A IA sugere o estado; você decide o que fazer.")
        sub.setStyleSheet("color:#61717F;font-size:11px;")
        lay.addWidget(title);lay.addWidget(sub)

        lst=QListWidget();lst.setSpacing(6)
        lst.setStyleSheet("QListWidget{background:#F7FAFC;border:1px solid #D7E0E7;padding:5px;} QListWidget::item{padding:10px;border-radius:7px;} QListWidget::item:selected{background:#DDEEFF;color:#0B3349;border:1px solid #76AEE0;}")
        lay.addWidget(lst,1)

        def refresh():
            lst.clear()
            rows=self._crm_states_payload(100,True) or []
            for x in rows:
                client=str(x.get("client") or "").strip()
                status=str(x.get("status") or "")
                action=str(x.get("next_action") or "")
                owner=str(x.get("owner") or "-")
                conf=str(x.get("confidence") or "-")
                it=QListWidgetItem(f"{client}\n{status}  •  responsável: {owner}  •  confiança: {conf}\nPróxima ação: {action}")
                it.setData(Qt.ItemDataRole.UserRole,client)
                it.setData(Qt.ItemDataRole.UserRole+1,dict(x))
                it.setSizeHint(it.sizeHint()+QtCore.QSize(0,28) if False else it.sizeHint())
                lst.addItem(it)
            if not rows:
                it=QListWidgetItem("Nenhuma pendência comercial detectada agora.")
                it.setFlags(Qt.ItemFlag.NoItemFlags);lst.addItem(it)

        def selected_client():
            it=lst.currentItem()
            return str(it.data(Qt.ItemDataRole.UserRole) or "").strip() if it else ""

        def open_chat():
            client=selected_client()
            if not client:return
            dlg.accept();QTimer.singleShot(120,lambda client=client:self._attendance_open_chat(client))

        def create_reminder():
            client=selected_client()
            if not client:return
            state=self._crm_state_for_client(client) or {}
            action=str(state.get("next_action") or f"Retornar para {client}")
            due=time.time()+3600
            self._reminder_add(dlg,None,force_client=client,context=str(state.get("evidence") or ""),prefill_text=action,prefill_due=due)

        def resolve_state():
            client=selected_client()
            if not client:return
            data=self._crm_states_load()
            state=data.get(client)
            if isinstance(state,dict):
                state["pending"]=False;state["status_key"]="resolvido_manual";state["status"]="Resolvido manualmente";state["owner"]="nenhum";state["next_action"]="Nenhuma ação pendente";state["updated_at"]=time.time()
                self._crm_states_save()
                try:self._diagnostic_log("crm_state_resolved_manual",client=client)
                except Exception:pass
                refresh()

        row=QHBoxLayout()
        open_btn=QPushButton("💬 Abrir WhatsApp")
        rem_btn=QPushButton("⏰ Criar lembrete")
        done_btn=QPushButton("✅ Marcar resolvido")
        ai_btn=QPushButton("🤖 Analisar CRM")
        close=QPushButton("Fechar")
        for b in (open_btn,rem_btn,done_btn,ai_btn):row.addWidget(b)
        row.addStretch(1);row.addWidget(close);lay.addLayout(row)

        open_btn.clicked.connect(open_chat)
        rem_btn.clicked.connect(create_reminder)
        done_btn.clicked.connect(resolve_state)
        lst.itemDoubleClicked.connect(lambda _it:open_chat())
        def run_ai():
            # Mantem a analise profunda disponivel em janela separada, sem transformar
            # este painel interativo em um editor de texto.
            old_txt=getattr(self,"_ai_observer_text_widget",None)
            old_status=getattr(self,"_ai_observer_status_widget",None)
            self._ai_observer_text_widget=None;self._ai_observer_status_widget=None
            self._ai_observer_analyze("crm_reminders",False)
            self._ai_observer_text_widget=old_txt;self._ai_observer_status_widget=old_status
        ai_btn.clicked.connect(run_ai)
        close.clicked.connect(dlg.accept)
        refresh();dlg.exec()

'''
# Evita dependencia de QtCore no bloco acima, removendo linha inócua.
new_block=new_block.replace('                it.setSizeHint(it.sizeHint()+QtCore.QSize(0,28) if False else it.sizeHint())\n','')
text=text[:start]+new_block+text[end:]

text=text.replace('aliyvo_version="0.22.93"','aliyvo_version="0.22.94"')
main.write_text(text,encoding='utf-8')
print('PATCH_CRM_INTERATIVO_V94=OK')
