from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v33.json').read_text(encoding='utf-8'))
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

new_reminders=r'''    def _reminder_show_dialog(self):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QListWidget,QListWidgetItem,QPushButton,QComboBox,QLabel
        import datetime
        dlg=QDialog(self); dlg.setWindowTitle("⏰ Lembretes do ALIYVO"); dlg.resize(700,500)
        lay=QVBoxLayout(dlg)

        top=QHBoxLayout()
        top.addWidget(QLabel("Mostrar:"))
        filt=QComboBox(); filt.addItems(["A fazer","Concluídos","Todos","Vencidos"]); filt.setCurrentText("A fazer")
        top.addWidget(filt)
        counts=QLabel(""); counts.setStyleSheet("font-weight:700;")
        top.addWidget(counts); top.addStretch(1); lay.addLayout(top)

        lst=QListWidget(); lay.addWidget(lst,1)
        def refresh():
            lst.clear()
            now=datetime.datetime.now().timestamp()
            allrows=[x for x in self._reminders if isinstance(x,dict)]
            pending=[x for x in allrows if not x.get("done")]
            done_rows=[x for x in allrows if x.get("done")]
            overdue=[x for x in pending if float(x.get("due_ts") or 0)<now]
            counts.setText(f"A fazer: {len(pending)}   •   Concluídos: {len(done_rows)}   •   Vencidos: {len(overdue)}")
            mode=filt.currentText()
            if mode=="A fazer": rows=pending
            elif mode=="Concluídos": rows=done_rows
            elif mode=="Vencidos": rows=overdue
            else: rows=allrows
            rows=sorted(rows,key=lambda x:(bool(x.get("done")),float(x.get("due_ts") or 0)))
            for r in rows:
                due_ts=float(r.get("due_ts") or 0)
                due=datetime.datetime.fromtimestamp(due_ts).strftime("%d/%m/%Y %H:%M") if due_ts else "Sem data"
                client=str(r.get("client") or "").strip()
                is_done=bool(r.get("done")); is_over=(not is_done and due_ts and due_ts<now)
                icon="✅" if is_done else "⚠️" if is_over else "⏰"
                status="  [VENCIDO]" if is_over else ""
                line=f"{icon} {due}  —  {r.get('text','')}{status}"+(f"\nCliente: {client}" if client else "")
                it=QListWidgetItem(line); it.setData(Qt.ItemDataRole.UserRole,str(r.get("id") or "")); lst.addItem(it)
        refresh(); filt.currentIndexChanged.connect(refresh)

        bar=QHBoxLayout(); add=QPushButton("＋ Novo"); edit=QPushButton("✏ Editar"); complete=QPushButton("✅ Concluir"); reopen=QPushButton("↩ Reabrir"); delete=QPushButton("🗑 Excluir"); close=QPushButton("Fechar")
        for b in (add,edit,complete,reopen,delete): bar.addWidget(b)
        bar.addStretch(1); bar.addWidget(close); lay.addLayout(bar)

        def selected():
            it=lst.currentItem(); return str(it.data(Qt.ItemDataRole.UserRole) or "") if it else ""
        def finish():
            rid=selected()
            if not rid:return
            for r in self._reminders:
                if str(r.get("id") or "")==rid:
                    r["done"]=True; r["alerted"]=True
                    try:self._diagnostic_log("reminder_done",client=r.get("client",""),text=r.get("text",""))
                    except Exception:pass
                    break
            self._reminder_save(); self._reminder_update_button(); refresh()
        def do_reopen():
            rid=selected()
            if not rid:return
            for r in self._reminders:
                if str(r.get("id") or "")==rid:
                    r["done"]=False; r["alerted"]=False
                    try:self._diagnostic_log("reminder_reopened",client=r.get("client",""),text=r.get("text",""))
                    except Exception:pass
                    break
            self._reminder_save(); self._reminder_update_button(); refresh()
        def remove():
            rid=selected()
            if not rid:return
            self._reminders=[r for r in self._reminders if str(r.get("id") or "")!=rid]
            self._reminder_save(); self._reminder_update_button(); refresh()
        def do_edit():
            rid=selected()
            if rid:self._reminder_edit(rid,dlg,refresh)
        add.clicked.connect(lambda:self._reminder_add(dlg,refresh)); edit.clicked.connect(do_edit); complete.clicked.connect(finish); reopen.clicked.connect(do_reopen); delete.clicked.connect(remove); close.clicked.connect(dlg.accept)
        lst.itemDoubleClicked.connect(lambda _it:do_edit())
        dlg.exec()
'''
text=replace_method(text,'MainWindow','_reminder_show_dialog',new_reminders)

