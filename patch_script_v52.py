from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v52.json').read_text(encoding='utf-8'))
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
    if not new_code.endswith('\n'):new_code+='\n'
    return src[:start]+new_code+src[end:]

text=replace_method(text,'MainWindow','_reminder_show_dialog',r'''    def _reminder_show_dialog(self):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QListWidget,QListWidgetItem,QPushButton,QComboBox,QLabel
        from PyQt6.QtGui import QColor,QFont
        import datetime,time
        dlg=QDialog(self); dlg.setWindowTitle("⏰ Lembretes do ALIYVO — CRM visual"); dlg.resize(760,560); lay=QVBoxLayout(dlg)
        top=QHBoxLayout();top.addWidget(QLabel("Mostrar:"));filt=QComboBox();filt.addItems(["A fazer","Concluídos","Todos","Vencidos"]);filt.setCurrentText("A fazer");top.addWidget(filt)
        counts=QLabel("");counts.setStyleSheet("font-weight:800;");top.addWidget(counts);top.addStretch(1)
        crm=QPushButton("🧭 CRM do dia");top.addWidget(crm);lay.addLayout(top)
        legend=QLabel("🔴 vencido   🟠 até 1h   🟡 hoje   🔵 futuro   🟢 concluído   •   prioridade visual")
        legend.setStyleSheet("font-weight:700;color:#44515c;padding:2px 4px;");lay.addWidget(legend)
        lst=QListWidget();lst.setSpacing(4);lst.setStyleSheet("QListWidget{border:1px solid #d7dee5;background:#ffffff;} QListWidget::item{border-radius:6px;padding:7px 9px;} QListWidget::item:selected{border:2px solid #1f6feb;}");lay.addWidget(lst,1)
        def urgency(r,now):
            if bool(r.get('done')):return (4,'CONCLUÍDO','🟢',QColor('#e8f7ee'),QColor('#176b3a'))
            try:due=float(r.get('due_ts') or 0)
            except Exception:due=0
            if due and due<now:return (0,'VENCIDO','🔴',QColor('#ffd9de'),QColor('#9e1027'))
            if due and 0<=due-now<=3600:return (1,'<1H','🟠',QColor('#ffe2bd'),QColor('#9b4d00'))
            if due:
                d=datetime.datetime.fromtimestamp(due)
                if d.date()==datetime.datetime.now().date():return (2,'HOJE','🟡',QColor('#fff4bf'),QColor('#715a00'))
            return (3,'FUTURO','🔵',QColor('#e0efff'),QColor('#16558c'))
        def refresh():
            lst.clear();now=time.time();allrows=[x for x in self._reminders if isinstance(x,dict)];pending=[x for x in allrows if not x.get('done')];done_rows=[x for x in allrows if x.get('done')];overdue=[x for x in pending if float(x.get('due_ts') or 0)<now]
            counts.setText(f"A fazer: {len(pending)}   •   Concluídos: {len(done_rows)}   •   Vencidos: {len(overdue)}")
            mode=filt.currentText();rows=pending if mode=='A fazer' else done_rows if mode=='Concluídos' else overdue if mode=='Vencidos' else allrows
            rows=sorted(rows,key=lambda r:(urgency(r,now)[0],float(r.get('due_ts') or 0)))
            for r in rows:
                due_ts=float(r.get('due_ts') or 0);due=datetime.datetime.fromtimestamp(due_ts).strftime('%d/%m/%Y %H:%M') if due_ts else 'Sem data';client=str(r.get('client') or '').strip();rank,label,icon,bg,fg=urgency(r,now)
                title=str(r.get('text') or '').strip()
                line=f"{icon}  [{label}]  {title}\n     {due}"+(f"   •   {client}" if client else '')
                it=QListWidgetItem(line);it.setData(Qt.ItemDataRole.UserRole,str(r.get('id') or ''));it.setBackground(bg);it.setForeground(fg)
                font=QFont();font.setBold(True);font.setPointSize(10);it.setFont(font);it.setSizeHint(it.sizeHint()+__import__('PyQt6.QtCore',fromlist=['QSize']).QSize(0,12));lst.addItem(it)
        refresh();filt.currentIndexChanged.connect(refresh)
        bar=QHBoxLayout();add_current=QPushButton("⏰ Desta conversa");add=QPushButton("＋ Novo");edit=QPushButton("✏ Editar");complete=QPushButton("✅ Concluir");reopen=QPushButton("↩ Reabrir");delete=QPushButton("🗑 Excluir");close=QPushButton("Fechar")
        for b in (add_current,add,edit,complete,reopen,delete):bar.addWidget(b)
        bar.addStretch(1);bar.addWidget(close);lay.addLayout(bar)
        def selected():
            it=lst.currentItem();return str(it.data(Qt.ItemDataRole.UserRole) or '') if it else ''
        def finish():
            rid=selected()
            if not rid:return
            for r in self._reminders:
                if str(r.get('id') or '')==rid:r['done']=True;r['alerted']=True;self._diagnostic_log('reminder_done',client=r.get('client',''),text=r.get('text',''));break
            self._reminder_save();self._reminder_update_button();refresh()
        def do_reopen():
            rid=selected()
            if not rid:return
            for r in self._reminders:
                if str(r.get('id') or '')==rid:r['done']=False;r['alerted']=False;self._diagnostic_log('reminder_reopened',client=r.get('client',''),text=r.get('text',''));break
            self._reminder_save();self._reminder_update_button();refresh()
        def remove():
            rid=selected()
            if not rid:return
            self._reminders=[r for r in self._reminders if str(r.get('id') or '')!=rid];self._reminder_save();self._reminder_update_button();refresh()
        def do_edit():
            rid=selected()
            if rid:self._reminder_edit(rid,dlg,refresh)
        add_current.clicked.connect(lambda:self._reminder_add_from_current(dlg,refresh));add.clicked.connect(lambda:self._reminder_add(dlg,refresh));edit.clicked.connect(do_edit);complete.clicked.connect(finish);reopen.clicked.connect(do_reopen);delete.clicked.connect(remove);close.clicked.connect(dlg.accept);lst.itemDoubleClicked.connect(lambda _it:do_edit())
        try:crm.clicked.connect(lambda:self._reminder_crm_dialog(dlg))
        except Exception:crm.setEnabled(False)
        dlg.exec()
''')

p.write_text(text,encoding='utf-8')
print('patched reminder urgency visual',version)
