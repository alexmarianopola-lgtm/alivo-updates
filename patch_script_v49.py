from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v49.json').read_text(encoding='utf-8'))
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
# IA Observadora 3
# - gargalos separados de automacoes
# - desfechos observaveis (sem chamar indicio de venda confirmada)
# - perfil comercial por cliente com fatos + sugestoes
# - perfil entra no contexto da IA para estrategia por cliente
# ---------------------------------------------------------------------
anchor='    def _ai_build_context(self,mode="observer"):\n'
if anchor not in text: raise SystemExit('_ai_build_context anchor missing')
helpers=r'''    def _ai_row_side(self,row):
        if not isinstance(row,dict):return "unknown"
        d=self._ai_learning_norm(row.get("direction"))
        e=self._ai_learning_norm(row.get("event"))
        if d in ("in","incoming","customer","client","received","recv") or any(x in e for x in ("customer_message","client_message","message_received","incoming_message")):
            return "customer"
        if d in ("out","outgoing","seller","me","mine","sent") or any(x in e for x in ("seller_message","message_sent","outgoing_message")):
            return "seller"
        return "unknown"

    def _ai_unique_rows(self):
        rows=[]
        try:rows=list(self._diagnostic_read() or [])
        except Exception:rows=[]
        good=[]
        for row in rows:
            if not isinstance(row,dict):continue
            client=str(row.get("client") or "").strip()
            if not client:continue
            try:ts=float(row.get("ts") or 0)
            except Exception:ts=0
            if ts<=0:continue
            good.append((ts,row))
        good.sort(key=lambda x:x[0])
        return good

    def _ai_outcomes_payload(self,client_name=""):
        # Desfechos que podem ser sustentados pelo diagnostico. Nao equivale a faturamento/venda.
        import re as _re
        target=str(client_name or "").strip()
        rows=[(ts,r) for ts,r in self._ai_unique_rows() if not target or str(r.get("client") or "").strip()==target]
        by_client={}
        for ts,row in rows:by_client.setdefault(str(row.get("client") or "").strip(),[]).append((ts,row))
        outcomes={}
        seen=set()
        def add(key,label,client,ts,evidence,confidence="observado"):
            stamp=str(int(ts//900))
            k=(key,self._ai_learning_norm(client),stamp,self._ai_learning_norm(evidence)[:80])
            if k in seen:return
            seen.add(k)
            rec=outcomes.get(key) or {"key":key,"label":label,"count":0,"clients":set(),"examples":[],"confidence":confidence}
            rec["count"]+=1
            if client:rec["clients"].add(client)
            ex=str(evidence or "").strip()[:150]
            if ex and ex not in rec["examples"]:rec["examples"].append(ex)
            rec["examples"]=rec["examples"][-4:]
            outcomes[key]=rec
        explicit_terms=("pode mandar","manda vir","pode enviar","pode faturar","pode separar","separa pra mim","separa para mim","fecha","fechado","vou ficar","manda pra mim","manda para mim","pode fechar")
        for client,items in by_client.items():
            # Texto explicito do cliente: e um sinal textual, nao prova fiscal de venda.
            for ts,row in items:
                side=self._ai_row_side(row)
                msg=str(row.get("text") or row.get("snippet") or row.get("row_text") or "").strip()
                norm=self._ai_learning_norm(msg)
                if side=="customer" and msg and any(term in norm for term in explicit_terms):
                    add("sinal_fechamento","Sinal explícito de fechamento/pedido no texto do cliente",client,ts,msg,"texto explícito")
            # Resposta do cliente depois de uma informacao comercial enviada pelo vendedor.
            for idx,(ts,row) in enumerate(items):
                if self._ai_row_side(row)!="seller":continue
                cats={x[0] for x in self._ai_learning_categories(row)}
                tracked=[]
                if "consulta_preco" in cats:tracked.append(("resposta_apos_preco","Cliente respondeu após preço/orçamento"))
                if "prazo_pagamento" in cats:tracked.append(("resposta_apos_prazo","Cliente respondeu após condição/prazo"))
                if "codigo_aplicacao" in cats:tracked.append(("resposta_apos_codigo","Cliente respondeu após código/aplicação"))
                if not tracked:continue
                nxt=None
                for nts,nrow in items[idx+1:]:
                    if nts-ts>4*3600:break
                    if self._ai_row_side(nrow)=="customer":
                        nxt=(nts,nrow);break
                if nxt:
                    evidence=str(nxt[1].get("text") or nxt[1].get("snippet") or "cliente respondeu")[:150]
                    for key,label in tracked:add(key,label,client,ts,evidence,"sequência observada")
        out=[]
        for rec in outcomes.values():
            rec=dict(rec);rec["clients_count"]=len(rec.pop("clients"));out.append(rec)
        out.sort(key=lambda x:(x.get("count",0),x.get("clients_count",0)),reverse=True)
        return out

    def _ai_client_profiles_payload(self):
        data={}
        seen=set()
        for ts,row in self._ai_unique_rows():
            client=str(row.get("client") or "").strip()
            if not client:continue
            rec=data.get(client)
            if rec is None:
                rec={"client":client,"first_seen":str(row.get("time") or "")[:19],"last_seen":str(row.get("time") or "")[:19],"patterns":{},"interaction_cases":0,"calls":0,"audio":0,"wait_over_5m":0,"interruptions":0}
            rec["last_seen"]=str(row.get("time") or "")[:19]
            # Um caso geral por cliente a cada 15 min, apenas para volume aproximado de interacoes.
            ik=(self._ai_learning_norm(client),int(ts//900))
            if ik not in seen:
                seen.add(ik);rec["interaction_cases"]+=1
            for key,label,weight in self._ai_learning_categories(row):
                case=(client,key,self._ai_learning_case_key(row,key))
                if case in seen:continue
                seen.add(case)
                if key=="espera_5min":rec["wait_over_5m"]+=1;continue
                if key=="interrupcoes":rec["interruptions"]+=1;continue
                if key=="ligacoes":rec["calls"]+=1;continue
                if key=="audio_recebido":rec["audio"]+=1;continue
                p=rec["patterns"].get(key) or {"label":label,"count":0,"weight":weight}
                p["count"]+=1;rec["patterns"][key]=p
            data[client]=rec
        # Junta os desfechos observados por cliente.
        for client,rec in data.items():
            rec["outcomes"]=self._ai_outcomes_payload(client)[:6]
            pats=[]
            for key,p in rec["patterns"].items():
                pats.append({"key":key,"label":p.get("label") or key,"count":int(p.get("count") or 0),"weight":float(p.get("weight") or 1)})
            pats.sort(key=lambda x:(x["count"]*x["weight"],x["count"]),reverse=True)
            rec["patterns"]=pats[:10]
            rec["evidence_count"]=sum(x["count"] for x in pats)+rec["calls"]+rec["audio"]
            rec["confidence"]="alta" if rec["evidence_count"]>=12 and rec["interaction_cases"]>=4 else ("média" if rec["evidence_count"]>=5 else "observando")
        return data

    def _ai_client_profile_payload(self,client_name):
        name=str(client_name or "").strip()
        return (self._ai_client_profiles_payload() or {}).get(name) or {"client":name,"patterns":[],"outcomes":[],"confidence":"observando","interaction_cases":0,"calls":0,"audio":0,"wait_over_5m":0,"interruptions":0}

    def _ai_client_profile_text(self,client_name):
        p=self._ai_client_profile_payload(client_name)
        lines=[f"PERFIL COMERCIAL OBSERVADO — {p.get('client') or '-'}",f"Confiança: {p.get('confidence')} • interações aproximadas: {p.get('interaction_cases',0)}",""]
        lines.append("FATOS OBSERVADOS")
        pats=p.get("patterns") or []
        if pats:
            for x in pats[:8]:lines.append(f"• {x['label']}: {x['count']} caso(s)")
        else:lines.append("• Ainda há pouca evidência comercial.")
        lines.append(f"• Áudios recebidos: {p.get('audio',0)} • ligações: {p.get('calls',0)}")
        lines += ["","DESFECHOS OBSERVÁVEIS"]
        outs=p.get("outcomes") or []
        if outs:
            for x in outs[:6]:lines.append(f"• {x['label']}: {x['count']} caso(s)")
        else:lines.append("• Ainda não há desfecho com evidência suficiente.")
        lines += ["","GARGALOS DE ATENDIMENTO"]
        lines.append(f"• Espera acima de 5 min úteis: {p.get('wait_over_5m',0)} caso(s)")
        lines.append(f"• Atendimento interrompido: {p.get('interruptions',0)} caso(s)")
        lines += ["","SUGESTÕES BASEADAS NOS PADRÕES (não são fatos)"]
        keys={x.get("key"):int(x.get("count") or 0) for x in pats}
        sug=[]
        if keys.get("consulta_preco",0)>=2 and keys.get("prazo_pagamento",0)>=2:sug.append("Quando fizer sentido na conversa, pode valer responder preço + condição juntos para reduzir ida e volta.")
        if keys.get("codigo_aplicacao",0)>=2:sug.append("Deixar busca por código/original/aplicação pronta tende a economizar tempo com este cliente.")
        if keys.get("pre_venda",0)>=2:sug.append("Pré-venda/separação aparece repetidamente; um atalho específico pode ser útil.")
        if keys.get("negociacao",0)>=2:sug.append("Negociação aparece com frequência; pode valer chegar à conversa já com limite/margem disponível.")
        if p.get("audio",0)>=3:sug.append("Este cliente usa áudio com frequência; futura transcrição automática pode ajudar a IA a entender melhor os pedidos.")
        if not sug:sug.append("Continuar observando antes de criar uma estratégia específica.")
        for s in sug[:5]:lines.append("• "+s)
        lines += ["","Importante: o perfil usa somente evidências encontradas no diagnóstico local. 'Sinal de fechamento' não significa venda/faturamento confirmado."]
        return "\n".join(lines)

    def _ai_client_profiles_dialog(self,parent=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPlainTextEdit,QPushButton
        profiles=self._ai_client_profiles_payload()
        dlg=QDialog(parent or self);dlg.setWindowTitle("👤 Perfis comerciais por cliente");dlg.resize(900,720)
        lay=QVBoxLayout(dlg);row=QHBoxLayout();row.addWidget(QLabel("Cliente:"));combo=QComboBox();combo.setEditable(True)
        names=sorted(profiles.keys(),key=lambda n:(int((profiles[n] or {}).get("evidence_count") or 0),int((profiles[n] or {}).get("interaction_cases") or 0)),reverse=True)
        combo.addItems(names);row.addWidget(combo,1);ai_btn=QPushButton("🤖 Estratégia IA");row.addWidget(ai_btn);lay.addLayout(row)
        txt=QPlainTextEdit();txt.setReadOnly(True);lay.addWidget(txt,1)
        status=QLabel("Selecione um cliente. A estratégia da IA não envia mensagens.");lay.addWidget(status)
        bottom=QHBoxLayout();refresh=QPushButton("↻ Atualizar");close=QPushButton("Fechar");bottom.addWidget(refresh);bottom.addStretch(1);bottom.addWidget(close);lay.addLayout(bottom)
        def render():
            name=str(combo.currentText() or "").strip();txt.setPlainText(self._ai_client_profile_text(name) if name else "Selecione um cliente.")
        def ai_strategy():
            name=str(combo.currentText() or "").strip()
            if not name:return
            self._ai_profile_target=name
            self._ai_observer_text_widget=txt;self._ai_observer_status_widget=status
            self._ai_observer_analyze("client_profile",False)
        combo.currentTextChanged.connect(lambda _=None:render());refresh.clicked.connect(render);ai_btn.clicked.connect(ai_strategy);close.clicked.connect(dlg.accept)
        dlg.finished.connect(lambda _=0:self._ai_observer_dialog_closed(txt,status));render();dlg.exec()

'''
text=text.replace(anchor,helpers+anchor,1)

