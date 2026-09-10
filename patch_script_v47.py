from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v47.json').read_text(encoding='utf-8'))
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

# ---------------------------------------------------------------------
# IA Observadora 2: aprendizado LOCAL, incremental e auditavel.
# Nada aqui envia mensagens; apenas organiza fatos ja observados.
# ---------------------------------------------------------------------
anchor='    def _ai_build_context(self,mode="observer"):\n'
if anchor not in text: raise SystemExit('_ai_build_context anchor not found')
helpers=r'''    def _ai_learning_path(self):
        return USER_DATA_DIR/"ia_observadora_aprendizado.json"

    def _ai_learning_empty(self):
        return {"version":1,"last_processed_ts":0.0,"patterns":{},"seller_phrases":{},"updated_at":""}

    def _ai_learning_load(self):
        data=self._ai_learning_empty()
        try:
            p=self._ai_learning_path()
            if p.exists():
                d=json.loads(p.read_text(encoding="utf-8"))
                if isinstance(d,dict):data.update(d)
        except Exception:pass
        if not isinstance(data.get("patterns"),dict):data["patterns"]={}
        if not isinstance(data.get("seller_phrases"),dict):data["seller_phrases"]={}
        return data

    def _ai_learning_save(self,data):
        try:
            import datetime
            USER_DATA_DIR.mkdir(parents=True,exist_ok=True)
            data["updated_at"]=datetime.datetime.now().isoformat(timespec="seconds")
            self._ai_learning_path().write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
            return True
        except Exception:return False

    def _ai_learning_norm(self,value):
        import unicodedata,re as _re
        s=str(value or "").lower().strip()
        s="".join(c for c in unicodedata.normalize("NFD",s) if unicodedata.category(c)!="Mn")
        s=_re.sub(r"\s+"," ",s)
        return s

    def _ai_learning_categories(self,row):
        if not isinstance(row,dict):return []
        raw=" ".join(str(row.get(k) or "") for k in ("text","snippet","row_text","tool","event","content_type"))
        s=self._ai_learning_norm(raw)
        event=self._ai_learning_norm(row.get("event"))
        tool=self._ai_learning_norm(row.get("tool"))
        found=[]
        def add(key,label,weight):
            if not any(x[0]==key for x in found):found.append((key,label,float(weight)))
        if any(x in s for x in ("preco","valor","quanto","cotacao","orcamento","oferecendo")):
            add("consulta_preco","Consulta de preço/orçamento",3.0)
        if any(x in s for x in ("pre-venda","pre venda","prevenda","separar","separa pra","reservar","reserva","deixa uma","deixe uma")):
            add("pre_venda","Separação / pré-venda / reserva",3.2)
        if any(x in s for x in ("desconto","melhor preco","consegue fazer","consigo fazer","oferecendo","fechar por","chegar em","negocia")):
            add("negociacao","Negociação de preço",2.7)
        if tool=="prazo" or any(x in s for x in ("prazo","parcela","boleto","30/60","20/40","28/56","dias para pagar")):
            add("prazo_pagamento","Consulta de prazo/condição",2.8)
        if any(x in s for x in ("tem em estoque","tem dispon","disponivel","disponibilidade","tem essa","tem esse","consegue uma","consegue duas")):
            add("estoque","Disponibilidade / estoque",2.5)
        if any(x in s for x in ("codigo","cod ","referencia","original","aplica","aplicacao")):
            add("codigo_aplicacao","Código / referência / aplicação",2.6)
        if tool in ("plate","placa","chassi") or any(x in s for x in ("placa","chassi")):
            add("placa_chassi","Consulta por placa/chassi",2.4)
        if tool in ("lens","image","imagem") or "busca por imagem" in s:
            add("busca_imagem","Busca por imagem",2.4)
        if "call" in event or "ligacao" in event or row.get("duration_seconds") not in (None,""):
            add("ligacoes","Ligações com clientes",1.8)
        try:
            wait=float(row.get("response_seconds") or row.get("total_wait_seconds") or 0)
            if 300<=wait<=172800:add("espera_5min","Atendimento com espera acima de 5 min úteis",2.2)
        except Exception:pass
        try:
            if int(row.get("interruptions") or 0)>0 or "interrupt" in event:
                add("interrupcoes","Atendimentos interrompidos",2.3)
        except Exception:pass
        ctype=self._ai_learning_norm(row.get("content_type"))
        if ctype in ("audio","voice","ptt"):
            add("audio_recebido","Áudios recebidos no WhatsApp",1.4)
        return found

    def _ai_learning_refresh(self):
        import datetime
        data=self._ai_learning_load();last=float(data.get("last_processed_ts") or 0);rows=[]
        try:rows=list(self._diagnostic_read() or [])
        except Exception:rows=[]
        fresh=[]
        for row in rows:
            if not isinstance(row,dict):continue
            try:ts=float(row.get("ts") or 0)
            except Exception:ts=0
            if ts>last:fresh.append((ts,row))
        if not fresh:return data
        fresh.sort(key=lambda x:x[0]);max_ts=last
        for ts,row in fresh:
            max_ts=max(max_ts,ts)
            client=str(row.get("client") or "").strip()
            stamp=str(row.get("time") or "")[:19]
            example=str(row.get("text") or row.get("snippet") or row.get("row_text") or "").strip()[:180]
            for key,label,weight in self._ai_learning_categories(row):
                rec=data["patterns"].get(key)
                if not isinstance(rec,dict):
                    rec={"label":label,"count":0,"weight":weight,"first_seen":stamp,"last_seen":stamp,"clients":[],"examples":[]}
                rec["label"]=label;rec["weight"]=weight;rec["count"]=int(rec.get("count") or 0)+1
                if not rec.get("first_seen"):rec["first_seen"]=stamp
                rec["last_seen"]=stamp
                clients=list(rec.get("clients") or [])
                if client and client not in clients:clients.append(client)
                rec["clients"]=clients[-40:]
                examples=list(rec.get("examples") or [])
                if example and example not in examples:examples.append(example)
                rec["examples"]=examples[-5:]
                data["patterns"][key]=rec
            # Aprende frases curtas do vendedor sem afirmar significado.
            ev=self._ai_learning_norm(row.get("event"));direction=self._ai_learning_norm(row.get("direction"))
            msg=str(row.get("text") or "").strip()
            seller=("seller" in ev or direction in ("out","outgoing","seller","me","mine"))
            if seller and 1<=len(msg)<=90:
                norm=self._ai_learning_norm(msg)
                if norm:
                    rec=data["seller_phrases"].get(norm) or {"text":msg,"count":0,"last_seen":stamp}
                    rec["text"]=msg;rec["count"]=int(rec.get("count") or 0)+1;rec["last_seen"]=stamp
                    data["seller_phrases"][norm]=rec
        # Evita crescimento infinito de frases raras.
        phrases=sorted(data["seller_phrases"].items(),key=lambda kv:(int((kv[1] or {}).get("count") or 0),str((kv[1] or {}).get("last_seen") or "")),reverse=True)[:80]
        data["seller_phrases"]={k:v for k,v in phrases}
        data["last_processed_ts"]=max_ts
        self._ai_learning_save(data)
        return data

    def _ai_learning_summary_payload(self,refresh=True):
        data=self._ai_learning_refresh() if refresh else self._ai_learning_load()
        out=[]
        for key,rec in (data.get("patterns") or {}).items():
            if not isinstance(rec,dict):continue
            count=int(rec.get("count") or 0);weight=float(rec.get("weight") or 1)
            conf="alta" if count>=12 else ("média" if count>=5 else "observando")
            out.append({"key":key,"label":rec.get("label") or key,"count":count,"clients_count":len(rec.get("clients") or []),"confidence":conf,"automation_score":round(count*weight,1),"last_seen":rec.get("last_seen") or "","examples":list(rec.get("examples") or [])[-2:]})
        out.sort(key=lambda x:(x["automation_score"],x["count"]),reverse=True)
        phrases=[]
        for rec in (data.get("seller_phrases") or {}).values():
            if isinstance(rec,dict) and int(rec.get("count") or 0)>=2:
                phrases.append({"text":str(rec.get("text") or "")[:90],"count":int(rec.get("count") or 0)})
        phrases.sort(key=lambda x:x["count"],reverse=True)
        return {"updated_at":data.get("updated_at") or "","patterns":out[:15],"top_seller_phrases":phrases[:10]}

    def _ai_learning_text(self):
        learn=self._ai_learning_summary_payload(True);patterns=learn.get("patterns") or []
        if not patterns:return "A IA ainda está juntando evidências. Use o ALIYVO normalmente e ela começará a confirmar padrões."
        confirmed=[x for x in patterns if x.get("confidence") in ("alta","média")]
        observing=[x for x in patterns if x.get("confidence")=="observando"]
        lines=["APRENDIZADO ACUMULADO DA IA","", "PADRÕES CONFIRMADOS"]
        if confirmed:
            for x in confirmed[:10]:lines.append(f"• {x['label']}: {x['count']} ocorrência(s) • {x['clients_count']} cliente(s) • confiança {x['confidence']}")
        else:lines.append("• Ainda não há padrão com evidência suficiente.")
        lines += ["", "RANKING PARA FUTURA AUTOMAÇÃO"]
        for i,x in enumerate(patterns[:8],1):lines.append(f"{i}. {x['label']} — {x['count']} ocorrência(s) • índice {x['automation_score']}")
        if observing:
            lines += ["", "AINDA OBSERVANDO"]
            for x in observing[:6]:lines.append(f"• {x['label']}: {x['count']} ocorrência(s)")
        phrases=learn.get("top_seller_phrases") or []
        if phrases:
            lines += ["", "FRASES CURTAS QUE VOCÊ REPETE"]
            for x in phrases[:7]:lines.append(f"• {x['text']} — {x['count']}x")
        lines += ["", "Importante: contagem = fato observado no diagnóstico. Prioridade de automação = sugestão calculada; não significa que a automação já existe."]
        return "\n".join(lines)

    def _ai_learning_dialog(self,parent=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QPlainTextEdit,QPushButton,QHBoxLayout
        dlg=QDialog(parent or self);dlg.setWindowTitle("📚 Aprendizado da IA Observadora");dlg.resize(820,650)
        lay=QVBoxLayout(dlg);txt=QPlainTextEdit();txt.setReadOnly(True);txt.setPlainText(self._ai_learning_text());lay.addWidget(txt,1)
        row=QHBoxLayout();refresh=QPushButton("↻ Atualizar aprendizado");close=QPushButton("Fechar");row.addWidget(refresh);row.addStretch(1);row.addWidget(close);lay.addLayout(row)
        refresh.clicked.connect(lambda:txt.setPlainText(self._ai_learning_text()));close.clicked.connect(dlg.accept);dlg.exec()

'''
text=text.replace(anchor,helpers+anchor,1)