# Classificacao simples das conversas para limpar as metricas do diagnostico.
anchor='    def _diagnostic_show_dialog(self):\n'
if anchor not in text: raise SystemExit('diagnostic dialog anchor not found')
helpers=r'''    def _contact_categories_file(self):
        try: USER_DATA_DIR.mkdir(parents=True,exist_ok=True)
        except Exception: pass
        return USER_DATA_DIR/"categorias_contatos.json"

    def _contact_categories_load(self):
        try:
            f=self._contact_categories_file()
            if f.exists():
                x=json.loads(f.read_text(encoding="utf-8"))
                if isinstance(x,dict): return x
        except Exception: pass
        return {}

    def _contact_categories_save(self,data):
        try:self._contact_categories_file().write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception:pass

    def _contact_category(self,name):
        name=str(name or "").strip()
        if not name:return ""
        return str(self._contact_categories_load().get(name) or "").strip()

    def _contact_classify_current(self,parent=None,on_done=None):
        from PyQt6.QtWidgets import QInputDialog,QMessageBox
        name=str(getattr(self,"_diagnostic_active_name","") or "").strip()
        if not name:
            QMessageBox.information(parent or self,"Classificar","Abra primeiro a conversa que deseja classificar no WhatsApp."); return
        opts=["Cliente","Interno","Pessoal","Grupo"]
        current=self._contact_category(name); idx=opts.index(current) if current in opts else 0
        val,ok=QInputDialog.getItem(parent or self,"Classificar conversa",f"{name}\n\nTipo:",opts,idx,False)
        if not ok:return
        data=self._contact_categories_load(); data[name]=str(val); self._contact_categories_save(data)
        try:self._diagnostic_log("contact_classified",client=name,category=str(val))
        except Exception:pass
        if callable(on_done):on_done()

'''
text=text.replace(anchor,helpers+anchor,1)

new_diag=r'''    def _diagnostic_show_dialog(self):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QTextEdit,QPushButton,QFileDialog,QMessageBox,QComboBox,QLabel
        dlg=QDialog(self); dlg.setWindowTitle("📊 Diagnóstico do atendimento"); dlg.resize(760,600)
        lay=QVBoxLayout(dlg)
        top=QHBoxLayout(); top.addWidget(QLabel("Analisar:"))
        scope=QComboBox(); scope.addItems(["Todos","Somente clientes","Excluir Interno/Pessoal/Grupo"]); top.addWidget(scope)
        classify=QPushButton("🏷 Classificar conversa atual"); top.addWidget(classify); top.addStretch(1); lay.addLayout(top)
        txt=QTextEdit(); txt.setReadOnly(True); txt.setStyleSheet("font-size:12px;font-weight:600;"); lay.addWidget(txt,1)
        rows=self._diagnostic_read()
        def filtered_rows():
            cats=self._contact_categories_load(); mode=scope.currentText()
            if mode=="Todos":return rows
            out=[]
            for x in rows:
                if not isinstance(x,dict):continue
                n=str(x.get("client") or "").strip(); cat=str(cats.get(n) or "").strip()
                if mode=="Somente clientes":
                    if cat=="Cliente":out.append(x)
                else:
                    if cat not in ("Interno","Pessoal","Grupo"):out.append(x)
            return out
        def refresh():
            cats=self._contact_categories_load(); vals=list(cats.values())
            cat_line=(f"Classificados: Cliente {vals.count('Cliente')} • Interno {vals.count('Interno')} • Pessoal {vals.count('Pessoal')} • Grupo {vals.count('Grupo')}\n\n")
            txt.setPlainText(cat_line+self._diagnostic_summary_text(filtered_rows()))
        refresh(); scope.currentIndexChanged.connect(refresh); classify.clicked.connect(lambda:self._contact_classify_current(dlg,refresh))
        bar=QHBoxLayout(); export=QPushButton("📤 Exportar diagnóstico"); close=QPushButton("Fechar")
        bar.addWidget(export); bar.addStretch(1); bar.addWidget(close); lay.addLayout(bar)
        def do_export():
            import datetime
            fn=f"ALIYVO_diagnostico_{datetime.date.today().isoformat()}.json"
            path,_=QFileDialog.getSaveFileName(dlg,"Exportar diagnóstico",fn,"Arquivo JSON (*.json)")
            if not path:return
            try:
                current=filtered_rows(); payload={"aliyvo_version":ALIYVO_VERSION,"exported_at":datetime.datetime.now().isoformat(timespec="seconds"),"scope":scope.currentText(),"categories":self._contact_categories_load(),"summary":self._diagnostic_summary_text(current),"events":current,"attendance_snapshot":getattr(self,"_attendance_data",{})}
                Path(path).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
                QMessageBox.information(dlg,"Diagnóstico","Arquivo exportado. Você pode me enviar esse JSON para eu analisar seu fluxo de atendimento.")
            except Exception as e: QMessageBox.warning(dlg,"Diagnóstico",f"Não consegui exportar: {e}")
        export.clicked.connect(do_export); close.clicked.connect(dlg.accept); dlg.exec()
'''
text=replace_method(text,'MainWindow','_diagnostic_show_dialog',new_diag)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched reminder filters + contact classification',version)
