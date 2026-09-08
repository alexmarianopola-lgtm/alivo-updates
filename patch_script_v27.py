from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v27.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.41 - Fila de atendimentos BETA, totalmente reversivel.
# Preserva o painel antigo de Acoes rapidas e todo o WhatsApp atual.
# O usuario pode voltar ao modo atual a qualquer momento; a preferencia fica salva.

if 'class AliyvoAttendancePanel(QWidget):' not in text:
    marker='class MainWindow(QMainWindow):\n'
    if marker not in text:
        raise SystemExit('MainWindow marker not found')

    panel=r'''

# -----------------------------------------------------------------------------
# ALIYVO - Fila de atendimentos BETA (reversivel)
# -----------------------------------------------------------------------------
class AliyvoAttendancePanel(QWidget):
    STATUS_META={
        "reply":("🔥","Preciso responder","#B91C1C"),
        "working":("🟠","Em atendimento","#B45309"),
        "waiting":("🔵","Aguardando cliente","#1D4ED8"),
        "resolved":("✅","Resolvido","#047857"),
    }

    def __init__(self,owner,parent=None):
        super().__init__(parent)
        self.owner=owner
        self.selected_name=""
        self.setObjectName("aliyvoAttendancePanel")
        self.setStyleSheet("""
            QWidget#aliyvoAttendancePanel{background:#071A2B;color:#F4FAF8;}
            QWidget#aliyvoAttendancePanel QLabel{color:#F4FAF8;background:transparent;}
            QWidget#aliyvoAttendancePanel QPushButton{
                background:#0A2236;color:#F4FAF8;border:1px solid #173B52;
                border-radius:7px;padding:7px 8px;font-size:10px;font-weight:700;
            }
            QWidget#aliyvoAttendancePanel QPushButton:hover{border-color:#20E983;background:#0D303B;}
            QWidget#aliyvoAttendancePanel QListWidget{
                background:#061626;color:#F4FAF8;border:1px solid #173B52;
                border-radius:7px;padding:3px;font-size:10px;
            }
            QWidget#aliyvoAttendancePanel QListWidget::item{padding:8px;border-bottom:1px solid #12374D;}
            QWidget#aliyvoAttendancePanel QListWidget::item:selected{background:#0D303B;border:1px solid #20E983;}
            QWidget#aliyvoAttendancePanel QCheckBox{color:#C8D8E2;font-size:9px;}
        """)
        lay=QVBoxLayout(self)
        lay.setContentsMargins(10,10,10,9)
        lay.setSpacing(7)

        head=QHBoxLayout()
        title=QLabel("🧠 Fila de atendimentos")
        title.setStyleSheet("font-size:14px;font-weight:800;color:#FFFFFF;")
        beta=QLabel("BETA")
        beta.setStyleSheet("font-size:8px;font-weight:800;color:#20E983;border:1px solid #20E983;border-radius:5px;padding:2px 5px;")
        head.addWidget(title); head.addStretch(1); head.addWidget(beta)
        lay.addLayout(head)

        sub=QLabel("Lido não significa resolvido. O ALIYVO guarda quem precisa de você e onde você parou.")
        sub.setWordWrap(True)
        sub.setStyleSheet("color:#7FC9B4;font-size:9px;")
        lay.addWidget(sub)

        self.current=QLabel("Abra uma conversa no WhatsApp")
        self.current.setWordWrap(True)
        self.current.setStyleSheet("background:#0A2236;border:1px solid #173B52;border-radius:7px;padding:8px;font-size:11px;font-weight:700;")
        lay.addWidget(self.current)

        self.resume=QLabel("")
        self.resume.setWordWrap(True)
        self.resume.setStyleSheet("color:#C8D8E2;font-size:9px;padding:2px 3px;")
        lay.addWidget(self.resume)

        r1=QHBoxLayout()
        self.park_btn=QPushButton("📌 Estacionar")
        self.resolve_btn=QPushButton("✅ Resolvido")
        r1.addWidget(self.park_btn); r1.addWidget(self.resolve_btn)
        lay.addLayout(r1)

        r2=QHBoxLayout()
        self.reply_btn=QPushButton("🔥 Responder")
        self.wait_btn=QPushButton("🔵 Aguardar")
        self.note_btn=QPushButton("✏ Nota")
        r2.addWidget(self.reply_btn); r2.addWidget(self.wait_btn); r2.addWidget(self.note_btn)
        lay.addLayout(r2)

        qhead=QHBoxLayout()
        qlab=QLabel("PENDÊNCIAS")
        qlab.setStyleSheet("font-size:9px;font-weight:800;color:#9FC4D5;")
        self.count=QLabel("0")
        self.count.setStyleSheet("font-size:9px;font-weight:800;color:#20E983;")
        qhead.addWidget(qlab); qhead.addStretch(1); qhead.addWidget(self.count)
        lay.addLayout(qhead)

        self.list=QListWidget()
        self.list.setMinimumHeight(170)
        lay.addWidget(self.list,1)

        self.show_resolved=QCheckBox("Mostrar resolvidos")
        lay.addWidget(self.show_resolved)

        r3=QHBoxLayout()
        self.open_btn=QPushButton("↗ Abrir conversa")
        self.refresh_btn=QPushButton("↻ Atualizar")
        r3.addWidget(self.open_btn); r3.addWidget(self.refresh_btn)
        lay.addLayout(r3)

        tools=QLabel("FERRAMENTAS DO CLIENTE ATUAL")
        tools.setStyleSheet("font-size:9px;font-weight:800;color:#9FC4D5;margin-top:3px;")
        lay.addWidget(tools)
        self.tool_soma=QPushButton("🔎  Busca Somaforce")
        self.tool_image=QPushButton("🖼  Busca por imagem")
        self.tool_plate=QPushButton("🚚  Placa / chassi")
        self.tool_audio=QPushButton("🎙  Áudio")
        for b in (self.tool_soma,self.tool_image,self.tool_plate,self.tool_audio):
            lay.addWidget(b)

        self.classic_btn=QPushButton("↩ Voltar ao modo atual")
        self.classic_btn.setToolTip("Esconde esta fila e restaura exatamente o painel de Ações rápidas anterior")
        self.classic_btn.setStyleSheet("background:#132B3D;color:#D9E7EE;border:1px solid #315269;border-radius:7px;padding:7px;font-size:9px;font-weight:700;")
        lay.addWidget(self.classic_btn)

        self.park_btn.clicked.connect(lambda:self.owner._attendance_mark("working"))
        self.resolve_btn.clicked.connect(lambda:self.owner._attendance_mark("resolved"))
        self.reply_btn.clicked.connect(lambda:self.owner._attendance_mark("reply"))
        self.wait_btn.clicked.connect(lambda:self.owner._attendance_mark("waiting"))
        self.note_btn.clicked.connect(self.owner._attendance_edit_note)
        self.open_btn.clicked.connect(self._open_selected)
        self.refresh_btn.clicked.connect(lambda:self.owner._attendance_scan(force=True))
        self.classic_btn.clicked.connect(lambda:self.owner._set_attendance_mode(False))
        self.show_resolved.stateChanged.connect(lambda *_:self.refresh())
        self.list.itemSelectionChanged.connect(self._selection_changed)
        self.list.itemDoubleClicked.connect(lambda *_:self._open_selected())
        self.tool_soma.clicked.connect(lambda:self.owner._open_quick_tool("technical"))
        self.tool_image.clicked.connect(lambda:self.owner._open_quick_tool("lens"))
        self.tool_plate.clicked.connect(lambda:self.owner._attendance_open_plate())
        self.tool_audio.clicked.connect(lambda:self.owner._open_quick_tool("audio"))

    def _selection_changed(self):
        it=self.list.currentItem()
        if it:
            self.selected_name=str(it.data(Qt.ItemDataRole.UserRole) or "")

    def _open_selected(self):
        name=self.selected_name or getattr(self.owner,"_attendance_current_name","")
        if name:
            self.owner._attendance_open_chat(name)

    def _age(self,ts):
        try:
            import time
            secs=max(0,int(time.time()-float(ts or 0)))
            if secs<60: return "agora"
            mins=secs//60
            if mins<60: return f"{mins} min"
            hrs=mins//60
            if hrs<24: return f"{hrs} h"
            return f"{hrs//24} d"
        except Exception:
            return ""

    def refresh(self):
        data=getattr(self.owner,"_attendance_data",{}) or {}
        items=data.get("items",{}) if isinstance(data,dict) else {}
        current=getattr(self.owner,"_attendance_current_name","") or ""
        if current:
            info=items.get(current,{})
            status=str(info.get("status") or "reply")
            emo,label,color=self.STATUS_META.get(status,self.STATUS_META["reply"])
            self.current.setText(f"{emo} {current}\n{label}")
            self.current.setStyleSheet(f"background:#0A2236;border:1px solid {color};border-radius:7px;padding:8px;font-size:11px;font-weight:700;color:#FFFFFF;")
            note=str(info.get("note") or "").strip()
            last=str(info.get("last_customer") or "").strip()
            codes=info.get("codes") or []
            plate=str(info.get("plate") or "")
            bits=[]
            if note: bits.append("📌 "+note)
            elif last: bits.append("Você parou aqui: "+last[:150])
            if codes: bits.append("Códigos: "+", ".join(str(x) for x in codes[:5]))
            if plate: bits.append("Placa: "+plate)
            self.resume.setText("\n".join(bits))
        else:
            self.current.setText("Abra uma conversa no WhatsApp")
            self.current.setStyleSheet("background:#0A2236;border:1px solid #173B52;border-radius:7px;padding:8px;font-size:11px;font-weight:700;color:#FFFFFF;")
            self.resume.setText("A fila continua guardada mesmo quando você troca de cliente.")

        old_selected=self.selected_name
        self.list.clear()
        weight={"reply":0,"working":1,"waiting":2,"resolved":3}
        rows=[]
        for name,info in items.items():
            if not isinstance(info,dict): continue
            st=str(info.get("status") or "reply")
            if st=="resolved" and not self.show_resolved.isChecked():
                continue
            rows.append((weight.get(st,9),-float(info.get("updated_at") or 0),str(name),info))
        rows.sort()
        pending=sum(1 for _,_,_,i in rows if str(i.get("status") or "")!="resolved")
        self.count.setText(str(pending))
        for _,__,name,info in rows:
            st=str(info.get("status") or "reply")
            emo,label,color=self.STATUS_META.get(st,self.STATUS_META["reply"])
            age=self._age(info.get("updated_at"))
            excerpt=str(info.get("note") or info.get("last_customer") or info.get("snippet") or "").replace("\n"," ").strip()
            if len(excerpt)>88: excerpt=excerpt[:85]+"..."
            line=f"{emo} {name}\n{label} • {age}"
            if excerpt: line+="\n"+excerpt
            it=QListWidgetItem(line)
            it.setData(Qt.ItemDataRole.UserRole,name)
            try: it.setForeground(QColor("#F4FAF8"))
            except Exception: pass
            self.list.addItem(it)
            if name==old_selected or (not old_selected and name==current):
                self.list.setCurrentItem(it)
        if not self.list.currentItem() and self.list.count():
            self.list.setCurrentRow(0)

'''
    text=text.replace(marker,panel+marker,1)

