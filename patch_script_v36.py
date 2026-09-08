from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v36.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)


def replace_method(src,class_name,method_name,new_code):
    tree=ast.parse(src)
    cls=next((n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==class_name),None)
    if cls is None: raise SystemExit(f'class {class_name} not found')
    target=next((n for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==method_name),None)
    if target is None: raise SystemExit(f'method {class_name}.{method_name} not found')
    lines=src.splitlines(keepends=True)
    start=sum(len(x) for x in lines[:target.lineno-1]); end=sum(len(x) for x in lines[:target.end_lineno])
    if not new_code.endswith('\n'): new_code+='\n'
    return src[:start]+new_code+src[end:]

# Inicia memoria de contexto por contato e o resumo diario automatico.
new_start=r'''    def _diagnostic_start(self):
        self._diagnostic_busy=False
        self._diagnostic_active_name=""
        self._diagnostic_last_active=""
        self._diagnostic_signatures={}
        self._diagnostic_pending={}
        self._diagnostic_unread=set()
        self._diagnostic_seen_calls=set()
        self._diagnostic_groups=set(self._diagnostic_groups_load())
        self._diagnostic_last_context_by_contact={}
        try:
            for row in self._diagnostic_read()[-1800:]:
                if isinstance(row,dict) and row.get("event")=="call":
                    k=str(row.get("call_key") or "").strip()
                    if k:self._diagnostic_seen_calls.add(k)
                if isinstance(row,dict) and row.get("client") and row.get("text"):
                    self._diagnostic_last_context_by_contact[str(row.get("client"))]=str(row.get("text"))[:700]
        except Exception: pass
        self._diagnostic_timer=QTimer(self); self._diagnostic_timer.setInterval(3000)
        self._diagnostic_timer.timeout.connect(self._diagnostic_scan); self._diagnostic_timer.start()
        QTimer.singleShot(1200,self._diagnostic_scan)
        self._daily_summary_timer=QTimer(self); self._daily_summary_timer.setInterval(60000)
        self._daily_summary_timer.timeout.connect(self._diagnostic_daily_check); self._daily_summary_timer.start()
        QTimer.singleShot(5000,self._diagnostic_daily_check)
        try:
            for attr,tool in (("plate_toggle","plate"),("lens_toggle","image")):
                b=getattr(self,attr,None)
                if b:b.clicked.connect(lambda _=False,t=tool:self._diagnostic_log("tool_opened",client=getattr(self,"_diagnostic_active_name","") or "",tool=t))
        except Exception: pass
'''
text=replace_method(text,'MainWindow','_diagnostic_start',new_start)

# Guarda um contexto curto da conversa ativa para usar em lembretes e historico.
needle='        self._diagnostic_active_name=name\n'
if needle not in text: raise SystemExit('diagnostic active name anchor not found')
insert='''        self._diagnostic_active_name=name\n        if name and context:\n            try:\n                _parts=[]\n                for _m in context[-6:]:\n                    if isinstance(_m,dict):\n                        _t=str(_m.get("text") or "").strip()\n                        if _t:_parts.append(_t)\n                if _parts:self._diagnostic_last_context_by_contact[name]=" | ".join(_parts)[-900:]\n            except Exception: pass\n'''
text=text.replace(needle,insert,1)

