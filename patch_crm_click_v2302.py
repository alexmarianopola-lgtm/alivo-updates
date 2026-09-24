from pathlib import Path
import subprocess,sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
text=main.read_text(encoding='utf-8')

if 'ALIYVO_VERSION = "0.23.01"' not in text:
    raise SystemExit('base esperada 0.23.01 nao encontrada')

# Reaplica as duas camadas de CRM ja validadas sobre a linha 0.23.01.
# O truque de versao serve apenas para reutilizar patches deterministas;
# o pacote final volta para a linha 0.23.x.
text=text.replace('ALIYVO_VERSION = "0.23.01"','ALIYVO_VERSION = "0.22.91"',1)
main.write_text(text,encoding='utf-8')

repo=Path(__file__).resolve().parent
subprocess.check_call([sys.executable,str(repo/'patch_crm_assistido_v92.py'),str(root)])
subprocess.check_call([sys.executable,str(repo/'patch_crm_visual_v93.py'),str(root)])

text=main.read_text(encoding='utf-8')
text=text.replace('ALIYVO_VERSION = "0.22.93"','ALIYVO_VERSION = "0.23.02"',1)
text=text.replace('aliyvo_version="0.22.93"','aliyvo_version="0.23.02"')
text=text.replace('aliyvo_version="0.23.01"','aliyvo_version="0.23.02"')

def one(old,new,label):
    global text
    n=text.count(old)
    if n!=1:
        raise SystemExit(f'{label}: esperado 1, encontrado {n}')
    text=text.replace(old,new,1)

# 1) O card visual nao pode roubar o clique do QListWidget.
old='''            card=QWidget();card.setStyleSheet(f"QWidget{{background:{bg};border-radius:9px;}}")
            vl=QVBoxLayout(card);vl.setContentsMargins(12,8,12,8);vl.setSpacing(3)
'''
new='''            card=QWidget();card.setStyleSheet(f"QWidget{{background:{bg};border-radius:9px;}}")
            # O card e apenas a camada visual. O clique deve chegar ao item da lista.
            card.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True)
            vl=QVBoxLayout(card);vl.setContentsMargins(12,8,12,8);vl.setSpacing(3)
'''
one(old,new,'card click-through')

# 2) Altura do item acompanha o conteudo do card, evitando CRM cortado.
old='''            for r in rows:
                it=QListWidgetItem();it.setData(Qt.ItemDataRole.UserRole,str(r.get('id') or ''));it.setSizeHint(QSize(100,60));lst.addItem(it);lst.setItemWidget(it,make_card(r,now))
'''
new='''            for r in rows:
                it=QListWidgetItem();it.setData(Qt.ItemDataRole.UserRole,str(r.get('id') or ''))
                card=make_card(r,now)
                it.setSizeHint(QSize(100,max(70,card.sizeHint().height()+10)))
                lst.addItem(it);lst.setItemWidget(it,card)
'''
one(old,new,'dynamic card height')

# 3) Barra de acoes ganha abertura direta do cliente selecionado.
old='''        bar=QHBoxLayout();add_current=QPushButton("⏰ Desta conversa");add=QPushButton("＋ Novo");edit=QPushButton("✏ Editar");complete=QPushButton("✅ Concluir");reopen=QPushButton("↩ Reabrir");delete=QPushButton("🗑 Excluir");close=QPushButton("Fechar")
        for b in (add_current,add,edit,complete,reopen,delete):bar.addWidget(b)
'''
new='''        bar=QHBoxLayout();add_current=QPushButton("⏰ Desta conversa");add=QPushButton("＋ Novo");open_client=QPushButton("💬 Abrir cliente");edit=QPushButton("✏ Editar");complete=QPushButton("✅ Concluir");reopen=QPushButton("↩ Reabrir");delete=QPushButton("🗑 Excluir");close=QPushButton("Fechar")
        for b in (add_current,add,open_client,edit,complete,reopen,delete):bar.addWidget(b)
'''
one(old,new,'open client button')

