from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v28.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.42 - fila mais legivel e mais automatica.
# Mantem integralmente o botao de retorno ao modo atual da v0.22.41.


def replace_method(src,class_name,method_name,new_code):
    tree=ast.parse(src)
    cls=None
    for n in tree.body:
        if isinstance(n,ast.ClassDef) and n.name==class_name:
            cls=n; break
    if cls is None:
        raise SystemExit(f'class {class_name} not found')
    target=None
    for n in cls.body:
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==method_name:
            target=n; break
    if target is None:
        raise SystemExit(f'method {class_name}.{method_name} not found')
    lines=src.splitlines(keepends=True)
    start=sum(len(x) for x in lines[:target.lineno-1])
    end=sum(len(x) for x in lines[:target.end_lineno])
    if not new_code.endswith('\n'):
        new_code+='\n'
    return src[:start]+new_code+src[end:]

# Legibilidade: painel mais largo, fila e contexto com fontes maiores/negrito.
text=text.replace(
    'border-radius:7px;padding:3px;font-size:10px;',
    'border-radius:7px;padding:3px;font-size:11px;font-weight:700;',
    1
)
text=text.replace(
    'QWidget#aliyvoAttendancePanel QListWidget::item{padding:8px;border-bottom:1px solid #12374D;}',
    'QWidget#aliyvoAttendancePanel QListWidget::item{padding:9px;border-bottom:1px solid #12374D;}',
    1
)
text=text.replace(
    'self.resume.setStyleSheet("color:#C8D8E2;font-size:9px;padding:2px 3px;")',
    'self.resume.setStyleSheet("color:#E8F1F5;font-size:10px;font-weight:700;padding:3px 3px;")\n        self.resume.setTextFormat(Qt.TextFormat.RichText)',
    1
)
text=text.replace(
    'self.current.setWordWrap(True)',
    'self.current.setWordWrap(True)\n        self.current.setTextFormat(Qt.TextFormat.RichText)',
    1
)
text=text.replace('self.quick_host.setFixedWidth(345)','self.quick_host.setFixedWidth(390)',1)

# Resumo de fila no topo.
anchor='''        lay.addWidget(sub)\n\n        self.current=QLabel("Abra uma conversa no WhatsApp")'''
if anchor not in text:
    raise SystemExit('attendance summary anchor not found')
text=text.replace(anchor,''''        lay.addWidget(sub)\n\n        self.summary=QLabel("🔥 0 responder  •  🟠 0 andamento  •  🔵 0 aguardando")\n        self.summary.setWordWrap(True)\n        self.summary.setStyleSheet("background:#061626;border:1px solid #173B52;border-radius:6px;padding:6px;color:#FFFFFF;font-size:10px;font-weight:800;")\n        lay.addWidget(self.summary)\n\n        self.current=QLabel("Abra uma conversa no WhatsApp")''',1)

# Por padrao, mostra so as 5 maiores prioridades; opcao para expandir.
anchor='''        self.show_resolved=QCheckBox("Mostrar resolvidos")\n        lay.addWidget(self.show_resolved)'''
if anchor not in text:
    raise SystemExit('show resolved anchor not found')
text=text.replace(anchor,''''        self.show_all=QCheckBox("Mostrar toda a fila")\n        lay.addWidget(self.show_all)\n        self.show_resolved=QCheckBox("Mostrar resolvidos")\n        lay.addWidget(self.show_resolved)''',1)
text=text.replace(
    'self.show_resolved.stateChanged.connect(lambda *_:self.refresh())',
    'self.show_all.stateChanged.connect(lambda *_:self.refresh())\n        self.show_resolved.stateChanged.connect(lambda *_:self.refresh())',
    1
)

# Ferramentas abertas passam a ser registradas no atendimento atual.
text=text.replace(
    'self.tool_soma.clicked.connect(lambda:self.owner._open_quick_tool("technical"))',
    'self.tool_soma.clicked.connect(lambda:self.owner._attendance_open_tool("technical"))',1)
text=text.replace(
    'self.tool_image.clicked.connect(lambda:self.owner._open_quick_tool("lens"))',
    'self.tool_image.clicked.connect(lambda:self.owner._attendance_open_tool("lens"))',1)
text=text.replace(
    'self.tool_audio.clicked.connect(lambda:self.owner._open_quick_tool("audio"))',
    'self.tool_audio.clicked.connect(lambda:self.owner._attendance_open_tool("audio"))',1)