new_build=r'''    def _ai_build_context(self,mode="observer"):
        import datetime,time
        today=datetime.date.today().isoformat();groups=set(self._diagnostic_groups_load());rows=[]
        for x in self._diagnostic_read():
            if not isinstance(x,dict):continue
            if not str(x.get("time") or "").startswith(today):continue
            if str(x.get("client") or "").strip() in groups:continue
            rows.append(x)
        active=str(getattr(self,"_diagnostic_active_name","") or "").strip()
        last_ai=float(getattr(self,"_ai_last_analyzed_event_ts",0) or 0)
        if mode=="conversation" and active:
            selected=[x for x in rows if str(x.get("client") or "").strip()==active][-60:]
        elif mode=="auto":
            # Automático envia somente o delta desde a última análise.
            selected=[]
            for x in rows:
                try:ts=float(x.get("ts") or 0)
                except Exception:ts=0
                if ts>last_ai:selected.append(x)
            selected=selected[-90:]
        else:selected=rows[-140:]
        events=[self._ai_compact_event(x) for x in selected];events=[x for x in events if x]
        last_event_ts=max([float(x.get("ts") or 0) for x in rows] or [0])
        try:overview=self._diagnostic_whatsapp_overview_payload()
        except Exception:overview={}
        try:waiting=self._diagnostic_waiting_snapshot()[:25]
        except Exception:waiting=[]
        try:current_context=str((getattr(self,"_diagnostic_last_context_by_contact",{}) or {}).get(active) or "")[-1600:]
        except Exception:current_context=""
        learning=self._ai_learning_summary_payload(True)
        return {"generated_at":datetime.datetime.now().isoformat(timespec="seconds"),"mode":mode,"delta_only":bool(mode=="auto"),"active_contact":active,"active_recent_context":current_context,"whatsapp_overview":overview,"waiting_now":waiting,"recent_events":events,"day_event_count":len(rows),"events_sent":len(events),"last_event_ts":last_event_ts,"accumulated_learning":learning,"working_hours":{"weekdays":"segunda a sexta","periods":["07:50-12:08","13:30-18:00"],"waiting_metrics_use_business_time":True},"goal":"observar o trabalho comercial, aprender padrões com evidência, detectar esquecimentos e priorizar futuras automações sem enviar mensagens automaticamente"}
'''
text=replace_method(text,'MainWindow','_ai_build_context',new_build)