old='''        def do_edit():
            rid=selected()
            if rid:self._reminder_edit(rid,dlg,refresh)
        add_current.clicked.connect(lambda:self._reminder_add_from_current(dlg,refresh));add.clicked.connect(lambda:self._reminder_add(dlg,refresh));edit.clicked.connect(do_edit);complete.clicked.connect(finish);reopen.clicked.connect(do_reopen);delete.clicked.connect(remove);close.clicked.connect(dlg.accept);lst.itemDoubleClicked.connect(lambda _it:do_edit())
'''
new='''        def do_edit():
            rid=selected()
            if rid:self._reminder_edit(rid,dlg,refresh)
        def do_open_client():
            rid=selected()
            if not rid:return
            client=""
            for r in self._reminders:
                if isinstance(r,dict) and str(r.get('id') or '')==rid:
                    client=str(r.get('client') or '').strip();break
            if not client:
                QMessageBox.information(dlg,"CRM","Este lembrete não está vinculado a um cliente.");return
            dlg.accept()
            QTimer.singleShot(120,lambda c=client:self._attendance_open_chat(c))
        add_current.clicked.connect(lambda:self._reminder_add_from_current(dlg,refresh));add.clicked.connect(lambda:self._reminder_add(dlg,refresh));open_client.clicked.connect(do_open_client);edit.clicked.connect(do_edit);complete.clicked.connect(finish);reopen.clicked.connect(do_reopen);delete.clicked.connect(remove);close.clicked.connect(dlg.accept);lst.itemDoubleClicked.connect(lambda _it:do_edit())
'''
one(old,new,'open client action')