# Metodos novos: historico por contato, resumo do dia e lembrete da conversa atual.
anchor='    def _diagnostic_show_dialog(self):\n'
if anchor not in text: raise SystemExit('diagnostic dialog anchor not found')
helpers=r'''    def _diagnostic_contact_history_text(self,name,rows):
        import datetime,statistics
        name=str(name or "").strip()
        now=datetime.datetime.now()
        groups=set(self._diagnostic_groups_load())
        if not name or name in groups:return "Selecione um contato individual."
        rel=[x for x in rows if isinstance(x,dict) and str(x.get("client") or "").strip()==name]
        def parse_dt(x):
            try:return datetime.datetime.fromisoformat(str(x.get("time") or ""))
            except Exception:return None
        def period(days):
            start=now-datetime.timedelta(days=days)
            return [x for x in rel if parse_dt(x) and parse_dt(x)>=start]
        def fmt(sec):
            sec=max(0,int(sec or 0)); h=sec//3600; m=(sec%3600)//60; s=sec%60
            if h:return f"{h}h {m:02d}m"
            if m:return f"{m}m {s:02d}s"
            return f"{s}s"
        def block(label,data):
            resp=[int(x.get("total_wait_seconds") or x.get("response_seconds") or 0) for x in data if x.get("event")=="response"]
            opens=sum(1 for x in data if x.get("event")=="chat_opened")
            cust=sum(1 for x in data if x.get("event")=="message_customer")
            seller=sum(1 for x in data if x.get("event")=="message_seller")
            calls=[x for x in data if x.get("event")=="call"]
            callsec=sum(max(0,int(x.get("duration_seconds") or 0)) for x in calls)
            intr=sum(1 for x in data if x.get("event")=="attendance_interrupted")
            rem=sum(1 for x in data if x.get("event")=="reminder_created")
            done=sum(1 for x in data if x.get("event")=="reminder_done")
            avg=(sum(resp)/len(resp)) if resp else 0
            mx=max(resp) if resp else 0
            return (f"{label}\n"
                    f"  Conversas abertas: {opens} • mensagens cliente: {cust} • suas: {seller}\n"
                    f"  Respostas medidas: {len(resp)} • média {fmt(avg) if resp else '-'} • maior {fmt(mx) if resp else '-'}\n"
                    f"  Ligações: {len(calls)} / {fmt(callsec)} • interrupções: {intr}\n"
                    f"  Lembretes criados: {rem} • concluídos: {done}")
        today=[x for x in rel if str(x.get("time") or "").startswith(now.date().isoformat())]
        recent=sorted(rel,key=lambda x:float(x.get("ts") or 0),reverse=True)[:10]
        labels={"message_customer":"Cliente","message_seller":"Você","response":"Resposta medida","call":"Ligação","chat_opened":"Conversa aberta","attendance_interrupted":"Interrompido","reminder_created":"Lembrete criado","reminder_done":"Lembrete concluído","tool_opened":"Ferramenta"}
        last=[]
        for x in recent:
            t=str(x.get("time") or "")[11:16]
            ev=labels.get(str(x.get("event") or ""),str(x.get("event") or ""))
            detail=str(x.get("text") or x.get("tool") or "").replace("\n"," ").strip()
            if len(detail)>95:detail=detail[:92]+"..."
            last.append(f"{t} • {ev}"+(f" — {detail}" if detail else ""))
        return (f"HISTÓRICO — {name}\n\n"+block("HOJE",today)+"\n\n"+block("ÚLTIMOS 7 DIAS",period(7))+"\n\n"+block("ÚLTIMOS 30 DIAS",period(30))+"\n\nÚLTIMOS EVENTOS\n"+("\n".join(last) if last else "Ainda não há eventos suficientes."))

    def _diagnostic_contact_history_dialog(self,parent=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QComboBox,QTextEdit,QPushButton,QLabel
        groups=set(self._diagnostic_groups_load()); rows=self._diagnostic_read()
        names=sorted(set(str(x.get("client") or "").strip() for x in rows if isinstance(x,dict) and x.get("client") and str(x.get("client") or "").strip() not in groups),key=str.lower)
        current=str(getattr(self,"_diagnostic_active_name","") or "").strip()
        if current and current not in groups and current not in names:names.insert(0,current)
        dlg=QDialog(parent or self); dlg.setWindowTitle("👤 Histórico por contato"); dlg.resize(720,590)
        lay=QVBoxLayout(dlg); top=QHBoxLayout(); top.addWidget(QLabel("Contato:"))
        combo=QComboBox(); combo.setEditable(True); combo.addItems(names); top.addWidget(combo,1); lay.addLayout(top)
        if current and current in names:combo.setCurrentText(current)
        txt=QTextEdit(); txt.setReadOnly(True); txt.setStyleSheet("font-size:12px;font-weight:600;"); lay.addWidget(txt,1)
        def refresh(*_):txt.setPlainText(self._diagnostic_contact_history_text(combo.currentText(),self._diagnostic_read()))
        combo.currentTextChanged.connect(refresh); refresh()
        bar=QHBoxLayout(); close=QPushButton("Fechar"); bar.addStretch(1);bar.addWidget(close);lay.addLayout(bar);close.clicked.connect(dlg.accept);dlg.exec()

    def _diagnostic_daily_summary_text(self,rows):
        import datetime,statistics
        today=datetime.date.today().isoformat(); day=[x for x in rows if isinstance(x,dict) and str(x.get("time") or "").startswith(today)]
        clients=set(str(x.get("client") or "") for x in day if x.get("client"))
        resp=[int(x.get("total_wait_seconds") or x.get("response_seconds") or 0) for x in day if x.get("event")=="response"]
        intr=sum(1 for x in day if x.get("event")=="attendance_interrupted")
        calls=[x for x in day if x.get("event")=="call"]
        callsec=sum(max(0,int(x.get("duration_seconds") or 0)) for x in calls)
        max_unread=max([int(x.get("count") or 0) for x in day if x.get("event")=="unread_snapshot"] or [0])
        over5=sum(1 for s in resp if s>300); over15=sum(1 for s in resp if s>900)
        avg=(sum(resp)/len(resp)) if resp else 0
        def fmt(sec):
            sec=max(0,int(sec or 0)); h=sec//3600;m=(sec%3600)//60;s=sec%60
            if h:return f"{h}h {m:02d}m"
            if m:return f"{m}m {s:02d}s"
            return f"{s}s"
        peak="-"
        snaps=[x for x in day if x.get("event")=="unread_snapshot"]
        if snaps:
            pk=max(snaps,key=lambda x:int(x.get("count") or 0)); peak=f"{int(pk.get('count') or 0)} não lidos às {str(pk.get('time') or '')[11:16]}"
        buckets={}
        for x in day:
            if x.get("event")!="response":continue
            hour=str(x.get("time") or "")[11:13]
            if not hour:continue
            buckets.setdefault(hour,[]).append(int(x.get("total_wait_seconds") or x.get("response_seconds") or 0))
        bottleneck="Ainda sem amostra suficiente."
        if buckets:
            hb,vals=max(buckets.items(),key=lambda kv:sum(kv[1])/max(1,len(kv[1])))
            bottleneck=f"Entre {hb}:00 e {hb}:59 a espera média foi {fmt(sum(vals)/len(vals))}."
        waiting=self._diagnostic_waiting_snapshot()
        return (f"RESUMO DO DIA — {datetime.date.today().strftime('%d/%m/%Y')}\n\n"
                f"Contatos observados: {len(clients)}\n"
                f"Respostas com tempo medido: {len(resp)}\n"
                f"Tempo médio de resposta: {fmt(avg) if resp else '-'}\n"
                f"Acima de 5 min: {over5} • acima de 15 min: {over15}\n"
                f"Atendimentos interrompidos: {intr}\n"
                f"Ligações: {len(calls)} • tempo detectado {fmt(callsec)}\n"
                f"Pico de não lidos: {peak}\n"
                f"Ainda aguardando agora: {len(waiting)}\n\n"
                f"⚠ PRINCIPAL GARGALO\n{bottleneck}")

    def _diagnostic_show_daily_summary(self,parent=None,automatic=False):
        from PyQt6.QtWidgets import QMessageBox
        groups=set(self._diagnostic_groups_load()); rows=[x for x in self._diagnostic_read() if not (isinstance(x,dict) and str(x.get("client") or "").strip() in groups)]
        box=QMessageBox(parent or self); box.setWindowTitle("📅 Resumo do dia ALIYVO"); box.setIcon(QMessageBox.Icon.Information); box.setText(self._diagnostic_daily_summary_text(rows)); box.addButton("Fechar",QMessageBox.ButtonRole.AcceptRole); box.exec()

    def _diagnostic_daily_state_file(self):
        try:USER_DATA_DIR.mkdir(parents=True,exist_ok=True)
        except Exception:pass
        return USER_DATA_DIR/"resumo_diario_estado.json"

    def _diagnostic_daily_check(self):
        import datetime
        now=datetime.datetime.now()
        if (now.hour,now.minute)<(17,55) or now.hour>=23:return
        today=now.date().isoformat(); last=""
        try:
            f=self._diagnostic_daily_state_file()
            if f.exists():last=str((json.loads(f.read_text(encoding="utf-8")) or {}).get("last_date") or "")
        except Exception:pass
        if last==today:return
        try:self._diagnostic_daily_state_file().write_text(json.dumps({"last_date":today},ensure_ascii=False),encoding="utf-8")
        except Exception:pass
        self._diagnostic_show_daily_summary(self,True)

    def _reminder_add_from_current(self,parent=None,refresh=None):
        from PyQt6.QtWidgets import QMessageBox
        name=str(getattr(self,"_diagnostic_active_name","") or "").strip(); groups=set(self._diagnostic_groups_load())
        if not name or name in groups:
            QMessageBox.information(parent or self,"Lembrete","Abra primeiro uma conversa individual no WhatsApp.");return
        context=str(getattr(self,"_diagnostic_last_context_by_contact",{}).get(name) or "").strip()
        self._reminder_add(parent,refresh,force_client=name,context=context)

'''
text=text.replace(anchor,helpers+anchor,1)