new_refresh=r'''    def refresh(self):
        import html as _html
        data=getattr(self.owner,"_attendance_data",{}) or {}
        items=data.get("items",{}) if isinstance(data,dict) else {}
        current=getattr(self.owner,"_attendance_current_name","") or ""

        counts={"reply":0,"working":0,"waiting":0,"resolved":0}
        unread_total=0
        for _name,_info in items.items():
            if not isinstance(_info,dict):
                continue
            _st=str(_info.get("status") or "reply")
            counts[_st]=counts.get(_st,0)+1
            if bool(_info.get("unread")):
                unread_total+=1
        self.summary.setText(
            f"🔥 {counts.get('reply',0)} RESPONDER  •  🟠 {counts.get('working',0)} ANDAMENTO  •  "
            f"🔵 {counts.get('waiting',0)} AGUARDANDO  •  🔴 {unread_total} NÃO LIDOS"
        )

        if current:
            info=items.get(current,{})
            status=str(info.get("status") or "reply")
            emo,label,color=self.STATUS_META.get(status,self.STATUS_META["reply"])
            age_ts=(info.get("reply_since") if status=="reply" else
                    info.get("working_since") if status=="working" else
                    info.get("waiting_since") if status=="waiting" else
                    info.get("updated_at"))
            age=self._age(age_ts)
            unread=' • 🔴 NÃO LIDO' if info.get("unread") else ''
            priority=' • ⚠ COBROU DE NOVO' if info.get("priority") else ''
            self.current.setText(
                f"<b>{_html.escape(emo+' '+current)}</b><br>"
                f"<b>{_html.escape(label.upper())} • {_html.escape(age)}{_html.escape(unread)}{_html.escape(priority)}</b>"
            )
            self.current.setStyleSheet(
                f"background:#0A2236;border:2px solid {color};border-radius:7px;"
                "padding:9px;font-size:12px;font-weight:800;color:#FFFFFF;"
            )

            note=str(info.get("note") or "").strip()
            last=str(info.get("last_customer") or "").strip()
            codes=info.get("codes") or []
            plate=str(info.get("plate") or "")
            request_items=info.get("request_items") or []
            pending_questions=info.get("pending_questions") or []
            last_tool=str(info.get("last_tool_label") or "").strip()
            bits=[]
            if note:
                bits.append("<b>📌 FALTA FAZER:</b> "+_html.escape(note))
            elif last:
                bits.append("<b>🧠 VOCÊ PAROU AQUI:</b> "+_html.escape(last[:180]))
            if request_items:
                compact=[_html.escape(str(x)[:105]) for x in request_items[-3:]]
                bits.append("<b>📋 PEDIDO RECENTE:</b> "+" • ".join(compact))
            if pending_questions:
                bits.append("<b>⚠ PERGUNTA PENDENTE:</b> "+_html.escape(str(pending_questions[-1])[:180]))
            if codes:
                bits.append("<b>🔢 CÓDIGOS:</b> "+_html.escape(", ".join(str(x) for x in codes[:6])))
            if plate:
                bits.append("<b>🚚 PLACA:</b> "+_html.escape(plate))
            if last_tool:
                bits.append("<b>🛠 ÚLTIMA FERRAMENTA:</b> "+_html.escape(last_tool))
            self.resume.setText("<br>".join(bits) if bits else "<b>Nenhuma pendência anotada.</b>")
        else:
            self.current.setText("<b>Abra uma conversa no WhatsApp</b>")
            self.current.setStyleSheet("background:#0A2236;border:1px solid #173B52;border-radius:7px;padding:9px;font-size:12px;font-weight:800;color:#FFFFFF;")
            self.resume.setText("<b>A fila continua guardada mesmo quando você troca de cliente.</b>")

        old_selected=self.selected_name
        self.list.clear()
        rows=[]
        status_weight={"reply":0,"working":1,"waiting":2,"resolved":3}
        now_sort=10**20
        for name,info in items.items():
            if not isinstance(info,dict):
                continue
            st=str(info.get("status") or "reply")
            if st=="resolved" and not self.show_resolved.isChecked():
                continue
            priority_rank=0 if bool(info.get("priority")) else 1
            if st=="reply":
                ts=float(info.get("reply_since") or info.get("updated_at") or now_sort)
            elif st=="working":
                ts=float(info.get("working_since") or info.get("updated_at") or now_sort)
            else:
                ts=float(info.get("updated_at") or now_sort)
            rows.append((status_weight.get(st,9),priority_rank,ts,str(name),info))
        rows.sort(key=lambda x:(x[0],x[1],x[2],x[3].lower()))

        total_visible=len(rows)
        if not self.show_all.isChecked() and not self.show_resolved.isChecked():
            rows=rows[:5]
        pending=sum(1 for _n,_i in items.items() if isinstance(_i,dict) and str(_i.get("status") or "")!="resolved")
        self.count.setText(f"{pending} pendente(s)" + (f" • mostrando {len(rows)}/{total_visible}" if total_visible>len(rows) else ""))

        for _,__,___,name,info in rows:
            st=str(info.get("status") or "reply")
            emo,label,color=self.STATUS_META.get(st,self.STATUS_META["reply"])
            ts=(info.get("reply_since") if st=="reply" else
                info.get("working_since") if st=="working" else
                info.get("waiting_since") if st=="waiting" else
                info.get("updated_at"))
            age=self._age(ts)
            excerpt=str(info.get("note") or info.get("last_customer") or info.get("snippet") or "").replace("\n"," ").strip()
            if len(excerpt)>78:
                excerpt=excerpt[:75]+"..."
            flags=[]
            if info.get("priority"):
                flags.append("⚠ COBROU")
            if info.get("unread"):
                flags.append("🔴 NÃO LIDO")
            status_line=f"{label.upper()} • ⏱ {age}"
            if flags:
                status_line+=" • "+" • ".join(flags)
            line=f"{emo} {name}\n{status_line}"
            if excerpt:
                line+="\n"+excerpt
            it=QListWidgetItem(line)
            it.setData(Qt.ItemDataRole.UserRole,name)
            try:
                it.setForeground(QColor("#FFFFFF"))
                f=it.font(); f.setBold(True)
                if f.pointSize()<10: f.setPointSize(10)
                it.setFont(f)
            except Exception:
                pass
            self.list.addItem(it)
            if name==old_selected or (not old_selected and name==current):
                self.list.setCurrentItem(it)
        if not self.list.currentItem() and self.list.count():
            self.list.setCurrentRow(0)
'''
text=replace_method(text,'AliyvoAttendancePanel','refresh',new_refresh)

