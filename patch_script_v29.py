from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v29.json').read_text(encoding='utf-8'))
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

# A fila visual sai do caminho. O botao vira Diagnostico e nasce Lembretes.
old='self.attendance_toggle=QPushButton("🧠  Atendimentos")'
if old not in text: raise SystemExit('attendance button anchor not found')
text=text.replace(old,'self.attendance_toggle=QPushButton("📊  Diagnóstico")\n        self.reminder_toggle=QPushButton("⏰  Lembretes")',1)
old='nav_lay.addWidget(self.attendance_toggle)'
if old not in text: raise SystemExit('attendance nav anchor not found')
text=text.replace(old,old+'\n        nav_lay.addWidget(self.reminder_toggle)',1)
old='self.attendance_toggle.clicked.connect(self._toggle_attendance_mode)'
if old not in text: raise SystemExit('attendance signal anchor not found')
text=text.replace(old,'self.attendance_toggle.clicked.connect(self._diagnostic_show_dialog)\n        self.reminder_toggle.clicked.connect(self._reminder_show_dialog)',1)
text=text.replace('self.attendance_toggle.setText("🧠  Atendimentos ✓")','self.attendance_toggle.setText("📊  Diagnóstico")')
text=text.replace('self.attendance_toggle.setText("🧠  Atendimentos")','self.attendance_toggle.setText("📊  Diagnóstico")')

# O modo visual volta ao painel antigo, mas o diagnostico continua silencioso.
new_boot=r'''    def _attendance_bootstrap(self):
        self._attendance_load()
        self._attendance_data["enabled"]=False
        self._attendance_save()
        self._attendance_apply_home()
        self._diagnostic_start()
        self._reminder_start()
'''
text=replace_method(text,'MainWindow','_attendance_bootstrap',new_boot)

# Registra uso das ferramentas mesmo trabalhando no painel classico.
needle='    def _open_quick_tool(self, tool):\n'
if needle not in text: raise SystemExit('quick tool method not found')
text=text.replace(needle,needle+'        try: self._diagnostic_log("tool_opened", client=getattr(self,"_diagnostic_active_name","") or "", tool=str(tool))\n        except Exception: pass\n',1)