# Diagnostico com historico por contato e resumo manual.
new_diag=r'''    def _diagnostic_show_dialog(self):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QTextEdit,QPushButton,QFileDialog,QMessageBox,QLabel
        import datetime
        dlg=QDialog(self); dlg.setWindowTitle("📊 Diagnóstico do atendimento"); dlg.resize(850,700)
        lay=QVBoxLayout(dlg); info=QLabel(""); info.setStyleSheet("font-weight:700;"); lay.addWidget(info)
        txt=QTextEdit(); txt.setReadOnly(True); txt.setStyleSheet("font-size:12px;font-weight:600;"); lay.addWidget(txt,1)
        def filtered_rows():
            groups=set(self._diagnostic_groups_load()); rows=self._diagnostic_read()
            return [x for x in rows if not (isinstance(x,dict) and str(x.get("client") or "").strip() in groups)]
        def refresh():
            groups=set(self._diagnostic_groups_load()); pending=len(self._diagnostic_waiting_snapshot())
            info.setText(f"Contatos individuais • {len(groups)} grupo(s) ignorado(s) • {pending} aguardando resposta agora")
            txt.setPlainText(self._diagnostic_enhanced_text(filtered_rows()))
        refresh(); live=QTimer(dlg); live.setInterval(3000); live.timeout.connect(refresh); live.start()
        bar=QHBoxLayout(); history=QPushButton("👤 Histórico por contato"); daily=QPushButton("📅 Resumo do dia"); refresh_btn=QPushButton("↻ Atualizar"); export=QPushButton("📤 Exportar diagnóstico"); close=QPushButton("Fechar")
        for b in (history,daily,refresh_btn,export):bar.addWidget(b)
        bar.addStretch(1);bar.addWidget(close);lay.addLayout(bar)
        history.clicked.connect(lambda:self._diagnostic_contact_history_dialog(dlg)); daily.clicked.connect(lambda:self._diagnostic_show_daily_summary(dlg)); refresh_btn.clicked.connect(refresh)
        def do_export():
            fn=f"ALIYVO_diagnostico_{datetime.date.today().isoformat()}.json"; path,_=QFileDialog.getSaveFileName(dlg,"Exportar diagnóstico",fn,"Arquivo JSON (*.json)")
            if not path:return
            try:
                current=filtered_rows(); ignored=sorted(self._diagnostic_groups_load(),key=str.lower)
                payload={"aliyvo_version":ALIYVO_VERSION,"exported_at":datetime.datetime.now().isoformat(timespec="seconds"),"mode":"contatos_individuais","ignored_groups":ignored,"summary":self._diagnostic_enhanced_text(current),"daily_summary":self._diagnostic_daily_summary_text(current),"waiting_now":self._diagnostic_waiting_snapshot(),"events":current,"attendance_snapshot":getattr(self,"_attendance_data",{})}
                Path(path).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8"); QMessageBox.information(dlg,"Diagnóstico","Arquivo exportado com histórico, resumo do dia e contatos aguardando.")
            except Exception as e:QMessageBox.warning(dlg,"Diagnóstico",f"Não consegui exportar: {e}")
        export.clicked.connect(do_export);close.clicked.connect(dlg.accept);dlg.exec()
'''
text=replace_method(text,'MainWindow','_diagnostic_show_dialog',new_diag)

