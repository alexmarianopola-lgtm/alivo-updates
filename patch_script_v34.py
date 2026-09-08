from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v34.json').read_text(encoding='utf-8'))
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

# Detecta grupos automaticamente pelo JID do WhatsApp (@g.us) e por marcadores de grupo no DOM.
old_active="if(name)out.active={name:name,context:ctx.slice(-20)};"
new_active="""let isGroup=false;
              try{
                const ids=Array.from(main.querySelectorAll('[data-id],[data-jid],[data-chat-id]')).slice(-50).map(e=>String(e.getAttribute('data-id')||e.getAttribute('data-jid')||e.getAttribute('data-chat-id')||''));
                isGroup=ids.some(v=>v.includes('@g.us')) || !!main.querySelector('header [data-icon*=\"group\"],header [data-testid*=\"group\"]');
              }catch(e){}
              if(name)out.active={name:name,context:ctx.slice(-20),is_group:isGroup};"""
if old_active not in text: raise SystemExit('active assignment not found')
text=text.replace(old_active,new_active,1)

old_unread="if(unread){let snippet=clean(row.innerText||row.textContent||'');if(snippet.length>220)snippet=snippet.slice(-220);out.unread.push({name:name,snippet:snippet});}"
new_unread="""if(unread){
                  let snippet=clean(row.innerText||row.textContent||'');if(snippet.length>220)snippet=snippet.slice(-220);
                  let isGroup=false;
                  try{
                    const ids=Array.from(row.querySelectorAll('[data-id],[data-jid],[data-chat-id]')).slice(0,30).map(e=>String(e.getAttribute('data-id')||e.getAttribute('data-jid')||e.getAttribute('data-chat-id')||''));
                    isGroup=ids.some(v=>v.includes('@g.us')) || !!row.querySelector('[data-icon*=\"group\"],[data-testid*=\"group\"]');
                  }catch(e){}
                  out.unread.push({name:name,snippet:snippet,is_group:isGroup});
                }"""
if old_unread not in text: raise SystemExit('unread push not found')
text=text.replace(old_unread,new_unread,1)

# Carrega a lista automática de grupos detectados ao iniciar o diagnóstico.
old_seen='        self._diagnostic_seen_calls=set()\n'
new_seen='        self._diagnostic_seen_calls=set()\n        self._diagnostic_groups=set(self._diagnostic_groups_load())\n'
if old_seen not in text: raise SystemExit('diagnostic seen calls anchor not found')
text=text.replace(old_seen,new_seen,1)

# Na leitura do diagnóstico, aprende grupos e os exclui sem exigir classificação manual.
old_scan_head='''        now=time.time(); active=result.get("active") or {}; name=str(active.get("name") or "").strip(); context=active.get("context") or []\n        self._diagnostic_active_name=name\n\n        changed_chat=bool(name and name!=getattr(self,"_diagnostic_last_active",""))\n'''
new_scan_head='''        now=time.time(); active=result.get("active") or {}; name=str(active.get("name") or "").strip(); context=active.get("context") or []\n        self._diagnostic_active_name=name\n\n        groups=set(getattr(self,"_diagnostic_groups",set()) or set())\n        learned=False\n        if name and bool(active.get("is_group")) and name not in groups:\n            groups.add(name); learned=True\n        for _row in (result.get("unread") or []):\n            if isinstance(_row,dict) and bool(_row.get("is_group")):\n                _n=str(_row.get("name") or "").strip()\n                if _n and _n not in groups: groups.add(_n); learned=True\n        if learned:\n            self._diagnostic_groups=groups; self._diagnostic_groups_save(groups)\n\n        changed_chat=bool(name and name not in groups and name!=getattr(self,"_diagnostic_last_active",""))\n'''
if old_scan_head not in text: raise SystemExit('scan head anchor not found')
text=text.replace(old_scan_head,new_scan_head,1)

old_context='        if name and context:\n'
new_context='        if name and name not in groups and context:\n'
if old_context not in text: raise SystemExit('context anchor not found')
text=text.replace(old_context,new_context,1)