new_prompt=r'''    def _ai_prompt(self,mode):
        base=("Você é a IA Observadora do ALIYVO, copiloto comercial para vendas de autopeças pesadas pelo WhatsApp. "
              "Analise somente os dados fornecidos. Não invente fatos, peças, preços, intenção ou perfil psicológico do cliente. "
              "O campo accumulated_learning contém CONTAGENS LOCAIS de ocorrências observadas: trate essas contagens como evidência factual. "
              "Separe explicitamente FATO OBSERVADO de SUGESTÃO/HIPÓTESE. Uma prioridade de automação é sugestão, nunca fato. "
              "O vendedor usa respostas curtas e informais; não critique isso se não prejudicar a venda. Mensagens como ok, show, obrigado e valeu normalmente encerram a conversa. "
              "Não sugira criar uma fila paralela de atendimento: a fila principal continua sendo o próprio filtro Não lidas do WhatsApp. "
              "Use os horários 07:50-12:08 e 13:30-18:00 de segunda a sexta; não trate almoço/noite como atraso do vendedor. "
              "Nunca diga que uma automação já existe se os dados não mostrarem. Não envie nada ao cliente.")
        if mode=="conversation":
            return base+("\nResponda em português, objetivo: 1) SITUAÇÃO AGORA; 2) O QUE FALTA; 3) RESPOSTA SUGERIDA, apenas se couber; 4) FATO APRENDIDO COM ESTE CASO; 5) OPORTUNIDADE FUTURA. Se não houver evidência, diga que precisa observar mais.")
        return base+("\nFaça auditoria do trabalho recente: 1) ATENÇÃO AGORA; 2) PADRÕES CONFIRMADOS, citando contagens quando disponíveis; 3) AINDA EM OBSERVAÇÃO; 4) TAREFAS REPETITIVAS; 5) TOP OPORTUNIDADES DE AUTOMAÇÃO, justificadas por repetição; 6) O QUE CONTINUAR OBSERVANDO. Não repita sugestões genéricas.")
'''
text=replace_method(text,'MainWindow','_ai_prompt',new_prompt)

