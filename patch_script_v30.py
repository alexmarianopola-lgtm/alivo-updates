from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v30.json').read_text(encoding='utf-8'))
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
    start=sum(len(x) for x in lines[:target.lineno-1])
    end=sum(len(x) for x in lines[:target.end_lineno])
    if not new_code.endswith('\n'): new_code+='\n'
    return src[:start]+new_code+src[end:]

new_show=r'''    def _reminder_show_dialog(self):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QListWidget,QListWidgetItem,QPushButton
        import datetime
        dlg=QDialog(self); dlg.setWindowTitle("⏰ Lembretes do ALIYVO"); dlg.resize(680,490)
        lay=QVBoxLayout(dlg); lst=QListWidget(); lay.addWidget(lst,1)
        def refresh():
            current_id=""
            if lst.currentItem():
                current_id=str(lst.currentItem().data(Qt.ItemDataRole.UserRole) or "")
            lst.clear()
            rows=sorted([x for x in self._reminders if isinstance(x,dict)],key=lambda x:(bool(x.get("done")),float(x.get("due_ts") or 0)))
            for r in rows:
                due=datetime.datetime.fromtimestamp(float(r.get("due_ts") or 0)).strftime("%d/%m/%Y %H:%M")
                client=str(r.get("client") or "").strip(); done="✅" if r.get("done") else "⏰"
                line=f"{done} {due}  —  {r.get('text','')}"+(f"\nCliente: {client}" if client else "")
                it=QListWidgetItem(line); it.setData(Qt.ItemDataRole.UserRole,str(r.get("id") or "")); lst.addItem(it)
                if current_id and str(r.get("id") or "")==current_id:
                    lst.setCurrentItem(it)
        refresh()
        bar=QHBoxLayout()
        add=QPushButton("＋ Novo")
        edit=QPushButton("✏ Editar")
        complete=QPushButton("✅ Concluir")
        delete=QPushButton("🗑 Excluir")
        close=QPushButton("Fechar")
        for b in (add,edit,complete,delete): bar.addWidget(b)
        bar.addStretch(1); bar.addWidget(close); lay.addLayout(bar)
        def selected():
            it=lst.currentItem(); return str(it.data(Qt.ItemDataRole.UserRole) or "") if it else ""
        def do_edit():
            rid=selected()
            if not rid:return
            self._reminder_edit(rid,dlg,refresh)
        def finish():
            rid=selected()
            if not rid:return
            for r in self._reminders:
                if str(r.get("id") or "")==rid:
                    r["done"]=True
                    break
            self._reminder_save(); self._reminder_update_button(); refresh()
        def remove():
            rid=selected()
            if not rid:return
            self._reminders=[r for r in self._reminders if str(r.get("id") or "")!=rid]
            self._reminder_save(); self._reminder_update_button(); refresh()
        add.clicked.connect(lambda:self._reminder_add(dlg,refresh))
        edit.clicked.connect(do_edit)
        complete.clicked.connect(finish)
        delete.clicked.connect(remove)
        close.clicked.connect(dlg.accept)
        lst.itemDoubleClicked.connect(lambda *_:do_edit())
        dlg.exec()
'''
text=replace_method(text,'MainWindow','_reminder_show_dialog',new_show)

anchor='    def _reminder_add(self,parent=None,refresh=None):\n'
if anchor not in text:
    raise SystemExit('reminder add anchor not found')
edit_method=r'''    def _reminder_edit(self,rid,parent=None,refresh=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QFormLayout,QLineEdit,QDateTimeEdit,QHBoxLayout,QPushButton,QMessageBox
        from PyQt6.QtCore import QDateTime
        import time
        reminder=None
        for r in getattr(self,"_reminders",[]):
            if isinstance(r,dict) and str(r.get("id") or "")==str(rid or ""):
                reminder=r; break
        if reminder is None:
            return
        dlg=QDialog(parent or self); dlg.setWindowTitle("✏ Editar lembrete"); dlg.resize(540,270)
        lay=QVBoxLayout(dlg); form=QFormLayout()
        textw=QLineEdit(str(reminder.get("text") or ""))
        dt=QDateTimeEdit(); dt.setDisplayFormat("dd/MM/yyyy HH:mm"); dt.setCalendarPopup(True)
        try:
            dt.setDateTime(QDateTime.fromSecsSinceEpoch(int(float(reminder.get("due_ts") or time.time()))))
        except Exception:
            dt.setDateTime(QDateTime.currentDateTime())
        clientw=QLineEdit(str(reminder.get("client") or ""))
        clientw.setPlaceholderText("Opcional — ex.: Antiqueira")
        form.addRow("Lembrete:",textw)
        form.addRow("Data e hora:",dt)
        form.addRow("Cliente:",clientw)
        lay.addLayout(form)
        bar=QHBoxLayout(); save=QPushButton("💾 Salvar alterações"); cancel=QPushButton("Cancelar")
        bar.addStretch(1); bar.addWidget(save); bar.addWidget(cancel); lay.addLayout(bar)
        def do_save():
            txt=textw.text().strip()
            if not txt:
                QMessageBox.information(dlg,"Lembrete","Digite o que você precisa lembrar.")
                return
            due=float(dt.dateTime().toSecsSinceEpoch())
            old_text=str(reminder.get("text") or "")
            old_due=float(reminder.get("due_ts") or 0)
            reminder["text"]=txt
            reminder["due_ts"]=due
            reminder["client"]=clientw.text().strip()
            reminder["updated_at"]=time.time()
            reminder["alerted"]=False
            self._reminder_save(); self._reminder_update_button()
            try:
                self._diagnostic_log("reminder_edited",client=reminder.get("client","") or "",text=txt,due_ts=due,old_text=old_text,old_due_ts=old_due)
            except Exception:
                pass
            dlg.accept()
            if callable(refresh): refresh()
        save.clicked.connect(do_save); cancel.clicked.connect(dlg.reject); dlg.exec()

'''
text=text.replace(anchor,edit_method+anchor,1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched reminder editing',version)