text=replace_method(text,'MainWindow','_ai_learning_summary_payload',r'''    def _ai_learning_summary_payload(self,refresh=True):
        data=self._ai_learning_refresh() if refresh else self._ai_learning_load()
        all_patterns=[]
        for key,rec in (data.get("patterns") or {}).items():
            if not isinstance(rec,dict):continue
            count=int(rec.get("count") or 0);weight=float(rec.get("weight") or 1);clients=len(rec.get("clients") or [])
            conf="alta" if count>=10 and clients>=3 else ("média" if count>=4 and clients>=2 else "observando")
            score=round(weight*((max(count,0)**0.5)*3.0 + clients*2.0),1)
            all_patterns.append({"key":key,"label":rec.get("label") or key,"count":count,"clients_count":clients,"confidence":conf,"automation_score":score,"last_seen":rec.get("last_seen") or "","examples":list(rec.get("examples") or [])[-2:]})
        all_patterns.sort(key=lambda x:(x["automation_score"],x["clients_count"],x["count"]),reverse=True)
        gargalo_keys={"espera_5min","interrupcoes"}
        automation=[x for x in all_patterns if x.get("key") not in gargalo_keys]
        gargalos=[x for x in all_patterns if x.get("key") in gargalo_keys]
        phrases=[]
        for rec in (data.get("seller_phrases") or {}).values():
            if isinstance(rec,dict) and int(rec.get("count") or 0)>=2:phrases.append({"text":str(rec.get("text") or "")[:90],"count":int(rec.get("count") or 0)})
        phrases.sort(key=lambda x:x["count"],reverse=True)
        return {"methodology":"unique_cases_v3","updated_at":data.get("updated_at") or "","patterns":all_patterns[:18],"automation_candidates":automation[:12],"service_bottlenecks":gargalos,"observable_outcomes":self._ai_outcomes_payload()[:10],"top_seller_phrases":phrases[:10]}
''')

