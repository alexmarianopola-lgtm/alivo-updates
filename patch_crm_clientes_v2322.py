from pathlib import Path
import sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
s=main.read_text(encoding='utf-8')

if 'ALIYVO_VERSION = "0.23.21"' not in s:
    raise SystemExit('base 0.23.21 nao encontrada')
s=s.replace('ALIYVO_VERSION = "0.23.21"','ALIYVO_VERSION = "0.23.22"',1)
s=s.replace('aliyvo_version="0.23.21"','aliyvo_version="0.23.22"')

# Botao principal deixa de parecer apenas lembretes.
s=s.replace('self.reminder_toggle=QPushButton("⏰  Lembretes")','self.reminder_toggle=QPushButton("👥  CRM")',1)
s=s.replace('self.reminder_toggle.setText(f"⏰  Lembretes ({n})" if n else "⏰  Lembretes")','self.reminder_toggle.setText(f"👥  CRM ({n})" if n else "👥  CRM")',1)

# Cabeçalho da tela atual de lembretes vira porta de entrada do CRM.
s=s.replace(
    'crm_sub=QLabel("Lembretes, clientes esperando e oportunidades em um só lugar")',
    'crm_sub=QLabel("Clientes, compradores, histórico, retornos, lembretes e oportunidades em um só lugar")',
    1
)

old='''        today_btn=QPushButton("📌 Hoje");top.addWidget(today_btn);crm=QPushButton("🤖 Pendências da IA");top.addWidget(crm);lay.addLayout(top)'''
new='''        today_btn=QPushButton("📌 Hoje");top.addWidget(today_btn);clients_btn=QPushButton("👥 Clientes");top.addWidget(clients_btn);crm=QPushButton("🤖 Pendências da IA");top.addWidget(crm);lay.addLayout(top)'''
if old not in s: raise SystemExit('barra superior CRM nao encontrada')
s=s.replace(old,new,1)

old='''        today_btn.clicked.connect(lambda:self._today_quick_panel(dlg))
        try:crm.clicked.connect(lambda:self._ai_crm_reminders_dialog(dlg))'''
new='''        today_btn.clicked.connect(lambda:self._today_quick_panel(dlg))
        clients_btn.clicked.connect(lambda:self._crm_clients_dialog(dlg))
        try:crm.clicked.connect(lambda:self._ai_crm_reminders_dialog(dlg))'''
if old not in s: raise SystemExit('acoes CRM nao encontradas')
s=s.replace(old,new,1)

# Hoje ganha acesso direto ao cadastro de clientes.
old='''        row=QHBoxLayout();crm=QPushButton('🧭 CRM do dia');close=QPushButton('Fechar');row.addWidget(crm);row.addStretch(1);row.addWidget(close);lay.addLayout(row)
        crm.clicked.connect(lambda:self._ai_crm_reminders_dialog(dlg));close.clicked.connect(dlg.accept);dlg.exec()'''
new='''        row=QHBoxLayout();clients=QPushButton('👥 Clientes CRM');crm=QPushButton('🧭 CRM do dia');close=QPushButton('Fechar');row.addWidget(clients);row.addWidget(crm);row.addStretch(1);row.addWidget(close);lay.addLayout(row)
        clients.clicked.connect(lambda:self._crm_clients_dialog(dlg));crm.clicked.connect(lambda:self._ai_crm_reminders_dialog(dlg));close.clicked.connect(dlg.accept);dlg.exec()'''
if old not in s: raise SystemExit('rodape Hoje nao encontrado')
s=s.replace(old,new,1)

# O telefone salvo no CRM passa a ser usado para abrir o WhatsApp.
old='''        raw=str(name or "").strip()
        digits=re.sub(r"\D","",raw)
        if len(digits)>=10:
            phone=digits
        else:
            phone=""
            try:
                con=self.db();cur=con.cursor()'''
new='''        raw=str(name or "").strip()
        digits=re.sub(r"\D","",raw)
        if len(digits)>=10:
            phone=digits
        else:
            phone=""
            try:
                prof=self._crm_client_profile(raw)
                phone=re.sub(r"\D","",str(prof.get("phone") or "")) if isinstance(prof,dict) else ""
            except Exception:
                phone=""
            try:
                con=self.db();cur=con.cursor()'''
if old not in s: raise SystemExit('resolver telefone nao encontrado')
s=s.replace(old,new,1)

# Nao sobrescrever telefone CRM com vazio vindo da base.
old='''                if row: phone=re.sub(r"\D","",str(row[0] or ""))
            except Exception:
                phone=""'''