# Tela de lembretes ganha o atalho "Desta conversa".
new_reminders=r'''    def _reminder_show_dialog(self):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QListWidget,QListWidgetItem,QPushButton,QComboBox,QLabel
        import datetime
        dlg=QDialog(self); dlg.setWindowTitle("⏰ Lembretes do ALIYVO"); dlg.resize(720,520); lay=QVBoxLayout(dlg)
        top=QHBoxLayout();top.addWidget(QLabel("Mostrar:"));filt=QComboBox();filt.addItems(["A fazer","Concluídos","Todos","Vencidos"]);filt.setCurrentText("A fazer");top.addWidget(filt)
        counts=QLabel("");counts.setStyleSheet("font-weight:700;");top.addWidget(counts);top.addStretch(1);lay.addLayout(top)
        lst=QListWidget();lay.addWidget(lst,1)
        def refresh():
            lst.clear();now=datetime.datetime.now().timestamp();allrows=[x for x in self._reminders if isinstance(x,dict)];pending=[x for x in allrows if not x.get("done")];done_rows=[x for x in allrows if x.get("done")];overdue=[x for x in pending if float(x.get("due_ts") or 0)<now]
            counts.setText(f"A fazer: {len(pending)}   •   Concluídos: {len(done_rows)}   •   Vencidos: {len(overdue)}");mode=filt.currentText();rows=pending if mode=="A fazer" else done_rows if mode=="Concluídos" else overdue if mode=="Vencidos" else allrows
            rows=sorted(rows,key=lambda x:(bool(x.get("done")),float(x.get("due_ts") or 0)))
            for r in rows:
                due_ts=float(r.get("due_ts") or 0);due=datetime.datetime.fromtimestamp(due_ts).strftime("%d/%m/%Y %H:%M") if due_ts else "Sem data";client=str(r.get("client") or "").strip();is_done=bool(r.get("done"));is_over=(not is_done and due_ts and due_ts<now);icon="✅" if is_done else "⚠️" if is_over else "⏰";status="  [VENCIDO]" if is_over else ""
                line=f"{icon} {due}  —  {r.get('text','')}{status}"+(f"\nCliente: {client}" if client else "");it=QListWidgetItem(line);it.setData(Qt.ItemDataRole.UserRole,str(r.get("id") or ""));lst.addItem(it)
        refresh();filt.currentIndexChanged.connect(refresh)
        bar=QHBoxLayout();add_current=QPushButton("⏰ Desta conversa");add=QPushButton("＋ Novo");edit=QPushButton("✏ Editar");complete=QPushButton("✅ Concluir");reopen=QPushButton("↩ Reabrir");delete=QPushButton("🗑 Excluir");close=QPushButton("Fechar")
        for b in (add_current,add,edit,complete,reopen,delete):bar.addWidget(b)
        bar.addStretch(1);bar.addWidget(close);lay.addLayout(bar)
        def selected():
            it=lst.currentItem();return str(it.data(Qt.ItemDataRole.UserRole) or "") if it else ""
        def finish():
            rid=selected();
            if not rid:return
            for r in self._reminders:
                if str(r.get("id") or "")==rid:r["done"]=True;r["alerted"]=True;self._diagnostic_log("reminder_done",client=r.get("client",""),text=r.get("text",""));break
            self._reminder_save();self._reminder_update_button();refresh()
        def do_reopen():
            rid=selected();
            if not rid:return
            for r in self._reminders:
                if str(r.get("id") or "")==rid:r["done"]=False;r["alerted"]=False;self._diagnostic_log("reminder_reopened",client=r.get("client",""),text=r.get("text",""));break
            self._reminder_save();self._reminder_update_button();refresh()
        def remove():
            rid=selected();
            if not rid:return
            self._reminders=[r for r in self._reminders if str(r.get("id") or "")!=rid];self._reminder_save();self._reminder_update_button();refresh()
        def do_edit():
            rid=selected();
            if rid:self._reminder_edit(rid,dlg,refresh)
        add_current.clicked.connect(lambda:self._reminder_add_from_current(dlg,refresh));add.clicked.connect(lambda:self._reminder_add(dlg,refresh));edit.clicked.connect(do_edit);complete.clicked.connect(finish);reopen.clicked.connect(do_reopen);delete.clicked.connect(remove);close.clicked.connect(dlg.accept);lst.itemDoubleClicked.connect(lambda _it:do_edit());dlg.exec()
'''
text=replace_method(text,'MainWindow','_reminder_show_dialog',new_reminders)