text=replace_method(text,'MainWindow','_ai_learning_text',r'''    def _ai_learning_text(self):
        learn=self._ai_learning_summary_payload(True);patterns=learn.get("patterns") or []
        if not patterns:return "A IA ainda está juntando evidências. Use o ALIYVO normalmente e ela começará a confirmar padrões."
        confirmed=[x for x in patterns if x.get("confidence") in ("alta","média") and x.get("key") not in ("espera_5min","interrupcoes")]
        lines=["APRENDIZADO ACUMULADO DA IA","Casos repetidos pelo scanner do diagnóstico são agrupados automaticamente.","", "PADRÕES COMERCIAIS CONFIRMADOS"]
        if confirmed:
            for x in confirmed[:10]:lines.append(f"• {x['label']}: {x['count']} caso(s) único(s) • {x['clients_count']} cliente(s) • confiança {x['confidence']}")
        else:lines.append("• Ainda não há padrão comercial com evidência suficiente.")
        lines += ["", "RANKING PARA FUTURA AUTOMAÇÃO"]
        for i,x in enumerate((learn.get("automation_candidates") or [])[:8],1):lines.append(f"{i}. {x['label']} — {x['count']} caso(s) • {x['clients_count']} cliente(s) • índice {x['automation_score']}")
        lines += ["", "GARGALOS DE ATENDIMENTO (não entram no ranking de automação)"]
        gs=learn.get("service_bottlenecks") or []
        if gs:
            for x in gs:lines.append(f"• {x['label']}: {x['count']} caso(s) • {x['clients_count']} cliente(s)")
        else:lines.append("• Nenhum gargalo confirmado ainda.")
        lines += ["", "DESFECHOS OBSERVÁVEIS"]
        outs=learn.get("observable_outcomes") or []
        if outs:
            for x in outs[:7]:lines.append(f"• {x['label']}: {x['count']} caso(s) • {x['clients_count']} cliente(s) • {x['confidence']}")
        else:lines.append("• Ainda não há sequência/desfecho com evidência suficiente.")
        phrases=learn.get("top_seller_phrases") or []
        if phrases:
            lines += ["", "FRASES CURTAS QUE VOCÊ REPETE"]
            for x in phrases[:7]:lines.append(f"• {x['text']} — {x['count']} cliente-dia(s)")
        lines += ["", "Importante: 'desfecho observável' é somente o que o diagnóstico consegue provar. Sinal textual de fechamento não é o mesmo que venda/faturamento confirmado."]
        return "\n".join(lines)
''')