old_unread_loop='''        for row in (result.get("unread") or []):\n            if isinstance(row,dict):\n                n=str(row.get("name") or "").strip()\n                if n: unread_rows[n]=row\n'''
new_unread_loop='''        for row in (result.get("unread") or []):\n            if isinstance(row,dict):\n                n=str(row.get("name") or "").strip()\n                if n and n not in groups and not bool(row.get("is_group")): unread_rows[n]=row\n'''
if old_unread_loop not in text: raise SystemExit('unread loop anchor not found')
text=text.replace(old_unread_loop,new_unread_loop,1)

# Persistência simples dos nomes de grupos já reconhecidos. Ao reconhecer um grupo depois,
# eventos antigos daquele nome também deixam de entrar nos relatórios futuros.
anchor='    def _diagnostic_show_dialog(self):\n'
if anchor not in text: raise SystemExit('diagnostic dialog anchor not found')
helpers=r'''    def _diagnostic_groups_file(self):
        try: USER_DATA_DIR.mkdir(parents=True,exist_ok=True)
        except Exception: pass
        return USER_DATA_DIR/"grupos_diagnostico.json"

    def _diagnostic_groups_load(self):
        try:
            f=self._diagnostic_groups_file()
            if f.exists():
                x=json.loads(f.read_text(encoding="utf-8"))
                if isinstance(x,list): return [str(v).strip() for v in x if str(v).strip()]
        except Exception: pass
        return []

    def _diagnostic_groups_save(self,groups):
        try:
            vals=sorted(set(str(v).strip() for v in (groups or []) if str(v).strip()),key=str.lower)
            self._diagnostic_groups_file().write_text(json.dumps(vals,ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception: pass

'''
text=text.replace(anchor,helpers+anchor,1)

# Remove da interface a classificação Cliente/Interno/Pessoal/Grupo.
# Todo contato individual entra; somente grupos reconhecidos são excluídos automaticamente.
new_diag=r'''    def _diagnostic_show_dialog(self):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QTextEdit,QPushButton,QFileDialog,QMessageBox,QLabel
        import datetime
        dlg=QDialog(self); dlg.setWindowTitle("📊 Diagnóstico do atendimento"); dlg.resize(760,600)
        lay=QVBoxLayout(dlg)
        groups=set(self._diagnostic_groups_load())
        info=QLabel(f"Analisando contatos individuais • {len(groups)} grupo(s) ignorado(s) automaticamente")
        info.setStyleSheet("font-weight:700;"); lay.addWidget(info)
        txt=QTextEdit(); txt.setReadOnly(True); txt.setStyleSheet("font-size:12px;font-weight:600;"); lay.addWidget(txt,1)
        rows=self._diagnostic_read()
        def filtered_rows():
            current_groups=set(self._diagnostic_groups_load())
            return [x for x in rows if not (isinstance(x,dict) and str(x.get("client") or "").strip() in current_groups)]
        current=filtered_rows(); txt.setPlainText(self._diagnostic_summary_text(current))
        bar=QHBoxLayout(); export=QPushButton("📤 Exportar diagnóstico"); close=QPushButton("Fechar")
        bar.addWidget(export); bar.addStretch(1); bar.addWidget(close); lay.addLayout(bar)
        def do_export():
            fn=f"ALIYVO_diagnostico_{datetime.date.today().isoformat()}.json"
            path,_=QFileDialog.getSaveFileName(dlg,"Exportar diagnóstico",fn,"Arquivo JSON (*.json)")
            if not path:return
            try:
                current=filtered_rows(); ignored=sorted(self._diagnostic_groups_load(),key=str.lower)
                payload={"aliyvo_version":ALIYVO_VERSION,"exported_at":datetime.datetime.now().isoformat(timespec="seconds"),"mode":"contatos_individuais","ignored_groups":ignored,"summary":self._diagnostic_summary_text(current),"events":current,"attendance_snapshot":getattr(self,"_attendance_data",{})}
                Path(path).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
                QMessageBox.information(dlg,"Diagnóstico","Arquivo exportado. Grupos reconhecidos foram retirados da análise.")
            except Exception as e: QMessageBox.warning(dlg,"Diagnóstico",f"Não consegui exportar: {e}")
        export.clicked.connect(do_export); close.clicked.connect(dlg.accept); dlg.exec()
'''
text=replace_method(text,'MainWindow','_diagnostic_show_dialog',new_diag)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched automatic group exclusion',version)