# Novo lembrete aceita cliente/contexto predefinidos sem quebrar chamadas antigas.
new_add=r'''    def _reminder_add(self,parent=None,refresh=None,force_client=None,context=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QFormLayout,QLineEdit,QDateTimeEdit,QCheckBox,QHBoxLayout,QPushButton,QMessageBox,QLabel
        from PyQt6.QtCore import QDateTime
        import time,uuid
        dlg=QDialog(parent or self);dlg.setWindowTitle("Novo lembrete");dlg.resize(570,310);lay=QVBoxLayout(dlg);form=QFormLayout();textw=QLineEdit();textw.setPlaceholderText("Ex.: fechar pedido Antiqueira")
        dt=QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600));dt.setDisplayFormat("dd/MM/yyyy HH:mm");dt.setCalendarPopup(True)
        current=str(force_client or getattr(self,"_diagnostic_active_name","") or "").strip();link=QCheckBox("Vincular ao contato atual");link.setChecked(bool(current));form.addRow("Lembrete:",textw);form.addRow("Data e hora:",dt)
        if current:form.addRow("Contato:",QLabel(current));form.addRow("",link)
        ctx=str(context or "").strip()
        if ctx:
            lab=QLabel(ctx[-500:]);lab.setWordWrap(True);lab.setStyleSheet("color:#526777;font-size:10px;");form.addRow("Contexto salvo:",lab)
        lay.addLayout(form);bar=QHBoxLayout();save=QPushButton("Salvar lembrete");cancel=QPushButton("Cancelar");bar.addStretch(1);bar.addWidget(save);bar.addWidget(cancel);lay.addLayout(bar)
        def do_save():
            txt=textw.text().strip()
            if not txt:QMessageBox.information(dlg,"Lembrete","Digite o que você precisa lembrar.");return
            due=float(dt.dateTime().toSecsSinceEpoch());client=current if (current and link.isChecked()) else "";r={"id":uuid.uuid4().hex,"text":txt,"due_ts":due,"client":client,"context":ctx if client else "","done":False,"alerted":False,"created_at":time.time()}
            self._reminders.append(r);self._reminder_save();self._reminder_update_button();self._diagnostic_log("reminder_created",client=client,text=txt,due_ts=due);dlg.accept()
            if callable(refresh):refresh()
        save.clicked.connect(do_save);cancel.clicked.connect(dlg.reject);dlg.exec()
'''
text=replace_method(text,'MainWindow','_reminder_add',new_add)