text=replace_method(text,'MainWindow','_ai_learning_dialog',r'''    def _ai_learning_dialog(self,parent=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QPlainTextEdit,QPushButton,QHBoxLayout
        dlg=QDialog(parent or self);dlg.setWindowTitle("📚 Aprendizado da IA Observadora");dlg.resize(900,720)
        lay=QVBoxLayout(dlg);txt=QPlainTextEdit();txt.setReadOnly(True);txt.setPlainText(self._ai_learning_text());lay.addWidget(txt,1)
        row=QHBoxLayout();profiles=QPushButton("👤 Perfis por cliente");refresh=QPushButton("↻ Atualizar aprendizado");close=QPushButton("Fechar");row.addWidget(profiles);row.addWidget(refresh);row.addStretch(1);row.addWidget(close);lay.addLayout(row)
        profiles.clicked.connect(lambda:self._ai_client_profiles_dialog(dlg));refresh.clicked.connect(lambda:txt.setPlainText(self._ai_learning_text()));close.clicked.connect(dlg.accept);dlg.exec()
''')

text=replace_method(text,'MainWindow','_ai_build_context',r'''    def _ai_build_context(self,mode="observer"):
        import datetime,time
        today=datetime.date.today().isoformat();groups=set(self._diagnostic_groups_load());rows=[]
        for x in self._diagnostic_read():
            if not isinstance(x,dict):continue
            if not str(x.get("time") or "").startswith(today):continue
            if str(x.get("client") or "").strip() in groups:continue
            rows.append(x)
        active=str(getattr(self,"_diagnostic_active_name","") or "").strip()
        target=str(getattr(self,"_ai_profile_target","") or "").strip() if mode=="client_profile" else active
        last_ai=float(getattr(self,"_ai_last_analyzed_event_ts",0) or 0)
        if mode in ("conversation","client_profile") and target:
            selected=[x for x in rows if str(x.get("client") or "").strip()==target][-90:]
        elif mode=="auto":
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
        try:current_context=str((getattr(self,"_diagnostic_last_context_by_contact",{}) or {}).get(target) or "")[-1800:]
        except Exception:current_context=""
        learning=self._ai_learning_summary_payload(True)
        profile=self._ai_client_profile_payload(target) if target else {}
        return {"generated_at":datetime.datetime.now().isoformat(timespec="seconds"),"mode":mode,"delta_only":bool(mode=="auto"),"active_contact":target,"active_recent_context":current_context,"client_profile":profile,"whatsapp_overview":overview,"waiting_now":waiting,"recent_events":events,"day_event_count":len(rows),"events_sent":len(events),"last_event_ts":last_event_ts,"accumulated_learning":learning,"working_hours":{"weekdays":"segunda a sexta","periods":["07:50-12:08","13:30-18:00"],"waiting_metrics_use_business_time":True},"goal":"observar o trabalho comercial, aprender padrões com evidência, separar gargalos de oportunidades de automação, reconhecer desfechos observáveis e sugerir estratégias por cliente sem inventar vendas nem enviar mensagens automaticamente"}
''')