# Botao superior para entrar/sair da experiencia nova.
old='''        self.plate_toggle=QPushButton("🚚  Busca placa")'''
if old not in text:
    raise SystemExit('plate top button anchor not found')
text=text.replace(old,old+'\n        self.attendance_toggle=QPushButton("🧠  Atendimentos")',1)

# Adiciona o botao na barra superior, preferencialmente logo depois de Busca placa.
nav_match=re.search(r'(?m)^(?P<indent>\s*)nav_lay\.addWidget\(self\.plate_toggle\)\s*$',text)
if nav_match:
    ins=nav_match.group(0)+'\n'+nav_match.group('indent')+'nav_lay.addWidget(self.attendance_toggle)'
    text=text[:nav_match.start()]+ins+text[nav_match.end():]
else:
    # fallback antes do primeiro addStretch da barra
    m=re.search(r'(?m)^(?P<indent>\s*)nav_lay\.addStretch\([^\n]*\)\s*$',text)
    if not m: raise SystemExit('nav layout anchor not found')
    text=text[:m.start()]+m.group('indent')+'nav_lay.addWidget(self.attendance_toggle)\n'+text[m.start():]

# Cria o painel beta ao lado do painel antigo, sem destruir o antigo.
old='''        self.quick_host_layout.addWidget(self.quick_panel)'''
if old not in text:
    raise SystemExit('quick panel host anchor not found')
