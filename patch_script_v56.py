from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v56.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

def append_to_method(src,class_name,method_name,code):
    tree=ast.parse(src)
    cls=next((n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==class_name),None)
    if cls is None: raise SystemExit(f'class {class_name} not found')
    fn=next((n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==method_name),None)
    if fn is None: raise SystemExit(f'method {class_name}.{method_name} not found')
    lines=src.splitlines(keepends=True)
    pos=sum(len(x) for x in lines[:fn.end_lineno])
    if not code.endswith('\n'): code+='\n'
    return src[:pos]+code+src[pos:]

# Permite abrir o editor de lembrete ja pre-preenchido pela sugestao inteligente.
old='def _reminder_add(self,parent=None,refresh=None,force_client=None,context=None):'
new='def _reminder_add(self,parent=None,refresh=None,force_client=None,context=None,prefill_text=None,prefill_due=None):'
if old not in text: raise SystemExit('assinatura _reminder_add nao encontrada')
text=text.replace(old,new,1)
old='initial=datetime.datetime.now()+datetime.timedelta(hours=1)'
new='initial=datetime.datetime.fromtimestamp(float(prefill_due)) if prefill_due else (datetime.datetime.now()+datetime.timedelta(hours=1))'
if old not in text: raise SystemExit('initial reminder nao encontrado')
text=text.replace(old,new,1)
old='textw=QLineEdit();textw.setPlaceholderText("Ex.: fechar pedido Antiqueira")'
new='textw=QLineEdit();textw.setPlaceholderText("Ex.: fechar pedido Antiqueira");\n        if prefill_text:textw.setText(str(prefill_text))'
if old not in text: raise SystemExit('textw reminder nao encontrado')
text=text.replace(old,new,1)