# Mantém análise automática somente durante o expediente real.
new_tick=r'''    def _ai_observer_tick(self):
        import datetime
        cfg=self._ai_config_load()
        if not bool(cfg.get("enabled")) or not self._ai_api_key():return
        now=datetime.datetime.now()
        if now.weekday()>=5:return
        minute=now.hour*60+now.minute
        in_work=(7*60+50<=minute<12*60+8) or (13*60+30<=minute<18*60)
        if not in_work:return
        self._ai_observer_analyze("auto",True)
'''
text=replace_method(text,'MainWindow','_ai_observer_tick',new_tick)

# Janela da IA ganha acesso direto ao aprendizado acumulado.
new_dialog=r'''    def _ai_observer_dialog(self,parent=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPlainTextEdit,QPushButton
        dlg=QDialog(parent or self);dlg.setWindowTitle("🤖 IA Observadora do ALIYVO");dlg.resize(900,690)
        lay=QVBoxLayout(dlg);cfg=self._ai_config_load();key_ok=bool(self._ai_api_key())
        status=QLabel(("✅ IA configurada" if key_ok else "⚠ Configure a chave da API")+(f" • automático a cada {cfg.get('interval_minutes')} min" if key_ok and cfg.get("enabled") else " • automático desligado"))
        lay.addWidget(status);txt=QPlainTextEdit();txt.setReadOnly(True);lay.addWidget(txt,1)
        self._ai_observer_text_widget=txt;self._ai_observer_status_widget=status
        latest=self._ai_history_latest()
        if isinstance(latest,dict) and latest.get("ok"):
            txt.setPlainText(f"Última análise: {latest.get('time','')}\nModelo: {latest.get('model','')}\n\n{latest.get('analysis','')}")
        else:txt.setPlainText("A IA ainda não analisou este trabalho. Ela passa a acumular padrões locais e separar fatos observados de sugestões. Nenhuma mensagem é enviada automaticamente.")
        bar=QHBoxLayout();settings=QPushButton("⚙ Configurar");now_btn=QPushButton("🧠 Analisar trabalho agora");chat_btn=QPushButton("💬 Analisar conversa atual");learn_btn=QPushButton("📚 Aprendizado");close=QPushButton("Fechar")
        for b in (settings,now_btn,chat_btn,learn_btn):bar.addWidget(b)
        bar.addStretch(1);bar.addWidget(close);lay.addLayout(bar)
        settings.clicked.connect(lambda:self._ai_settings_dialog(dlg));now_btn.clicked.connect(lambda:self._ai_observer_analyze("observer",False));chat_btn.clicked.connect(lambda:self._ai_observer_analyze("conversation",False));learn_btn.clicked.connect(lambda:self._ai_learning_dialog(dlg));close.clicked.connect(dlg.accept)
        dlg.finished.connect(lambda _=0:self._ai_observer_dialog_closed(txt,status));dlg.exec()
'''
text=replace_method(text,'MainWindow','_ai_observer_dialog',new_dialog)

# Backup diário leva também o aprendizado estruturado.
old='                "ai_observer_latest":self._ai_history_latest(),\n'
if old in text and '"ai_observer_learning":self._ai_learning_summary_payload' not in text:
    text=text.replace(old,old+'                "ai_observer_learning":self._ai_learning_summary_payload(True),\n',1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched AI Observer learning memory',version)
