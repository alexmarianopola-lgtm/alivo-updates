from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v37.json').read_text(encoding='utf-8'))
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

# Backup automatico a cada 2 minutos, alem dos timers existentes.
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
        self._diagnostic_backup_timer=QTimer(self); self._diagnostic_backup_timer.setInterval(120000)
        self._diagnostic_backup_timer.timeout.connect(self._diagnostic_daily_backup); self._diagnostic_backup_timer.start()
        QTimer.singleShot(7000,self._diagnostic_daily_backup)
        try:
            for attr,tool in (("plate_toggle","plate"),("lens_toggle","image")):
                b=getattr(self,attr,None)
                if b:b.clicked.connect(lambda _=False,t=tool:self._diagnostic_log("tool_opened",client=getattr(self,"_diagnostic_active_name","") or "",tool=t))
        except Exception: pass
'''
text=replace_method(text,'MainWindow','_diagnostic_start',new_start)

anchor='    def _diagnostic_show_dialog(self):\n'
if anchor not in text: raise SystemExit('diagnostic dialog anchor not found')
helpers=r'''    def _diagnostic_backup_folder(self):
        try:
            from PyQt6.QtCore import QStandardPaths
            base=str(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation) or "").strip()
        except Exception:
            base=""
        try:
            folder=(Path(base) if base else (Path.home()/"Documents"))/"ALIYVO"/"Diagnósticos"
            folder.mkdir(parents=True,exist_ok=True)
            return folder
        except Exception:
            folder=USER_DATA_DIR/"Diagnósticos"
            try:folder.mkdir(parents=True,exist_ok=True)
            except Exception:pass
            return folder

    def _diagnostic_daily_backup(self):
        import datetime
        try:
            today=datetime.date.today()
            iso=today.isoformat()
            groups=set(self._diagnostic_groups_load())
            rows=[]
            for x in self._diagnostic_read():
                if not isinstance(x,dict):continue
                if not str(x.get("time") or "").startswith(iso):continue
                if str(x.get("client") or "").strip() in groups:continue
                rows.append(x)
            payload={
                "aliyvo_version":ALIYVO_VERSION,
                "date":iso,
                "generated_at":datetime.datetime.now().isoformat(timespec="seconds"),
                "automatic_backup":True,
                "mode":"contatos_individuais",
                "ignored_groups":sorted(groups,key=str.lower),
                "summary":self._diagnostic_daily_summary_text(rows),
                "full_diagnostic":self._diagnostic_enhanced_text(rows),
                "waiting_now":self._diagnostic_waiting_snapshot(),
                "events":rows,
                "attendance_snapshot":getattr(self,"_attendance_data",{})
            }
            folder=self._diagnostic_backup_folder()
            name=f"Diagnostico_{today.strftime('%d-%m-%Y')}.json"
            target=folder/name
            tmp=folder/(name+".tmp")
            tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
            try:tmp.replace(target)
            except Exception:
                target.write_text(tmp.read_text(encoding="utf-8"),encoding="utf-8")
                try:tmp.unlink()
                except Exception:pass
            return str(target)
        except Exception:
            return ""

    def _diagnostic_open_backup_folder(self,parent=None):
        from PyQt6.QtWidgets import QMessageBox
        try:
            from PyQt6.QtCore import QUrl
            from PyQt6.QtGui import QDesktopServices
            self._diagnostic_daily_backup()
            folder=self._diagnostic_backup_folder()
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))):
                raise RuntimeError("Não consegui abrir a pasta automaticamente.")
        except Exception as e:
            try:QMessageBox.information(parent or self,"Diagnósticos",f"Os backups ficam em:\n{self._diagnostic_backup_folder()}\n\n{e}")
            except Exception:pass

'''
text=text.replace(anchor,helpers+anchor,1)

# Acrescenta botao para abrir a pasta onde os backups diarios ficam salvos.
old='''        bar=QHBoxLayout(); history=QPushButton("👤 Histórico por contato"); daily=QPushButton("📅 Resumo do dia"); refresh_btn=QPushButton("↻ Atualizar"); export=QPushButton("📤 Exportar diagnóstico"); close=QPushButton("Fechar")
        for b in (history,daily,refresh_btn,export):bar.addWidget(b)
        bar.addStretch(1);bar.addWidget(close);lay.addLayout(bar)
        history.clicked.connect(lambda:self._diagnostic_contact_history_dialog(dlg)); daily.clicked.connect(lambda:self._diagnostic_show_daily_summary(dlg)); refresh_btn.clicked.connect(refresh)
'''
new='''        bar=QHBoxLayout(); history=QPushButton("👤 Histórico por contato"); daily=QPushButton("📅 Resumo do dia"); folder_btn=QPushButton("📁 Abrir pasta"); refresh_btn=QPushButton("↻ Atualizar"); export=QPushButton("📤 Exportar diagnóstico"); close=QPushButton("Fechar")
        for b in (history,daily,folder_btn,refresh_btn,export):bar.addWidget(b)
        bar.addStretch(1);bar.addWidget(close);lay.addLayout(bar)
        history.clicked.connect(lambda:self._diagnostic_contact_history_dialog(dlg)); daily.clicked.connect(lambda:self._diagnostic_show_daily_summary(dlg)); folder_btn.clicked.connect(lambda:self._diagnostic_open_backup_folder(dlg)); refresh_btn.clicked.connect(refresh)
'''
if old not in text: raise SystemExit('diagnostic button bar anchor not found')
text=text.replace(old,new,1)

# Antes de exibir o resumo automatico/manual, garante que a copia do dia esteja atualizada.
old_daily='''    def _diagnostic_show_daily_summary(self,parent=None,automatic=False):
        from PyQt6.QtWidgets import QMessageBox
        groups=set(self._diagnostic_groups_load()); rows=[x for x in self._diagnostic_read() if not (isinstance(x,dict) and str(x.get("client") or "").strip() in groups)]
'''
new_daily='''    def _diagnostic_show_daily_summary(self,parent=None,automatic=False):
        from PyQt6.QtWidgets import QMessageBox
        try:self._diagnostic_daily_backup()
        except Exception:pass
        groups=set(self._diagnostic_groups_load()); rows=[x for x in self._diagnostic_read() if not (isinstance(x,dict) and str(x.get("client") or "").strip() in groups)]
'''
if old_daily not in text: raise SystemExit('daily summary method anchor not found')
text=text.replace(old_daily,new_daily,1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched automatic daily diagnostic backups',version)