new_scan_done=r'''    def _attendance_scan_done(self,result):
        self._attendance_scan_busy=False
        if not isinstance(result,dict) or not result.get("ok"):
            return
        import time,re as _re
        now=time.time()
        items=self._attendance_data.setdefault("items",{})

        # O selo de não lido é um sinal adicional, nunca o único critério da fila.
        for _info in items.values():
            if isinstance(_info,dict):
                _info["unread"]=False

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
            previous_status=str(info.get("status") or "")
            info["name"]=name
            info["last_seen"]=now
            info["context"]=context[-12:]

            customers=[str(x.get("text") or "").strip() for x in context if isinstance(x,dict) and x.get("side")=="customer" and str(x.get("text") or "").strip()]
            sellers=[str(x.get("text") or "").strip() for x in context if isinstance(x,dict) and x.get("side")=="seller" and str(x.get("text") or "").strip()]
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
            except Exception:
                pass

            # Perguntas do cliente depois da nossa ultima resposta ficam destacadas.
            last_seller_idx=-1
            for idx,x in enumerate(context):
                if isinstance(x,dict) and x.get("side")=="seller":
                    last_seller_idx=idx
            pending=[]
            for x in context[last_seller_idx+1:]:
                if not isinstance(x,dict) or x.get("side")!="customer":
                    continue
                t=str(x.get("text") or "").strip()
                if '?' in t and 2<len(t)<=300:
                    pending.append(t)
            info["pending_questions"]=pending[-4:]

            # Pequeno resumo do pedido recente, removendo saudacoes/cobrancas curtas.
            request_items=[]
            for msg in customers[-6:]:
                t=_re.sub(r'\s+',' ',msg).strip()
                low=t.lower()
                if len(t)<4: continue
                if low in {"bom dia","boa tarde","boa noite","oi","ola","olá","obrigado","valeu"}: continue
                if _re.fullmatch(r'[?!.\s]{1,8}',t): continue
                if _re.search(r'\b(conseguiu|aguardo|alguma novidade|viu pra mim|me retorna|retorno)\b',low) and len(t)<65:
                    continue
                if t not in request_items:
                    request_items.append(t[:150])
            info["request_items"]=request_items[-4:]

            # Cobranças curtas ganham prioridade sobre a ordem cronologica normal.
            low_last=_re.sub(r'\s+',' ',last_text.lower()).strip()
            priority=False
            if side=="customer":
                if _re.fullmatch(r'[?!.\s]{1,8}',last_text):
                    priority='?' in last_text
                if _re.search(r'\b(conseguiu|aguardo|novidade|retorno|viu pra mim|conseguiu ver|me retorna|me dá um retorno|me da um retorno)\b',low_last):
                    priority=True
            info["priority"]=bool(priority)

            if changed:
                info["last_signature"]=signature
                info["updated_at"]=now
                if side=="customer":
                    if previous_status=="resolved":
                        info["cycle_count"]=int(info.get("cycle_count") or 0)+1
                        info["note"]=""
                    info["status"]="reply"
                    info["reply_since"]=now
                    info["waiting_since"]=0
                elif side=="seller":
                    info["status"]="waiting"
                    info["waiting_since"]=now
                    info["reply_since"]=0
                    info["priority"]=False
            elif "status" not in info:
                if side=="seller":
                    info["status"]="waiting"; info["waiting_since"]=now
                else:
                    info["status"]="reply"; info["reply_since"]=now
                info["updated_at"]=now
            items[name]=info
        else:
            self._attendance_current_name=""

        unread_names=set()
        for row in (result.get("unread") or []):
            if not isinstance(row,dict):
                continue
            n=str(row.get("name") or "").strip()
            if not n:
                continue
            unread_names.add(n)
            info=items.get(n) if isinstance(items.get(n),dict) else {}
            info["name"]=n
            info["unread"]=True
            info["snippet"]=str(row.get("snippet") or "")[-180:]
            if str(info.get("status") or "")!="reply":
                info["status"]="reply"
                info["updated_at"]=now
                info["reply_since"]=now
            elif not info.get("reply_since"):
                info["reply_since"]=float(info.get("updated_at") or now)
            items[n]=info

        self._attendance_data["last_scan_at"]=now
        self._attendance_save()
        try:self.attendance_panel.refresh()
        except Exception:pass
'''
text=replace_method(text,'MainWindow','_attendance_scan_done',new_scan_done)