new='''        self.quick_host_layout.addWidget(self.quick_panel)\n        self.attendance_panel=AliyvoAttendancePanel(self,self.quick_host)\n        self.attendance_panel.hide()\n        self.quick_host_layout.addWidget(self.attendance_panel,1)'''
text=text.replace(old,new,1)

# Conecta o botao superior.
anchor='''        self.quick_plate.clicked.connect(lambda: self._open_quick_tool("plate"))'''
if anchor not in text:
    raise SystemExit('quick plate signal anchor not found')
text=text.replace(anchor,anchor+'\n        self.attendance_toggle.clicked.connect(self._toggle_attendance_mode)',1)

# Inicializa a fila depois que a janela principal ja existe.
anchor='''        self.setCentralWidget(self.splitter)'''
if anchor not in text:
    raise SystemExit('central widget anchor not found')
text=text.replace(anchor,anchor+'\n        QTimer.singleShot(650,self._attendance_bootstrap)',1)

# Ao abrir uma ferramenta, esconde tambem a home beta.
anchor='''        self.quick_panel.hide()'''
if anchor not in text:
    raise SystemExit('quick panel hide anchor not found')
# Ha mais de um; queremos o que fica em _open_quick_tool. Localiza depois da definicao.
pos=text.find('    def _open_quick_tool(self, tool):')
h=text.find(anchor,pos)
if h==-1:
    raise SystemExit('quick panel hide inside _open_quick_tool not found')