# 4) CRM do dia deixa de ser texto morto e vira painel interativo.
start=text.index('    def _ai_crm_reminders_dialog(self,parent=None):')
end=text.index('    def _today_quick_panel(self,parent=None):',start)
old_method=text[start:end]
new_method='''    def _ai_crm_reminders_dialog(self,parent=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QPlainTextEdit,QPushButton,QHBoxLayout,QLabel,QListWidget,QListWidgetItem,QMessageBox
        dlg=QDialog(parent or self);dlg.setWindowTitle("🧭 CRM do dia — IA + Lembretes");dlg.resize(860,690)
        lay=QVBoxLayout(dlg)
        status=QLabel("Selecione uma pendência para abrir a conversa ou criar um lembrete. A IA não envia nada sozinha.")
        status.setWordWrap(True);status.setStyleSheet("font-weight:700;color:#425466;padding:4px;");lay.addWidget(status)

        active=str(getattr(self,"_diagnostic_active_name","") or "").strip()
        state=self._crm_state_for_client(active) if active else {}
        current=QLabel()
        current.setWordWrap(True)
        current.setStyleSheet("background:#EDF6FF;color:#174A70;border-radius:8px;padding:9px;font-weight:800;")
        if active and state:
            current.setText(f"CONVERSA ATUAL: {active}\n{state.get('status') or '-'} → {state.get('next_action') or '-'}")
        elif active:current.setText(f"CONVERSA ATUAL: {active} — ainda sem classificação comercial.")
        else:current.setText("CONVERSA ATUAL: abra um cliente no WhatsApp para ver o estado comercial.")
        lay.addWidget(current)

        lay.addWidget(QLabel("🤖 PENDÊNCIAS DETECTADAS PELO OBSERVADOR"))
        pending_list=QListWidget();pending_list.setSpacing(4);pending_list.setMinimumHeight(180)
        live=self._crm_states_payload(30,True)
        for x in live:
            client=str(x.get('client') or '').strip()
            item=QListWidgetItem(f"{client}  •  {x.get('status') or '-'}\n→ {x.get('next_action') or '-'}")
            item.setData(Qt.ItemDataRole.UserRole,client)
            item.setData(Qt.ItemDataRole.UserRole+1,str(x.get('evidence') or ''))
            pending_list.addItem(item)
        if not live:
            item=QListWidgetItem("Nenhuma pendência comercial detectada nos últimos 7 dias.");item.setFlags(Qt.ItemFlag.NoItemFlags);pending_list.addItem(item)
        lay.addWidget(pending_list,1)

        lay.addWidget(QLabel("⏰ LEMBRETES ABERTOS"))
        reminder_list=QListWidget();reminder_list.setSpacing(3);reminder_list.setMinimumHeight(120)
        rem=self._crm_open_reminders_payload()
        for r in rem[:30]:
            client=str(r.get('client') or '').strip()
            prefix="⚠ " if r.get("overdue") else "• "
            item=QListWidgetItem(prefix+f"{r.get('due')}  •  {client or 'sem cliente'} — {r.get('text')}")
            item.setData(Qt.ItemDataRole.UserRole,client)
            item.setData(Qt.ItemDataRole.UserRole+1,str(r.get('context') or ''))
            reminder_list.addItem(item)
        if not rem:
            item=QListWidgetItem("Nenhum lembrete aberto.");item.setFlags(Qt.ItemFlag.NoItemFlags);reminder_list.addItem(item)
        lay.addWidget(reminder_list,1)

        ai_output=QPlainTextEdit();ai_output.setReadOnly(True);ai_output.setMaximumHeight(170)
        ai_output.setPlaceholderText("A análise da IA aparecerá aqui quando você clicar em Analisar meu CRM.")
        lay.addWidget(ai_output)

        def selected_payload():
            it=pending_list.currentItem()
            if it and str(it.data(Qt.ItemDataRole.UserRole) or '').strip():
                return str(it.data(Qt.ItemDataRole.UserRole) or '').strip(),str(it.data(Qt.ItemDataRole.UserRole+1) or '')
            it=reminder_list.currentItem()
            if it and str(it.data(Qt.ItemDataRole.UserRole) or '').strip():
                return str(it.data(Qt.ItemDataRole.UserRole) or '').strip(),str(it.data(Qt.ItemDataRole.UserRole+1) or '')
            return "",""

        def select_pending(_cur,_prev):
            if _cur is not None:reminder_list.clearSelection()
        def select_reminder(_cur,_prev):
            if _cur is not None:pending_list.clearSelection()
        pending_list.currentItemChanged.connect(select_pending)
        reminder_list.currentItemChanged.connect(select_reminder)

        def open_selected():
            client,_ctx=selected_payload()
            if not client:
                QMessageBox.information(dlg,"CRM","Selecione uma pendência vinculada a um cliente.");return
            dlg.accept()
            QTimer.singleShot(120,lambda c=client:self._attendance_open_chat(c))

        def remind_selected():
            client,ctx=selected_payload()
            if not client:
                QMessageBox.information(dlg,"CRM","Selecione uma pendência vinculada a um cliente.");return
            st=self._crm_state_for_client(client) or {}
            title=str(st.get('next_action') or f"Retornar para {client}")
            evidence=str(st.get('evidence') or ctx or '')
            self._reminder_add(dlg,None,force_client=client,context=evidence,prefill_text=title)

        row=QHBoxLayout()
        open_btn=QPushButton("💬 Abrir conversa");remind_btn=QPushButton("⏰ Criar lembrete");an=QPushButton("🤖 Analisar meu CRM");close=QPushButton("Fechar")
        row.addWidget(open_btn);row.addWidget(remind_btn);row.addWidget(an);row.addStretch(1);row.addWidget(close);lay.addLayout(row)

        def run():
            self._ai_observer_text_widget=ai_output;self._ai_observer_status_widget=status;self._ai_observer_analyze("crm_reminders",False)
        open_btn.clicked.connect(open_selected);remind_btn.clicked.connect(remind_selected);an.clicked.connect(run);close.clicked.connect(dlg.accept)
        pending_list.itemDoubleClicked.connect(lambda _it:open_selected())
        reminder_list.itemDoubleClicked.connect(lambda _it:open_selected())
        dlg.finished.connect(lambda _=0:self._ai_observer_dialog_closed(ai_output,status));dlg.exec()

'''
text=text[:start]+new_method+text[end:]

main.write_text(text,encoding='utf-8')
print('PATCH_CRM_CLICK_V2302=OK')