new_mark=r'''    def _attendance_mark(self,status):
        name=str(getattr(self,"_attendance_current_name","") or "").strip()
        if not name:
            QMessageBox.information(self,"Atendimentos","Abra a conversa do cliente no WhatsApp primeiro.")
            return
        import time
        now=time.time()
        items=self._attendance_data.setdefault("items",{})
        info=items.get(name) if isinstance(items.get(name),dict) else {}
        info["name"]=name; info["status"]=status; info["updated_at"]=now
        if status=="working":
            info["working_since"]=now
            if not str(info.get("note") or "").strip():
                last=str(info.get("last_customer") or "").strip()
                if last: info["note"]="Retomar: "+last[:180]
        elif status=="reply":
            info["reply_since"]=now
        elif status=="waiting":
            info["waiting_since"]=now
            info["priority"]=False
        elif status=="resolved":
            info["resolved_at"]=now
            info["priority"]=False
        items[name]=info
        self._attendance_save(); self.attendance_panel.refresh()
'''
text=replace_method(text,'MainWindow','_attendance_mark',new_mark)

# Registra qual ferramenta pertence ao cliente atual antes de abri-la.
insert_anchor='''    def _attendance_open_plate(self):\n'''
if insert_anchor not in text:
    raise SystemExit('attendance open plate anchor not found')
open_tool=r'''    def _attendance_open_tool(self,tool):
        labels={"technical":"Busca Somaforce","lens":"Busca por imagem","audio":"Áudio","plate":"Placa/chassi"}
        name=str(getattr(self,"_attendance_current_name","") or "").strip()
        if name:
            try:
                import time
                items=self._attendance_data.setdefault("items",{})
                info=items.get(name) if isinstance(items.get(name),dict) else {}
                info["last_tool"]=str(tool)
                info["last_tool_label"]=labels.get(str(tool),str(tool))
                info["tool_opened_at"]=time.time()
                items[name]=info
                self._attendance_save()
                self.attendance_panel.refresh()
            except Exception:
                pass
        self._open_quick_tool(tool)

'''
text=text.replace(insert_anchor,open_tool+insert_anchor,1)

# Placa/chassi tambem fica associada ao cliente atual.
old='''    def _attendance_open_plate(self):\n        try:\n            # O fluxo novo de placa instalado nas versoes recentes abre um dialogo proprio.'''
if old in text:
    text=text.replace(old,'''    def _attendance_open_plate(self):\n        try:\n            name=str(getattr(self,"_attendance_current_name","") or "").strip()\n            if name:\n                import time\n                items=self._attendance_data.setdefault("items",{})\n                info=items.get(name) if isinstance(items.get(name),dict) else {}\n                info["last_tool"]="plate"; info["last_tool_label"]="Placa/chassi"; info["tool_opened_at"]=time.time()\n                items[name]=info; self._attendance_save(); self.attendance_panel.refresh()\n        except Exception:\n            pass\n        try:\n            # O fluxo novo de placa instalado nas versoes recentes abre um dialogo proprio.''',1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched smarter/bolder attendance queue',version)