rep=anchor+'\n        try: self.attendance_panel.hide()\n        except Exception: pass'
text=text[:h]+text[h:].replace(anchor,rep,1)

# Ao voltar da ferramenta, escolhe a home beta ou a home antiga conforme preferencia.
old='''        self.quick_host.setFixedWidth(225)\n        self.quick_panel.show()\n        self.quick_panel.raise_()\n        self._reset_tool_button_texts()'''
if old not in text:
    raise SystemExit('restore quick actions block not found')
new='''        self._attendance_apply_home()\n        self._reset_tool_button_texts()'''
text=text.replace(old,new,1)

# Metodos da MainWindow. Inseridos imediatamente antes do primeiro metodo tecnico.
anchor='''    def _technical_open_and_analyze(self):\n'''
if anchor not in text:
    raise SystemExit('technical method anchor not found')
methods=r'''    def _attendance_file(self):
        try:
            USER_DATA_DIR.mkdir(parents=True,exist_ok=True)
        except Exception:
            pass
        return USER_DATA_DIR/"atendimentos_beta.json"

    def _attendance_load(self):
        data={"enabled":True,"items":{}}
        try:
            f=self._attendance_file()
            if f.exists():
                loaded=json.loads(f.read_text(encoding="utf-8"))
                if isinstance(loaded,dict):
                    data.update(loaded)
                    if not isinstance(data.get("items"),dict): data["items"]={}
        except Exception:
            pass
        self._attendance_data=data
        self._attendance_current_name=""
        self._attendance_scan_busy=False

    def _attendance_save(self):
        try:
            self._attendance_file().write_text(json.dumps(self._attendance_data,ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception:
            pass

    def _attendance_bootstrap(self):
        self._attendance_load()
        self._attendance_apply_home()
        try:
            self._attendance_timer=QTimer(self)
            self._attendance_timer.setInterval(2800)
            self._attendance_timer.timeout.connect(self._attendance_scan)
            self._attendance_timer.start()
        except Exception:
            pass
        QTimer.singleShot(900,lambda:self._attendance_scan(force=True))

    def _attendance_enabled(self):
        try: return bool(self._attendance_data.get("enabled",True))
        except Exception: return True

    def _attendance_apply_home(self):
        enabled=self._attendance_enabled() if hasattr(self,"_attendance_data") else True
        try:
            self.quick_scroll.hide()
        except Exception:
            pass
        if enabled:
            try:
                self.quick_panel.hide()
                self.attendance_panel.show(); self.attendance_panel.raise_()
                self.quick_host.setFixedWidth(345)
                self.attendance_toggle.setText("🧠  Atendimentos ✓")
                self.attendance_panel.refresh()
            except Exception:
                pass
        else:
            try:
                self.attendance_panel.hide()
                self.quick_panel.show(); self.quick_panel.raise_()
                self.quick_host.setFixedWidth(225)
                self.attendance_toggle.setText("🧠  Atendimentos")
            except Exception:
                pass

    def _set_attendance_mode(self,enabled):
        if not hasattr(self,"_attendance_data"):
            self._attendance_load()
        self._attendance_data["enabled"]=bool(enabled)
        self._attendance_save()
        # Fecha ferramenta lateral e volta para a home escolhida.
        try:
            if getattr(self,"_quick_mode_tool",None):
                self._restore_quick_actions()
            else:
                self._attendance_apply_home()
        except Exception:
            self._attendance_apply_home()

    def _toggle_attendance_mode(self):
        self._set_attendance_mode(not self._attendance_enabled())

    def _attendance_extract_js(self):
        return r"""
        (() => {
          try{
            const clean=t=>String(t||'').replace(/\s+/g,' ').trim();
            const out={ok:true,active:null,unread:[]};
            const main=document.querySelector('#main') || document.querySelector('[data-testid="conversation-panel-wrapper"]');
            if(main){
              let name='';
              const h=main.querySelector('header [data-testid="conversation-info-header-chat-title"]') ||
                      main.querySelector('header span[title]') || main.querySelector('header [title]');
              if(h) name=clean(h.getAttribute('title')||h.textContent||'');
              const ctx=[];
              const mr=main.getBoundingClientRect();
              const mid=mr.left+mr.width*0.50;
              const push=(side,txt)=>{txt=clean(txt);if(txt&&txt.length>1)ctx.push({side:side,text:txt.slice(0,1200)});};
              const bubbles=Array.from(main.querySelectorAll('div.message-in,div.message-out')).slice(-18);
              if(bubbles.length){
                for(const b of bubbles){
                  const side=b.classList.contains('message-out')?'seller':'customer';
                  const ns=Array.from(b.querySelectorAll('span.selectable-text,[data-testid="selectable-text"]'));
                  let parts=[];
                  for(const n of ns){const t=clean(n.innerText||n.textContent||'');if(t&&!parts.includes(t))parts.push(t);}
                  if(parts.length)push(side,parts.join(' '));
                }
              }else{
                for(const b of Array.from(main.querySelectorAll('[data-pre-plain-text]')).slice(-18)){
                  const r=b.getBoundingClientRect();
                  const side=((r.left+r.right)/2)>=mid?'seller':'customer';
                  const ns=Array.from(b.querySelectorAll('span.selectable-text,[data-testid="selectable-text"]'));
                  let parts=[];
                  for(const n of ns){const t=clean(n.innerText||n.textContent||'');if(t&&!parts.includes(t))parts.push(t);}
                  if(parts.length)push(side,parts.join(' '));
                }
              }
              if(name) out.active={name:name,context:ctx.slice(-14)};
            }
            const pane=document.querySelector('#pane-side');
            if(pane){
              const rows=Array.from(pane.querySelectorAll('[role="listitem"],[role="row"],[data-testid="cell-frame-container"]')).slice(0,90);
              const seen=new Set();
              for(const row of rows){
                const n=row.querySelector('span[title]');
                const name=n?clean(n.getAttribute('title')||n.textContent||''):'';
                if(!name||seen.has(name))continue;
                seen.add(name);
                let unread=false;
                const els=Array.from(row.querySelectorAll('[aria-label],[data-testid],[data-icon]'));
                for(const e of els){
                  const a=(String(e.getAttribute('aria-label')||'')+' '+String(e.getAttribute('data-testid')||'')+' '+String(e.getAttribute('data-icon')||'')).toLowerCase();
                  if(a.includes('unread')||a.includes('não lida')||a.includes('não lidas')||a.includes('não lido')||a.includes('não lidos')){unread=true;break;}
                }
                if(unread){
                  let snippet=clean(row.innerText||row.textContent||'');
                  if(snippet.length>180)snippet=snippet.slice(-180);
                  out.unread.push({name:name,snippet:snippet});
                }
              }
            }
            return out;
          }catch(e){return {ok:false,error:String(e)};}
        })();
        """

    def _attendance_scan(self,force=False):
        if not self._attendance_enabled(): return
        if getattr(self,"_attendance_scan_busy",False) and not force: return
        try:
            self._attendance_scan_busy=True
            self.web.page().runJavaScript(self._attendance_extract_js(),self._attendance_scan_done)
        except Exception:
            self._attendance_scan_busy=False

    def _attendance_scan_done(self,result):
        self._attendance_scan_busy=False
        if not isinstance(result,dict) or not result.get("ok"):
            return
        import time
        now=time.time()
        items=self._attendance_data.setdefault("items",{})
        active=result.get("active") or {}
        name=str(active.get("name") or "").strip()
        context=active.get("context") or []
        if name:
            self._attendance_current_name=name
            info=items.get(name) if isinstance(items.get(name),dict) else {}
            last=context[-1] if context else {}
            side=str(last.get("side") or "")
            last_text=str(last.get("text") or "").strip()
            signature=(side+"|"+last_text)[-1500:]
            changed=bool(signature and signature!=str(info.get("last_signature") or ""))
            info["name"]=name
            info["last_seen"]=now
            info["context"]=context[-10:]
            customers=[str(x.get("text") or "") for x in context if isinstance(x,dict) and x.get("side")=="customer"]
            sellers=[str(x.get("text") or "") for x in context if isinstance(x,dict) and x.get("side")=="seller"]
            if customers: info["last_customer"]=customers[-1]
            if sellers: info["last_seller"]=sellers[-1]
            all_text="\n".join(str(x.get("text") or "") for x in context if isinstance(x,dict))
            try: info["plate"]=detect_plate(all_text)
            except Exception: info["plate"]=""
            try:
                codes=[]
                for c in extract_codes(all_text):
                    c=str(c)
                    if c not in codes: codes.append(c)
                info["codes"]=codes[:12]
            except Exception: pass
            if changed:
                info["last_signature"]=signature
                info["updated_at"]=now
                info["status"]="reply" if side=="customer" else "waiting" if side=="seller" else str(info.get("status") or "reply")
            elif "status" not in info:
                info["status"]="reply" if side=="customer" else "waiting"
                info["updated_at"]=now
            items[name]=info
        else:
            self._attendance_current_name=""

        # Conversas visíveis com selo de não lida continuam sendo consideradas pendentes.
        for row in (result.get("unread") or []):
            if not isinstance(row,dict): continue
            n=str(row.get("name") or "").strip()
            if not n: continue
            info=items.get(n) if isinstance(items.get(n),dict) else {}
            info["name"]=n
            info["snippet"]=str(row.get("snippet") or "")[-180:]
            if str(info.get("status") or "")!="reply":
                info["status"]="reply"
                info["updated_at"]=now
            elif not info.get("updated_at"):
                info["updated_at"]=now
            items[n]=info

        self._attendance_save()
        try:self.attendance_panel.refresh()
        except Exception:pass

    def _attendance_mark(self,status):
        name=str(getattr(self,"_attendance_current_name","") or "").strip()
        if not name:
            QMessageBox.information(self,"Atendimentos","Abra a conversa do cliente no WhatsApp primeiro.")
            return
        import time
        items=self._attendance_data.setdefault("items",{})
        info=items.get(name) if isinstance(items.get(name),dict) else {}
        info["name"]=name; info["status"]=status; info["updated_at"]=time.time()
        if status=="working" and not str(info.get("note") or "").strip():
            last=str(info.get("last_customer") or "").strip()
            if last: info["note"]="Retomar: "+last[:180]
        items[name]=info
        self._attendance_save(); self.attendance_panel.refresh()

    def _attendance_edit_note(self):
        name=str(getattr(self,"_attendance_current_name","") or "").strip()
        if not name:
            QMessageBox.information(self,"Atendimentos","Abra a conversa do cliente no WhatsApp primeiro.")
            return
        items=self._attendance_data.setdefault("items",{})
        info=items.get(name) if isinstance(items.get(name),dict) else {}
        current=str(info.get("note") or "")
        value,ok=QInputDialog.getText(self,"O que falta fazer?",f"Pendência de {name}:",text=current)
        if ok:
            import time
            info["note"]=str(value or "").strip(); info["updated_at"]=time.time()
            items[name]=info; self._attendance_save(); self.attendance_panel.refresh()

    def _attendance_open_chat(self,name):
        name=str(name or "").strip()
        if not name:return
        js=r"""
        ((wanted)=>{
          try{
            const clean=t=>String(t||'').replace(/\s+/g,' ').trim();
            const pane=document.querySelector('#pane-side');
            if(!pane)return false;
            for(const s of Array.from(pane.querySelectorAll('span[title]'))){
              const n=clean(s.getAttribute('title')||s.textContent||'');
              if(n===wanted){
                const row=s.closest('[role="listitem"],[role="row"],[data-testid="cell-frame-container"]') || s.closest('div');
                if(row){row.click();return true;}
              }
            }
            return false;
          }catch(e){return false;}
        })(__NAME__));
        """.replace('__NAME__',json.dumps(name,ensure_ascii=False))
        def done(ok):
            if not ok:
                QMessageBox.information(self,"Atendimentos",f"{name} não está visível na lista do WhatsApp agora. Use a busca do próprio WhatsApp e abra a conversa.")
            else:
                QTimer.singleShot(650,lambda:self._attendance_scan(force=True))
        try:self.web.page().runJavaScript(js,done)
        except Exception:pass

    def _attendance_open_plate(self):
        try:
            # O fluxo novo de placa instalado nas versoes recentes abre um dialogo proprio.
            _aliyvo_show_plate_dialog(self)
        except Exception:
            try:self._open_quick_tool("plate")
            except Exception:pass

'''
text=text.replace(anchor,methods+anchor,1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched reversible attendance queue beta',version)