anchor='    def _technical_open_and_analyze(self):\n'
if anchor not in text: raise SystemExit('technical anchor not found')
methods=r'''    def _diagnostic_file(self):
        try: USER_DATA_DIR.mkdir(parents=True,exist_ok=True)
        except Exception: pass
        return USER_DATA_DIR/"diagnostico_eventos.jsonl"

    def _diagnostic_log(self,event,**payload):
        try:
            import time,datetime
            row={"ts":time.time(),"time":datetime.datetime.now().isoformat(timespec="seconds"),"event":str(event)}
            for k,v in payload.items():
                if v is not None: row[str(k)]=v
            with self._diagnostic_file().open("a",encoding="utf-8") as f:
                f.write(json.dumps(row,ensure_ascii=False)+"\n")
        except Exception:
            pass

    def _diagnostic_start(self):
        self._diagnostic_busy=False
        self._diagnostic_active_name=""
        self._diagnostic_last_active=""
        self._diagnostic_signatures={}
        self._diagnostic_pending={}
        self._diagnostic_unread=set()
        self._diagnostic_timer=QTimer(self)
        self._diagnostic_timer.setInterval(3000)
        self._diagnostic_timer.timeout.connect(self._diagnostic_scan)
        self._diagnostic_timer.start()
        QTimer.singleShot(1200,self._diagnostic_scan)
        try:
            for attr,tool in (("plate_toggle","plate"),("lens_toggle","image")):
                b=getattr(self,attr,None)
                if b: b.clicked.connect(lambda _=False,t=tool:self._diagnostic_log("tool_opened",client=getattr(self,"_diagnostic_active_name","") or "",tool=t))
        except Exception:
            pass

    def _diagnostic_scan(self):
        if getattr(self,"_diagnostic_busy",False): return
        try:
            self._diagnostic_busy=True
            self.web.page().runJavaScript(self._attendance_extract_js(),self._diagnostic_scan_done)
        except Exception:
            self._diagnostic_busy=False

    def _diagnostic_scan_done(self,result):
        self._diagnostic_busy=False
        if not isinstance(result,dict) or not result.get("ok"): return
        import time
        now=time.time()
        active=result.get("active") or {}
        name=str(active.get("name") or "").strip()
        context=active.get("context") or []
        self._diagnostic_active_name=name
        if name and name!=getattr(self,"_diagnostic_last_active",""):
            self._diagnostic_log("chat_opened",client=name,previous=getattr(self,"_diagnostic_last_active","") or "")
            self._diagnostic_last_active=name
        if name and context:
            last=context[-1] if isinstance(context[-1],dict) else {}
            side=str(last.get("side") or "")
            msg=str(last.get("text") or "").strip()
            sig=(side+"|"+msg)[-1800:]
            prev=self._diagnostic_signatures.get(name)
            if prev is None:
                self._diagnostic_signatures[name]=sig
            elif sig and sig!=prev:
                self._diagnostic_signatures[name]=sig
                ev="message_customer" if side=="customer" else "message_seller" if side=="seller" else "message"
                self._diagnostic_log(ev,client=name,text=msg[:500])
                if side=="customer":
                    self._diagnostic_pending[name]=now
                elif side=="seller" and name in self._diagnostic_pending:
                    secs=max(0,int(now-float(self._diagnostic_pending.pop(name))))
                    self._diagnostic_log("response",client=name,response_seconds=secs)
        unread_now=set()
        for row in (result.get("unread") or []):
            if isinstance(row,dict):
                n=str(row.get("name") or "").strip()
                if n: unread_now.add(n)
        old=set(getattr(self,"_diagnostic_unread",set()) or set())
        if unread_now!=old:
            self._diagnostic_log("unread_snapshot",count=len(unread_now),names=sorted(unread_now)[:40],new=sorted(unread_now-old)[:20],cleared=sorted(old-unread_now)[:20])
            self._diagnostic_unread=unread_now

    def _diagnostic_read(self):
        rows=[]
        try:
            f=self._diagnostic_file()
            if not f.exists(): return rows
            for line in f.read_text(encoding="utf-8",errors="ignore").splitlines():
                try:
                    x=json.loads(line)
                    if isinstance(x,dict): rows.append(x)
                except Exception: pass
        except Exception: pass
        return rows

    def _diagnostic_summary_text(self,rows):
        import datetime,statistics
        today=datetime.date.today().isoformat()
        day=[x for x in rows if str(x.get("time") or "").startswith(today)]
        clients=set(str(x.get("client") or "") for x in day if x.get("client"))
        responses=[int(x.get("response_seconds") or 0) for x in day if x.get("event")=="response" and int(x.get("response_seconds") or 0)>=0]
        tools={}
        for x in day:
            if x.get("event")=="tool_opened":
                t=str(x.get("tool") or "outro"); tools[t]=tools.get(t,0)+1
        max_unread=max([int(x.get("count") or 0) for x in day if x.get("event")=="unread_snapshot"] or [0])
        cust=sum(1 for x in day if x.get("event")=="message_customer")
        seller=sum(1 for x in day if x.get("event")=="message_seller")
        opens=sum(1 for x in day if x.get("event")=="chat_opened")
        avg=(sum(responses)/len(responses)) if responses else 0
        med=statistics.median(responses) if responses else 0
        def fmt(s):
            s=int(s); return f"{s//60}m {s%60:02d}s" if s>=60 else f"{s}s"
        tool_line=", ".join(f"{k}: {v}" for k,v in sorted(tools.items(),key=lambda z:-z[1])) or "nenhuma registrada"
        return (f"DIAGNÓSTICO DE HOJE\n\n"
                f"Clientes observados: {len(clients)}\n"
                f"Trocas/aberturas de conversa: {opens}\n"
                f"Mensagens novas de clientes detectadas: {cust}\n"
                f"Respostas suas detectadas: {seller}\n"
                f"Maior quantidade de não lidos observada: {max_unread}\n"
                f"Tempo médio de resposta medido: {fmt(avg) if responses else 'ainda sem amostra'}\n"
                f"Mediana de resposta: {fmt(med) if responses else 'ainda sem amostra'}\n"
                f"Ferramentas usadas: {tool_line}\n\n"
                f"Eventos guardados no histórico: {len(rows)}\n\n"
                "O analisador trabalha em segundo plano. Continue usando Lido/Não lido normalmente.")

    def _diagnostic_show_dialog(self):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QTextEdit,QPushButton,QFileDialog,QMessageBox
        dlg=QDialog(self); dlg.setWindowTitle("📊 Diagnóstico do atendimento"); dlg.resize(650,520)
        lay=QVBoxLayout(dlg)
        txt=QTextEdit(); txt.setReadOnly(True); txt.setStyleSheet("font-size:12px;font-weight:600;")
        rows=self._diagnostic_read(); txt.setPlainText(self._diagnostic_summary_text(rows)); lay.addWidget(txt,1)
        bar=QHBoxLayout(); export=QPushButton("📤 Exportar diagnóstico"); close=QPushButton("Fechar")
        bar.addWidget(export); bar.addStretch(1); bar.addWidget(close); lay.addLayout(bar)
        def do_export():
            import datetime
            fn=f"ALIYVO_diagnostico_{datetime.date.today().isoformat()}.json"
            path,_=QFileDialog.getSaveFileName(dlg,"Exportar diagnóstico",fn,"Arquivo JSON (*.json)")
            if not path:return
            try:
                payload={"aliyvo_version":ALIYVO_VERSION,"exported_at":datetime.datetime.now().isoformat(timespec="seconds"),"summary":self._diagnostic_summary_text(rows),"events":rows,"attendance_snapshot":getattr(self,"_attendance_data",{})}
                Path(path).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
                QMessageBox.information(dlg,"Diagnóstico","Arquivo exportado. Você pode me enviar esse JSON para eu analisar seu fluxo de atendimento.")
            except Exception as e: QMessageBox.warning(dlg,"Diagnóstico",f"Não consegui exportar: {e}")
        export.clicked.connect(do_export); close.clicked.connect(dlg.accept); dlg.exec()

    def _reminder_file(self):
        try: USER_DATA_DIR.mkdir(parents=True,exist_ok=True)
        except Exception: pass
        return USER_DATA_DIR/"lembretes.json"

    def _reminder_load(self):
        try:
            f=self._reminder_file()
            if f.exists():
                x=json.loads(f.read_text(encoding="utf-8"))
                if isinstance(x,list): return x
        except Exception: pass
        return []

    def _reminder_save(self):
        try: self._reminder_file().write_text(json.dumps(self._reminders,ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception: pass

    def _reminder_start(self):
        self._reminders=self._reminder_load()
        self._reminder_update_button()
        self._reminder_timer=QTimer(self); self._reminder_timer.setInterval(15000)
        self._reminder_timer.timeout.connect(self._reminder_check); self._reminder_timer.start()
        QTimer.singleShot(1800,self._reminder_check)

    def _reminder_update_button(self):
        try:
            n=sum(1 for x in getattr(self,"_reminders",[]) if isinstance(x,dict) and not x.get("done"))
            self.reminder_toggle.setText(f"⏰  Lembretes ({n})" if n else "⏰  Lembretes")
        except Exception: pass

    def _reminder_show_dialog(self):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QListWidget,QListWidgetItem,QPushButton,QMessageBox
        import datetime
        dlg=QDialog(self); dlg.setWindowTitle("⏰ Lembretes do ALIYVO"); dlg.resize(650,470)
        lay=QVBoxLayout(dlg); lst=QListWidget(); lay.addWidget(lst,1)
        def refresh():
            lst.clear()
            rows=sorted([x for x in self._reminders if isinstance(x,dict)],key=lambda x:(bool(x.get("done")),float(x.get("due_ts") or 0)))
            for r in rows:
                due=datetime.datetime.fromtimestamp(float(r.get("due_ts") or 0)).strftime("%d/%m/%Y %H:%M")
                client=str(r.get("client") or "").strip(); done="✅" if r.get("done") else "⏰"
                line=f"{done} {due}  —  {r.get('text','')}"+(f"\nCliente: {client}" if client else "")
                it=QListWidgetItem(line); it.setData(Qt.ItemDataRole.UserRole,str(r.get("id") or "")); lst.addItem(it)
        refresh()
        bar=QHBoxLayout(); add=QPushButton("＋ Novo"); complete=QPushButton("✅ Concluir"); delete=QPushButton("🗑 Excluir"); close=QPushButton("Fechar")
        for b in (add,complete,delete): bar.addWidget(b)
        bar.addStretch(1); bar.addWidget(close); lay.addLayout(bar)
        def selected():
            it=lst.currentItem(); return str(it.data(Qt.ItemDataRole.UserRole) or "") if it else ""
        def finish():
            rid=selected()
            if not rid:return
            for r in self._reminders:
                if str(r.get("id") or "")==rid: r["done"]=True; break
            self._reminder_save(); self._reminder_update_button(); refresh()
        def remove():
            rid=selected()
            if not rid:return
            self._reminders=[r for r in self._reminders if str(r.get("id") or "")!=rid]
            self._reminder_save(); self._reminder_update_button(); refresh()
        add.clicked.connect(lambda:self._reminder_add(dlg,refresh)); complete.clicked.connect(finish); delete.clicked.connect(remove); close.clicked.connect(dlg.accept)
        dlg.exec()

    def _reminder_add(self,parent=None,refresh=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QFormLayout,QLineEdit,QDateTimeEdit,QCheckBox,QHBoxLayout,QPushButton,QMessageBox,QLabel
        from PyQt6.QtCore import QDateTime
        import time,uuid
        dlg=QDialog(parent or self); dlg.setWindowTitle("Novo lembrete"); dlg.resize(520,250)
        lay=QVBoxLayout(dlg); form=QFormLayout(); textw=QLineEdit(); textw.setPlaceholderText("Ex.: fechar pedido Antiqueira")
        dt=QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600)); dt.setDisplayFormat("dd/MM/yyyy HH:mm"); dt.setCalendarPopup(True)
        client=str(getattr(self,"_diagnostic_active_name","") or "").strip(); link=QCheckBox("Vincular ao cliente atual")
        link.setChecked(bool(client)); form.addRow("Lembrete:",textw); form.addRow("Data e hora:",dt)
        if client: form.addRow("Cliente atual:",QLabel(client)); form.addRow("",link)
        lay.addLayout(form); bar=QHBoxLayout(); save=QPushButton("Salvar lembrete"); cancel=QPushButton("Cancelar"); bar.addStretch(1); bar.addWidget(save); bar.addWidget(cancel); lay.addLayout(bar)
        def do_save():
            txt=textw.text().strip()
            if not txt: QMessageBox.information(dlg,"Lembrete","Digite o que você precisa lembrar."); return
            due=dt.dateTime().toSecsSinceEpoch()
            r={"id":uuid.uuid4().hex,"text":txt,"due_ts":float(due),"created_at":time.time(),"done":False,"alerted":False,"client":client if client and link.isChecked() else ""}
            self._reminders.append(r); self._reminder_save(); self._reminder_update_button(); self._diagnostic_log("reminder_created",client=r.get("client",""),text=txt,due_ts=due)
            dlg.accept()
            if callable(refresh): refresh()
        save.clicked.connect(do_save); cancel.clicked.connect(dlg.reject); dlg.exec()

    def _reminder_check(self):
        import time
        now=time.time(); changed=False
        due=[r for r in getattr(self,"_reminders",[]) if isinstance(r,dict) and not r.get("done") and not r.get("alerted") and float(r.get("due_ts") or 0)<=now]
        for r in due[:3]:
            r["alerted"]=True; changed=True
            self._reminder_save()
            try:
                self.showNormal(); self.raise_(); self.activateWindow()
            except Exception: pass
            from PyQt6.QtWidgets import QMessageBox
            box=QMessageBox(self); box.setWindowTitle("⏰ Lembrete ALIYVO"); box.setIcon(QMessageBox.Icon.Information)
            client=str(r.get("client") or "").strip(); box.setText((f"Cliente: {client}\n\n" if client else "")+str(r.get("text") or ""))
            done=box.addButton("✅ Concluir",QMessageBox.ButtonRole.AcceptRole); m15=box.addButton("Adiar 15 min",QMessageBox.ButtonRole.ActionRole); h1=box.addButton("Adiar 1 hora",QMessageBox.ButtonRole.ActionRole); box.addButton("Fechar",QMessageBox.ButtonRole.RejectRole)
            box.exec(); clicked=box.clickedButton()
            if clicked==done:
                r["done"]=True; self._diagnostic_log("reminder_done",client=client,text=r.get("text",""))
            elif clicked==m15:
                r["due_ts"]=now+900; r["alerted"]=False
            elif clicked==h1:
                r["due_ts"]=now+3600; r["alerted"]=False
            else:
                r["due_ts"]=now+900; r["alerted"]=False
            changed=True
        if changed:
            self._reminder_save(); self._reminder_update_button()

'''
text=text.replace(anchor,methods+anchor,1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched silent diagnostics + reminders',version)