text=replace_method(text,'MainWindow','_ai_prompt',r'''    def _ai_prompt(self,mode):
        base=("Você é a IA Observadora do ALIYVO, um copiloto comercial para vendas de autopeças pesadas pelo WhatsApp. "
              "Analise somente os dados fornecidos. Não invente fatos, peças, preços, venda fechada ou intenção do cliente. "
              "O vendedor trabalha rápido e usa respostas curtas; não critique abreviações ou informalidade se não prejudicarem a venda. "
              "Mensagens de encerramento como ok, show, obrigado, valeu e equivalentes normalmente não exigem resposta. "
              "Diferencie sempre FATO OBSERVADO, INDÍCIO e SUGESTÃO. Um sinal textual de fechamento não prova faturamento. "
              "Gargalos de atendimento (espera/interrupção) não devem ser tratados como automações por si só. "
              "Nunca diga que uma automação já existe se os dados não mostrarem isso. Não envie nada ao cliente.")
        if mode=="conversation":
            return base+("\nAnalise a conversa atual e responda em português com: 1) SITUAÇÃO AGORA; 2) O QUE AINDA FALTA RESPONDER/FAZER; 3) RESPOSTA SUGERIDA curta, somente se couber; 4) PRÓXIMA FERRAMENTA/AÇÃO; 5) OPORTUNIDADE DE AUTOMAÇÃO aprendida com este caso. Seja objetivo.")
        if mode=="client_profile":
            return base+("\nVocê recebeu o perfil acumulado e eventos recentes de UM cliente. Produza uma estratégia comercial baseada somente nessas evidências: 1) FATOS CONFIRMADOS; 2) PADRÕES DO CLIENTE; 3) DESFECHOS OBSERVADOS; 4) COMO ABORDAR/RESPONDER MELHOR; 5) O QUE AINDA NÃO SABEMOS; 6) AUTOMAÇÃO/FERRAMENTA QUE PODERIA AJUDAR. Não atribua personalidade, renda, saúde, política, religião ou qualquer característica sensível ao cliente. Não chame indício de venda confirmada.")
        return base+("\nFaça uma auditoria do fluxo recente e responda em português com: 1) ATENÇÃO AGORA; 2) PADRÕES COMERCIAIS; 3) GARGALOS DE ATENDIMENTO; 4) DESFECHOS OBSERVÁVEIS; 5) TAREFAS REPETITIVAS; 6) FERRAMENTAS/ATALHOS; 7) AUTOMAÇÕES FUTURAS; 8) O QUE CONTINUAR OBSERVANDO. Priorize ganhos de tempo reais e evite sugestões genéricas.")
''')

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched AI observer profiles/outcomes',version)