anchor='    def _ai_build_context(self,mode="observer"):\n'
if anchor not in text: raise SystemExit('_ai_build_context anchor missing')
helpers=r'''    def _smart_crm_init(self):
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QPushButton
        self._smart_reminder_baseline={}
        self._smart_reminder_seen=set()
        self._smart_reminder_popup=None
        self._today_quick_btn=QPushButton("📌 Hoje",self)
        self._today_quick_btn.setToolTip("Resumo rápido do dia: esperas, lembretes e prioridades")
        self._today_quick_btn.setStyleSheet("QPushButton{background:#0f2b3d;color:white;border:1px solid #1e5f7c;border-radius:7px;padding:5px 12px;font-weight:800;} QPushButton:hover{background:#17425c;}")
        self._today_quick_btn.setFixedSize(105,32)
        self._today_quick_btn.clicked.connect(self._today_quick_panel)
        self._today_quick_btn.show();self._today_quick_btn.raise_()
        self._smart_crm_timer=QTimer(self);self._smart_crm_timer.timeout.connect(self._smart_crm_cycle);self._smart_crm_timer.start(7000)
        QTimer.singleShot(300,self._smart_crm_cycle)

    def _smart_crm_cycle(self):
        try:
            if getattr(self,"_today_quick_btn",None):
                self._today_quick_btn.move(max(900,self.width()-245),48);self._today_quick_btn.raise_()
        except Exception:pass
        try:self._smart_reminder_scan()
        except Exception as e:
            try:self._diagnostic_log("smart_reminder_error",error=str(e)[:220])
            except Exception:pass

    def _smart_reminder_parse(self,text,client):
        import re,datetime,time,unicodedata
        raw=str(text or "").strip()
        if not raw:return None
        low=''.join(c for c in unicodedata.normalize('NFD',raw.lower()) if unicodedata.category(c)!='Mn')
        # So sugere quando ha ao mesmo tempo uma acao e uma referencia futura.
        action=bool(re.search(r'\b(me liga|me chama|me avisa|me lembra|liga|chama|retorna|retorno|separa|separar|manda|mandar|envia|enviar|fatura|faturar|cobra|cobrar|confirma|confirmar)\b',low))
        future=bool(re.search(r'\b(amanha|depois|mais tarde|segunda|terca|quarta|quinta|sexta|sabado|domingo|daqui a|as\s+\d{1,2}|\d{1,2}:\d{2}|\d{1,2}h)\b',low))
        if not (action and future):return None
        now=datetime.datetime.now();due=None
        # daqui a N minutos/horas
        m=re.search(r'daqui a\s+(\d{1,3})\s*(min|minuto|minutos|h|hora|horas)',low)
        if m:
            n=int(m.group(1));due=now+datetime.timedelta(minutes=n if m.group(2).startswith('min') else n*60)
        # horario explicito
        hm=None
        for pat in (r'\b(?:as|pelas?)\s*(\d{1,2})(?::|h)?(\d{2})?\b',r'\b(\d{1,2}):(\d{2})\b',r'\b(\d{1,2})h(\d{2})?\b'):
            m=re.search(pat,low)
            if m:
                try:
                    hh=int(m.group(1));mm=int(m.group(2) or 0)
                    if 0<=hh<=23 and 0<=mm<=59:hm=(hh,mm);break
                except Exception:pass
        base=now
        if 'amanha' in low:base=now+datetime.timedelta(days=1)
        weekdays={'segunda':0,'terca':1,'quarta':2,'quinta':3,'sexta':4,'sabado':5,'domingo':6}
        for word,wd in weekdays.items():
            if word in low:
                add=(wd-now.weekday())%7
                if add==0:add=7
                base=now+datetime.timedelta(days=add);break
        if hm:
            due=base.replace(hour=hm[0],minute=hm[1],second=0,microsecond=0)
            if due<=now and 'amanha' not in low and not any(w in low for w in weekdays):due+=datetime.timedelta(days=1)
        elif due is None:
            if 'depois do almoco' in low or 'apos o almoco' in low:due=base.replace(hour=13,minute=30,second=0,microsecond=0)
            elif 'mais tarde' in low:due=now+datetime.timedelta(hours=2)
            elif 'amanha' in low:due=base.replace(hour=9,minute=0,second=0,microsecond=0)
            elif any(w in low for w in weekdays):due=base.replace(hour=9,minute=0,second=0,microsecond=0)
        if due is None:return None
        c=str(client or 'cliente').strip()
        if re.search(r'\b(me liga|liga)\b',low):title=f"Ligar para {c}"
        elif re.search(r'\b(separa|separar)\b',low):title=f"Separar / confirmar para {c}"
        elif re.search(r'\b(fatura|faturar)\b',low):title=f"Faturar pedido de {c}"
        elif re.search(r'\b(manda|mandar|envia|enviar)\b',low):title=f"Enviar retorno para {c}"
        elif re.search(r'\b(cobra|cobrar)\b',low):title=f"Cobrar retorno de {c}"
        else:title=f"Retornar para {c}"
        return {"title":title,"due_ts":due.timestamp(),"snippet":raw[-450:]}

    def _smart_reminder_scan(self):
        import hashlib
        name=str(getattr(self,"_diagnostic_active_name","") or "").strip()
        if not name:return
        try:
            if name in set(self._diagnostic_groups_load()):return
        except Exception:pass
        ctx=str((getattr(self,"_diagnostic_last_context_by_contact",{}) or {}).get(name) or "").strip()
        if not ctx:return
        digest=hashlib.sha1(ctx.encode('utf-8','ignore')).hexdigest()
        old=self._smart_reminder_baseline.get(name)
        self._smart_reminder_baseline[name]=digest
        if old is None or old==digest:return
        # examina somente o final novo/proximo do contexto e evita oferecer a mesma sugestao de novo.
        tail=ctx[-900:]
        parsed=self._smart_reminder_parse(tail,name)
        if not parsed:return
        key=hashlib.sha1((name+'|'+parsed['title']+'|'+str(int(parsed['due_ts']//300))+'|'+parsed['snippet'][-180:]).encode('utf-8','ignore')).hexdigest()
        if key in self._smart_reminder_seen:return
        # evita duplicar tarefa equivalente ja existente no mesmo cliente e horario aproximado.
        for r in getattr(self,"_reminders",[]) or []:
            if not isinstance(r,dict) or r.get('done'):continue
            if str(r.get('client') or '').strip()!=name:continue
            try:
                if abs(float(r.get('due_ts') or 0)-float(parsed['due_ts']))<1800 and parsed['title'].lower()[:12] in str(r.get('text') or '').lower():
                    self._smart_reminder_seen.add(key);return
            except Exception:pass
        self._smart_reminder_seen.add(key);self._smart_reminder_offer(name,ctx,parsed)

    def _smart_reminder_offer(self,client,context,parsed):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QLabel,QHBoxLayout,QPushButton
        from PyQt6.QtCore import Qt
        import datetime
        try:
            if self._smart_reminder_popup and self._smart_reminder_popup.isVisible():return
        except Exception:pass
        dlg=QDialog(self);self._smart_reminder_popup=dlg;dlg.setWindowTitle("💡 Sugestão de lembrete");dlg.setModal(False);dlg.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint,True);dlg.resize(520,220)
        lay=QVBoxLayout(dlg);head=QLabel("A conversa parece ter uma tarefa futura");head.setStyleSheet("font-size:14px;font-weight:900;color:#0b5d44;");lay.addWidget(head)
        when=datetime.datetime.fromtimestamp(float(parsed['due_ts'])).strftime('%d/%m/%Y às %H:%M')
        task=QLabel(f"<b>{parsed['title']}</b><br>{when}<br><span style='color:#61717f'>Cliente: {client}</span>");task.setWordWrap(True);lay.addWidget(task)
        snippet=QLabel("Trecho observado: “"+str(parsed.get('snippet') or '')[-220:].replace('\n',' ')+'”');snippet.setWordWrap(True);snippet.setStyleSheet("color:#59636d;font-size:10px;");lay.addWidget(snippet)
        row=QHBoxLayout();create=QPushButton("⏰ Criar lembrete");ignore=QPushButton("Ignorar");row.addWidget(create);row.addStretch(1);row.addWidget(ignore);lay.addLayout(row)
        create.clicked.connect(lambda:(dlg.accept(),self._reminder_add(self,None,force_client=client,context=context,prefill_text=parsed['title'],prefill_due=parsed['due_ts'])))
        ignore.clicked.connect(dlg.reject);dlg.finished.connect(lambda _=0:setattr(self,'_smart_reminder_popup',None));dlg.show();dlg.raise_();dlg.activateWindow()

    def _today_quick_panel(self):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QLabel,QHBoxLayout,QPushButton,QScrollArea,QWidget
        import datetime,time
        now=time.time();today=datetime.date.today();pending=[r for r in getattr(self,'_reminders',[]) or [] if isinstance(r,dict) and not r.get('done')]
        overdue=sorted([r for r in pending if float(r.get('due_ts') or 0) and float(r.get('due_ts') or 0)<now],key=lambda r:float(r.get('due_ts') or 0))
        today_rows=sorted([r for r in pending if float(r.get('due_ts') or 0) and datetime.datetime.fromtimestamp(float(r.get('due_ts'))).date()==today],key=lambda r:float(r.get('due_ts') or 0))
        try:waiting=self._diagnostic_waiting_snapshot() or []
        except Exception:waiting=[]
        candidates=set()
        for w in waiting:
            n=str(w.get('client') or '').strip()
            if n:candidates.add(n)
        for r in pending:
            n=str(r.get('client') or '').strip()
            if n:candidates.add(n)
        priorities=[]
        for n in candidates:
            try:pri=self._ai_priority_for_client(n);priorities.append((int(pri.get('score') or 0),n,pri))
            except Exception:pass
        priorities.sort(reverse=True,key=lambda x:x[0]);priorities=priorities[:3]
        dlg=QDialog(self);dlg.setWindowTitle("📌 Hoje — painel rápido");dlg.resize(650,650);lay=QVBoxLayout(dlg)
        title=QLabel("HOJE NO ALIYVO");title.setStyleSheet("font-size:16px;font-weight:900;color:#07344a;");lay.addWidget(title)
        def section(title_txt,items,bg,fg):
            h=QLabel(title_txt);h.setStyleSheet(f"font-size:12px;font-weight:900;color:{fg};margin-top:8px;");lay.addWidget(h)
            if not items:
                x=QLabel("Nenhum item agora.");x.setStyleSheet("color:#6c7780;padding:4px 10px;");lay.addWidget(x);return
            for txt in items:
                x=QLabel(txt);x.setWordWrap(True);x.setStyleSheet(f"background:{bg};color:{fg};border-radius:7px;padding:8px 10px;font-weight:700;");lay.addWidget(x)
        wait_items=[]
        for w in waiting[:8]:
            n=str(w.get('client') or 'Cliente');sec=float(w.get('wait_seconds') or w.get('business_wait_seconds') or w.get('total_wait_seconds') or 0);wait_items.append(f"{n}  •  aguardando {int(sec//60)} min úteis")
        section(f"💬 CLIENTES ESPERANDO ({len(waiting)})",wait_items,"#e7f3ff","#16558c")
        over_items=[f"{datetime.datetime.fromtimestamp(float(r.get('due_ts'))).strftime('%H:%M')}  •  {r.get('text')}"+(f"  — {r.get('client')}" if r.get('client') else '') for r in overdue[:6]]
        section(f"🔴 VENCIDOS ({len(overdue)})",over_items,"#ffd9de","#9e1027")
        today_items=[f"{datetime.datetime.fromtimestamp(float(r.get('due_ts'))).strftime('%H:%M')}  •  {r.get('text')}"+(f"  — {r.get('client')}" if r.get('client') else '') for r in today_rows if r not in overdue][:8]
        section(f"🟡 TAREFAS DE HOJE ({len(today_rows)})",today_items,"#fff4bf","#715a00")
        pri_items=[]
        for score,n,pri in priorities:
            reasons='; '.join(pri.get('reasons') or []) or 'histórico e pendências atuais'
            pri_items.append(f"{n}  •  prioridade {str(pri.get('level') or '').upper()} ({score})\n{reasons}")
        section("⭐ 3 PRIORIDADES SUGERIDAS",pri_items,"#e8f7ee","#176b3a")
        row=QHBoxLayout();crm=QPushButton("🧭 Abrir CRM do dia");rem=QPushButton("⏰ Lembretes");close=QPushButton("Fechar");row.addWidget(crm);row.addWidget(rem);row.addStretch(1);row.addWidget(close);lay.addLayout(row)
        crm.clicked.connect(lambda:self._ai_crm_reminders_dialog(dlg));rem.clicked.connect(lambda:self._reminder_show_dialog());close.clicked.connect(dlg.accept);dlg.exec()

'''
text=text.replace(anchor,helpers+anchor,1)

# Inicializa o detector e o botao Hoje sem interferir na inicializacao principal.
text=append_to_method(text,'MainWindow','__init__','        from PyQt6.QtCore import QTimer\n        QTimer.singleShot(1800,self._smart_crm_init)\n')

p.write_text(text,encoding='utf-8')
print('patched smart reminder + today panel',version)