new='''                if row and not phone: phone=re.sub(r"\D","",str(row[0] or ""))
            except Exception:
                pass'''
if old not in s: raise SystemExit('fallback telefone nao encontrado')
s=s.replace(old,new,1)

anchor='''    def _crm_state_file(self):
'''
if anchor not in s: raise SystemExit('anchor CRM state nao encontrado')

methods=r'''    # ===== CRM DE CLIENTES 0.23.22 =====
    def _crm_clients_file(self):
        try: USER_DATA_DIR.mkdir(parents=True,exist_ok=True)
        except Exception: pass
        return USER_DATA_DIR/"crm_clientes.json"

    def _crm_clients_load(self,force=False):
        if not force:
            cached=getattr(self,"_crm_clients_cache",None)
            if isinstance(cached,dict):return cached
        data={"version":1,"clients":{}}
        try:
            f=self._crm_clients_file()
            if f.exists():
                x=json.loads(f.read_text(encoding="utf-8"))
                if isinstance(x,dict):
                    data.update(x)
                    if not isinstance(data.get("clients"),dict):data["clients"]={}
        except Exception:pass
        self._crm_clients_cache=data
        return data

    def _crm_clients_save(self):
        try:
            data=self._crm_clients_load()
            self._crm_clients_file().write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
            return True
        except Exception:return False

    def _crm_client_key(self,name):
        return self._crm_norm(str(name or "").strip())

    def _crm_client_find_name(self,name):
        wanted=self._crm_client_key(name)
        if not wanted:return ""
        clients=self._crm_clients_load().get("clients") or {}
        for saved in clients.keys():
            if self._crm_client_key(saved)==wanted:return str(saved)
        return ""

    def _crm_client_profile(self,name):
        saved=self._crm_client_find_name(name)
        if not saved:return {}
        x=(self._crm_clients_load().get("clients") or {}).get(saved)
        return dict(x) if isinstance(x,dict) else {}

    def _crm_current_contact_name(self):
        for value in (getattr(self,"_diagnostic_active_name",""),getattr(self,"_attendance_current_name","")):
            value=str(value or "").strip()
            if value:return value
        return ""

    def _crm_save_profile(self,profile,old_name=""):
        import time
        name=str((profile or {}).get("name") or "").strip()
        if not name:return False
        data=self._crm_clients_load();clients=data.setdefault("clients",{})
        old_saved=self._crm_client_find_name(old_name) if old_name else ""
        current=self._crm_client_profile(old_saved or name)
        merged=dict(current);merged.update(profile or {})
        merged["name"]=name;merged["updated_at"]=time.time();merged.setdefault("created_at",time.time())
        if not isinstance(merged.get("history"),list):merged["history"]=[]
        if old_saved and old_saved!=name:clients.pop(old_saved,None)
        clients[name]=merged
        ok=self._crm_clients_save()
        if old_saved and old_saved!=name:
            changed=False
            for r in getattr(self,"_reminders",[]) or []:
                if isinstance(r,dict) and self._crm_client_key(r.get("client"))==self._crm_client_key(old_saved):
                    r["client"]=name;changed=True
            if changed:
                try:self._reminder_save();self._reminder_update_button()
                except Exception:pass
        return ok

    def _crm_schedule_followup(self,client,days=1,reason=""):
        import datetime,time,uuid
        client=str(client or "").strip()
        if not client:return 0
        try:days=max(0,int(days))
        except Exception:days=1
        now=datetime.datetime.now()
        due=(now+datetime.timedelta(hours=1)) if days<=0 else (now+datetime.timedelta(days=days)).replace(hour=9,minute=0,second=0,microsecond=0)
        due_ts=due.timestamp();text=str(reason or "").strip() or f"Retornar para {client}"
        if not hasattr(self,"_reminders") or not isinstance(self._reminders,list):self._reminders=[]
        for r in self._reminders:
            if not isinstance(r,dict) or r.get("done"):continue
            if str(r.get("source") or "")!="crm_followup":continue
            if self._crm_client_key(r.get("client"))==self._crm_client_key(client):
                r["done"]=True;r["alerted"]=True
        self._reminders.append({"id":uuid.uuid4().hex,"text":text,"due_ts":due_ts,"client":client,"context":"Follow-up criado pelo cadastro CRM","done":False,"alerted":False,"created_at":time.time(),"source":"crm_followup"})
        try:self._reminder_save();self._reminder_update_button()
        except Exception:pass
        profile=self._crm_client_profile(client)
        if profile:
            profile["next_contact_ts"]=due_ts;profile["next_contact_reason"]=text
            self._crm_save_profile(profile,client)
        try:self._diagnostic_log("crm_followup_created",client=client,text=text,due_ts=due_ts)
        except Exception:pass
        return due_ts

    def _crm_followup_dialog(self,client,parent=None,refresh=None,reason=""):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QFormLayout,QLineEdit,QComboBox,QHBoxLayout,QPushButton,QMessageBox
        client=str(client or "").strip()
        if not client:
            QMessageBox.information(parent or self,"CRM","Selecione um cliente primeiro.");return
        dlg=QDialog(parent or self);dlg.setWindowTitle(f"⏰ Próximo contato — {client}");dlg.resize(520,240)
        lay=QVBoxLayout(dlg);form=QFormLayout();why=QLineEdit(str(reason or f"Retornar para {client}"));period=QComboBox()
        for label,days in (("Amanhã às 09:00",1),("Em 3 dias",3),("Em 7 dias",7),("Em 15 dias",15),("Em 30 dias",30),("Em 1 hora",0)):period.addItem(label,days)
        form.addRow("O que fazer:",why);form.addRow("Quando:",period);lay.addLayout(form)
        bar=QHBoxLayout();save=QPushButton("✅ Agendar retorno");cancel=QPushButton("Cancelar");bar.addStretch(1);bar.addWidget(save);bar.addWidget(cancel);lay.addLayout(bar)
        def do_save():
            self._crm_schedule_followup(client,period.currentData(),why.text().strip());dlg.accept()
            if callable(refresh):refresh()
        save.clicked.connect(do_save);cancel.clicked.connect(dlg.reject);dlg.exec()

    def _crm_register_contact_dialog(self,client,parent=None,refresh=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QFormLayout,QTextEdit,QComboBox,QHBoxLayout,QPushButton,QMessageBox
        import time
        client=str(client or "").strip();profile=self._crm_client_profile(client)
        if not profile:
            QMessageBox.information(parent or self,"CRM","Cadastre o cliente antes de registrar o contato.");return
        dlg=QDialog(parent or self);dlg.setWindowTitle(f"📝 Registrar contato — {client}");dlg.resize(600,390)
        lay=QVBoxLayout(dlg);form=QFormLayout();typ=QComboBox();typ.addItems(["Conversa WhatsApp","Ligação","Cotação enviada","Pós-cotação","Visita","Outro"])
        note=QTextEdit();note.setPlaceholderText("Resumo rápido: o que conversamos, o que pediu, preço, objeção, próximo passo...");note.setMaximumHeight(130)
        follow=QComboBox()
        for label,days in (("Sem retorno automático",-1),("Amanhã 09:00",1),("3 dias",3),("7 dias",7),("15 dias",15),("30 dias",30)):follow.addItem(label,days)
        form.addRow("Tipo:",typ);form.addRow("Resumo:",note);form.addRow("Próximo contato:",follow);lay.addLayout(form)
        bar=QHBoxLayout();save=QPushButton("💾 Salvar contato");cancel=QPushButton("Cancelar");bar.addStretch(1);bar.addWidget(save);bar.addWidget(cancel);lay.addLayout(bar)
        def do_save():
            txt=note.toPlainText().strip()
            if not txt:
                QMessageBox.information(dlg,"CRM","Escreva um resumo curto do contato.");return
            p=self._crm_client_profile(client);hist=p.get("history") if isinstance(p.get("history"),list) else []
            hist.append({"ts":time.time(),"type":typ.currentText(),"note":txt});p["history"]=hist[-200:];p["last_contact_ts"]=time.time();p["last_summary"]=txt
            self._crm_save_profile(p,client);days=int(follow.currentData())
            if days>=0:self._crm_schedule_followup(client,days,f"Retornar: {txt[:120]}")
            try:self._diagnostic_log("crm_contact_registered",client=client,type=typ.currentText(),text=txt[:300])
            except Exception:pass
            dlg.accept()
            if callable(refresh):refresh()
        save.clicked.connect(do_save);cancel.clicked.connect(dlg.reject);dlg.exec()

    def _crm_profile_dialog(self,parent=None,name="",on_saved=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QFormLayout,QLineEdit,QTextEdit,QHBoxLayout,QPushButton,QMessageBox
        old_name=self._crm_client_find_name(name) or str(name or "").strip();p=self._crm_client_profile(old_name)
        if not p and old_name:p={"name":old_name}
        dlg=QDialog(parent or self);dlg.setWindowTitle("👤 Cliente CRM");dlg.resize(650,520);lay=QVBoxLayout(dlg);form=QFormLayout()
        namew=QLineEdit(str(p.get("name") or old_name));phone=QLineEdit(str(p.get("phone") or ""));buyer=QLineEdit(str(p.get("buyer") or ""));role=QLineEdit(str(p.get("buyer_role") or ""));buys=QLineEdit(str(p.get("buys") or ""));brands=QLineEdit(str(p.get("brands") or ""));notes=QTextEdit(str(p.get("notes") or ""));notes.setMaximumHeight(110)
        namew.setPlaceholderText("Empresa ou nome do cliente");phone.setPlaceholderText("Telefone/WhatsApp");buyer.setPlaceholderText("Nome do comprador");role.setPlaceholderText("Ex.: compras, proprietário, mecânico");buys.setPlaceholderText("Ex.: freio, suspensão, motor");brands.setPlaceholderText("Ex.: Mercedes, Scania, Volvo")
        form.addRow("Cliente/empresa:",namew);form.addRow("Telefone:",phone);form.addRow("Comprador:",buyer);form.addRow("Função:",role);form.addRow("O que compra:",buys);form.addRow("Marcas/frota:",brands);form.addRow("Observações:",notes);lay.addLayout(form)
        bar=QHBoxLayout();save=QPushButton("💾 Salvar cliente");cancel=QPushButton("Cancelar");bar.addStretch(1);bar.addWidget(save);bar.addWidget(cancel);lay.addLayout(bar)
        def do_save():
            nm=namew.text().strip()
            if not nm:
                QMessageBox.information(dlg,"CRM","Informe o nome do cliente ou empresa.");return
            profile=dict(p);profile.update({"name":nm,"phone":phone.text().strip(),"buyer":buyer.text().strip(),"buyer_role":role.text().strip(),"buys":buys.text().strip(),"brands":brands.text().strip(),"notes":notes.toPlainText().strip()})
            if not self._crm_save_profile(profile,old_name):
                QMessageBox.warning(dlg,"CRM","Não consegui salvar o cadastro.");return
            dlg.accept()
            if callable(on_saved):on_saved(nm)
        save.clicked.connect(do_save);cancel.clicked.connect(dlg.reject);dlg.exec()

    def _crm_clients_dialog(self,parent=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QListWidget,QListWidgetItem,QTextEdit,QPushButton,QMessageBox,QSplitter,QWidget
        from PyQt6.QtCore import Qt,QTimer
        import datetime,time
        dlg=QDialog(parent or self);dlg.setWindowTitle("👥 ALIYVO CRM — Clientes");dlg.resize(1040,700);lay=QVBoxLayout(dlg)
        title=QLabel("CLIENTES CRM");title.setStyleSheet("font-size:20px;font-weight:900;color:#0B3349;");lay.addWidget(title)
        hint=QLabel("Cadastro rápido + histórico + próximo contato. Use a conversa atual para cadastrar um cliente sem redigitar o nome.");hint.setWordWrap(True);hint.setStyleSheet("color:#60717F;font-weight:600;");lay.addWidget(hint)
        search=QLineEdit();search.setPlaceholderText("Buscar cliente, comprador, produto ou marca...");lay.addWidget(search)
        split=QSplitter(Qt.Orientation.Horizontal);left=QWidget();lv=QVBoxLayout(left);lst=QListWidget();lv.addWidget(lst)
        right=QWidget();rv=QVBoxLayout(right);detail=QTextEdit();detail.setReadOnly(True);detail.setStyleSheet("font-size:12px;font-weight:600;");rv.addWidget(detail,1)
        split.addWidget(left);split.addWidget(right);split.setSizes([360,640]);lay.addWidget(split,1)

        def current_name():
            it=lst.currentItem();return str(it.data(Qt.ItemDataRole.UserRole) or "") if it else ""

        def profile_text(name):
            p=self._crm_client_profile(name)
            if not p:return "Selecione um cliente."
            def fmt_ts(v):
                try:return datetime.datetime.fromtimestamp(float(v)).strftime("%d/%m/%Y %H:%M")
                except Exception:return "-"
            hist=p.get("history") if isinstance(p.get("history"),list) else []
            lines=[
                str(p.get("name") or name),
                "",
                f"Telefone: {p.get('phone') or '-'}",
                f"Comprador: {p.get('buyer') or '-'}",
                f"Função: {p.get('buyer_role') or '-'}",
                f"O que compra: {p.get('buys') or '-'}",
                f"Marcas/frota: {p.get('brands') or '-'}",
                f"Observações: {p.get('notes') or '-'}",
                "",
                f"Último contato: {fmt_ts(p.get('last_contact_ts'))}",
                f"Resumo: {p.get('last_summary') or '-'}",
                f"Próximo contato: {fmt_ts(p.get('next_contact_ts'))}",
                f"Ação: {p.get('next_contact_reason') or '-'}",
                "",
                "HISTÓRICO RECENTE"
            ]
            for h in reversed(hist[-12:]):
                if not isinstance(h,dict):continue
                lines.append(f"{fmt_ts(h.get('ts'))} • {h.get('type') or 'Contato'}")
                lines.append("  "+str(h.get("note") or ""))
            if not hist:lines.append("Ainda não há contatos registrados.")
            return "\n".join(lines)

        def refresh(select_name=""):
            q=self._crm_norm(search.text());lst.clear();clients=self._crm_clients_load(force=True).get("clients") or {}
            rows=[]
            for name,p in clients.items():
                if not isinstance(p,dict):p={}
                hay=self._crm_norm(" ".join(str(p.get(k) or "") for k in ("name","buyer","buyer_role","buys","brands","phone")))
                if q and q not in hay:continue
                rows.append((str(name),p))
            rows.sort(key=lambda x:x[0].lower())
            target=self._crm_client_find_name(select_name) if select_name else ""
            target_row=-1
            for idx,(name,p) in enumerate(rows):
                buyer=str(p.get("buyer") or "").strip();next_ts=p.get("next_contact_ts")
                next_txt=""
                try:next_txt=" • próximo "+datetime.datetime.fromtimestamp(float(next_ts)).strftime("%d/%m")
                except Exception:pass
                it=QListWidgetItem(name+(f"\nComprador: {buyer}" if buyer else "")+next_txt);it.setData(Qt.ItemDataRole.UserRole,name);lst.addItem(it)
                if target and self._crm_client_key(name)==self._crm_client_key(target):target_row=idx
            if target_row>=0:lst.setCurrentRow(target_row)
            elif lst.count():lst.setCurrentRow(0)
            else:detail.setPlainText("Nenhum cliente cadastrado.")

        def show_detail():
            detail.setPlainText(profile_text(current_name()))

        def add_new():
            self._crm_profile_dialog(dlg,"",lambda n:refresh(n))

        def add_current():
            name=self._crm_current_contact_name()
            if not name:
                QMessageBox.information(dlg,"CRM","Abra primeiro a conversa do cliente no WhatsApp.");return
            self._crm_profile_dialog(dlg,name,lambda n:refresh(n))

        def edit():
            name=current_name()
            if name:self._crm_profile_dialog(dlg,name,lambda n:refresh(n))

        def open_chat():
            name=current_name()
            if not name:return
            dlg.accept();QTimer.singleShot(120,lambda n=name:self._attendance_open_chat(n))

        def register():
            name=current_name()
            if name:self._crm_register_contact_dialog(name,dlg,lambda:refresh(name))

        def follow():
            name=current_name()
            if name:self._crm_followup_dialog(name,dlg,lambda:refresh(name))

        bar=QHBoxLayout();newb=QPushButton("＋ Novo cliente");currentb=QPushButton("💬 Cadastrar conversa atual");openb=QPushButton("↗ Abrir WhatsApp");editb=QPushButton("✏ Editar");contactb=QPushButton("📝 Registrar contato");followb=QPushButton("⏰ Agendar retorno");close=QPushButton("Fechar")
        for b in (newb,currentb,openb,editb,contactb,followb):bar.addWidget(b)
        bar.addStretch(1);bar.addWidget(close);lay.addLayout(bar)
        search.textChanged.connect(lambda _=None:refresh());lst.currentItemChanged.connect(lambda _a,_b:show_detail());lst.itemDoubleClicked.connect(lambda _it:edit())
        newb.clicked.connect(add_new);currentb.clicked.connect(add_current);openb.clicked.connect(open_chat);editb.clicked.connect(edit);contactb.clicked.connect(register);followb.clicked.connect(follow);close.clicked.connect(dlg.accept)
        refresh(self._crm_current_contact_name());dlg.exec()

'''
s=s.replace(anchor,methods+anchor,1)

main.write_text(s,encoding='utf-8')
print('PATCH_CRM_CLIENTES_V2322=OK')