# Alerta mostra contexto e abre a conversa do WhatsApp quando solicitado.
new_check=r'''    def _reminder_check(self):
        import time,datetime
        from PyQt6.QtWidgets import QMessageBox
        now=time.time();changed=False
        due=[r for r in getattr(self,"_reminders",[]) if isinstance(r,dict) and not r.get("done") and not r.get("alerted") and float(r.get("due_ts") or 0)<=now]
        for r in due[:3]:
            r["alerted"]=True;changed=True;client=str(r.get("client") or "").strip();ctx=str(r.get("context") or "").strip();body=(f"Cliente: {client}\n\n" if client else "")+str(r.get("text") or "")
            if ctx:body+="\n\nContexto:\n"+ctx[-600:]
            box=QMessageBox(self);box.setWindowTitle("⏰ Lembrete ALIYVO");box.setIcon(QMessageBox.Icon.Information);box.setText(body)
            done=box.addButton("✅ Concluir",QMessageBox.ButtonRole.AcceptRole);openb=box.addButton("↗ Abrir conversa",QMessageBox.ButtonRole.ActionRole) if client else None;m15=box.addButton("+15 min",QMessageBox.ButtonRole.ActionRole);h1=box.addButton("+1 hora",QMessageBox.ButtonRole.ActionRole);tom=box.addButton("Amanhã 09:00",QMessageBox.ButtonRole.ActionRole);box.addButton("Fechar",QMessageBox.ButtonRole.RejectRole)
            box.exec();clicked=box.clickedButton()
            if clicked==done:r["done"]=True;self._diagnostic_log("reminder_done",client=client,text=r.get("text",""))
            elif openb is not None and clicked==openb:
                try:self._attendance_open_chat(client)
                except Exception:pass
            elif clicked==m15:r["due_ts"]=now+900;r["alerted"]=False
            elif clicked==h1:r["due_ts"]=now+3600;r["alerted"]=False
            elif clicked==tom:
                d=datetime.datetime.now()+datetime.timedelta(days=1);d=d.replace(hour=9,minute=0,second=0,microsecond=0);r["due_ts"]=d.timestamp();r["alerted"]=False
        if changed:self._reminder_save();self._reminder_update_button()
'''
text=replace_method(text,'MainWindow','_reminder_check',new_check)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched contact history + conversation reminders + daily summary',version)
