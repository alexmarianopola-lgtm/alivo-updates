from pathlib import Path
import sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
text=main.read_text(encoding='utf-8')

def one(old,new,label):
    global text
    n=text.count(old)
    if n!=1:
        raise SystemExit(f'{label}: esperado 1, encontrado {n}')
    text=text.replace(old,new,1)

one('ALIYVO_VERSION = "0.22.91"','ALIYVO_VERSION = "0.22.92"','version')

old_hook='''            try:self._smart_reminder_from_diagnostic(name,context)
            except Exception as _smart_err:
                try:self._diagnostic_log("smart_reminder_error",error=str(_smart_err)[:220])
                except Exception:pass
'''
new_hook='''            try:self._smart_reminder_from_diagnostic(name,context)
            except Exception as _smart_err:
                try:self._diagnostic_log("smart_reminder_error",error=str(_smart_err)[:220])
                except Exception:pass
            # CRM Assistido 0.22.92: reaproveita o MESMO contexto ja extraido
            # pelo diagnostico. Nao cria scanner, timer nem leitura adicional do DOM.
            try:self._crm_update_state_from_context(name,context)
            except Exception as _crm_err:
                try:self._diagnostic_log("crm_state_error",error=str(_crm_err)[:220])
                except Exception:pass
'''
one(old_hook,new_hook,'crm hook')

marker='''    def _smart_reminder_parse_message(self,message,client):
'''
crm_methods=r'''    def _crm_state_file(self):
        try:USER_DATA_DIR.mkdir(parents=True,exist_ok=True)
        except Exception:pass
        return USER_DATA_DIR/"crm_estados_beta.json"

    def _crm_states_load(self):
        cached=getattr(self,"_crm_states",None)
        if isinstance(cached,dict):return cached
        data={}
        try:
            f=self._crm_state_file()
            if f.exists():
                x=json.loads(f.read_text(encoding="utf-8"))
                if isinstance(x,dict):data=x
        except Exception:pass
        self._crm_states=data
        return data

    def _crm_states_save(self):
        try:
            self._crm_state_file().write_text(json.dumps(self._crm_states_load(),ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception:pass

    def _crm_norm(self,value):
        import unicodedata
        s=str(value or "").lower()
        return "".join(c for c in unicodedata.normalize("NFD",s) if unicodedata.category(c)!="Mn")

    def _crm_detect_state(self,client,context):
        import re,time
        name=str(client or "").strip()
        msgs=[]
        for m in (context or [])[-12:]:
            if not isinstance(m,dict) or m.get("is_call"):continue
            txt=str(m.get("text") or "").strip()
            side=str(m.get("side") or "").strip()
            if txt and side in ("customer","seller"):msgs.append({"text":txt,"side":side})
        base={"client":name,"status_key":"sem_evidencia","status":"Sem pendência comercial clara","next_action":"Continuar observando","pending":False,"owner":"nenhum","confidence":"baixa","reason":"contexto insuficiente","evidence":"","updated_at":time.time()}
        if not msgs:return base
        last=msgs[-1];last_raw=last["text"];last_txt=self._crm_norm(last_raw)
        recent=self._crm_norm(" | ".join(x["text"] for x in msgs[-8:]))
        side=last["side"]

        courtesy=bool(re.fullmatch(r"\s*(ok|okay|show|obrigad[oa]?|valeu|beleza|blz|certo|perfeito|top|joia|jóia|fechou)[!. ]*\s*",last_txt))
        wait_customer=bool(re.search(r"\b(vou ver|vou conferir|vou analisar|vou pensar|vou falar|falo com|te aviso|depois te falo|vejo e te aviso|qualquer coisa te aviso)\b",last_txt))
        closing=bool(re.search(r"\b(pode separar|separa pra mim|separa para mim|pode faturar|pode fatura|fatura pra mim|fatura para mim|pode mandar|manda pra mim|manda para mim|fecha pra mim|fecha para mim|vou ficar com|pode fechar)\b",last_txt))
        ask_info=bool(re.search(r"\b(me passa|me manda|manda|envia|preciso)\b.{0,45}\b(placa|chassi|codigo|código|referencia|referência|foto|aplicacao|aplicação|quantidade|medida)\b",last_txt))
        no_stock=bool(re.search(r"\b(nao temos|não temos|nao tenho|não tenho|sem estoque|indisponivel|indisponível)\b",last_txt))
        quote=bool(re.search(r"\b(preco|preço|valor|orcamento|orçamento|cotacao|cotação|quanto|desconto|condicao|condição|prazo)\b",recent))
        stock=bool(re.search(r"\b(estoque|disponivel|disponível|tem esse|tem essa|temos sim|tenho sim)\b",recent))
        code=bool(re.search(r"\b(codigo|código|referencia|referência|aplicacao|aplicação|placa|chassi|original)\b",recent))
        commercial=bool(quote or stock or code or closing or no_stock or ask_info or wait_customer)

        def out(key,status,action,pending,owner,confidence,reason):
            x=dict(base);x.update({"status_key":key,"status":status,"next_action":action,"pending":bool(pending),"owner":owner,"confidence":confidence,"reason":reason,"evidence":last_raw[-220:],"last_side":side,"updated_at":time.time()});return x

        if side=="customer":
            if wait_customer:
                return out("aguardando_cliente","Aguardando cliente","Não cobrar agora; acompanhar depois se a oportunidade continuar aberta",True,"cliente","alta","cliente disse que vai verificar/analisar e retornar")
            if closing:
                return out("possivel_fechamento","Possível fechamento","Confirmar item, quantidade, condição e faturamento antes de concluir",True,"vendedor","alta","cliente usou frase compatível com avanço de pedido")
            if courtesy:
                return out("sem_pendencia","Sem pendência clara","Nenhuma ação imediata",False,"nenhum","alta","última mensagem parece encerramento curto")
            if commercial:
                return out("cliente_aguarda_resposta","Cliente aguardando resposta","Responder o cliente e definir o próximo passo",True,"vendedor","alta","última mensagem comercial veio do cliente")
            return out("cliente_aguarda_resposta","Cliente aguardando resposta","Conferir a mensagem e responder se necessário",True,"vendedor","média","última mensagem veio do cliente")

        # Última mensagem foi do vendedor.
        if ask_info:
            return out("aguardando_informacao","Aguardando informação do cliente","Aguardar placa/chassi/código/foto solicitado",True,"cliente","alta","vendedor pediu uma informação necessária")
        if no_stock:
            return out("sem_produto","Sem produto informado","Buscar alternativa/similar ou encerrar a oportunidade",True,"vendedor","alta","vendedor informou falta de produto/estoque")
        if quote:
            return out("cotacao_enviada","Cotação/condição enviada","Acompanhar se o cliente não retornar; criar lembrete se fizer sentido",True,"cliente","média","há preço/orçamento/condição no contexto e a última mensagem é do vendedor")
        if commercial:
            return out("aguardando_cliente","Aguardando cliente","Aguardar retorno e definir acompanhamento se a oportunidade ficar parada",True,"cliente","média","conversa comercial terminou com mensagem do vendedor")
        return out("sem_pendencia","Sem pendência comercial clara","Continuar observando","False"=="True","nenhum","baixa","não há sinal comercial forte no contexto recente")

    def _crm_update_state_from_context(self,client,context):
        import time
        name=str(client or "").strip()
        if not name:return {}
        state=self._crm_detect_state(name,context)
        data=self._crm_states_load();old=data.get(name) if isinstance(data.get(name),dict) else {}
        changed=any(old.get(k)!=state.get(k) for k in ("status_key","next_action","pending","owner","evidence"))
        data[name]=state
        if changed:
            self._crm_states_save()
            try:self._diagnostic_log("crm_state_changed",client=name,status=state.get("status_key"),pending=state.get("pending"),owner=state.get("owner"),next_action=state.get("next_action"),confidence=state.get("confidence"))
            except Exception:pass
        return state

    def _crm_state_for_client(self,client):
        name=str(client or "").strip()
        if not name:return {}
        x=self._crm_states_load().get(name)
        return dict(x) if isinstance(x,dict) else {}

    def _crm_states_payload(self,limit=20,pending_only=False):
        import time
        now=time.time();rows=[]
        for name,x in self._crm_states_load().items():
            if not isinstance(x,dict):continue
            try:age=now-float(x.get("updated_at") or 0)
            except Exception:age=9e9
            if age>7*86400:continue
            if pending_only and not bool(x.get("pending")):continue
            row=dict(x);row["client"]=str(row.get("client") or name);rows.append(row)
        rows.sort(key=lambda x:(0 if x.get("owner")=="vendedor" else 1,-float(x.get("updated_at") or 0)))
        return rows[:max(1,int(limit or 20))]

'''
one(marker,crm_methods+marker,'insert crm methods')

old_assist='''        lines=[f"ASSISTÊNCIA RÁPIDA — {name}",f"Prioridade agora: {pri['level'].upper()} • índice {pri['score']}"]
        if pri.get("reasons"):
            lines.append("Motivos: "+"; ".join(pri["reasons"]))
        lines += ["", "O QUE O HISTÓRICO SUGERE"]
'''
new_assist='''        lines=[f"ASSISTÊNCIA RÁPIDA — {name}",f"Prioridade agora: {pri['level'].upper()} • índice {pri['score']}"]
        if pri.get("reasons"):
            lines.append("Motivos: "+"; ".join(pri["reasons"]))
        crm_state=self._crm_state_for_client(name)
        lines += ["", "SITUAÇÃO CRM"]
        if crm_state:
            lines.append(f"• Status: {crm_state.get('status') or '-'}")
            lines.append(f"• Próxima ação: {crm_state.get('next_action') or '-'}")
            lines.append(f"• Pendência: {'SIM' if crm_state.get('pending') else 'NÃO'} • responsável agora: {crm_state.get('owner') or '-'} • confiança {crm_state.get('confidence') or '-'}")
            if crm_state.get("reason"):lines.append("• Motivo: "+str(crm_state.get("reason")))
        else:
            lines.append("• Ainda não há estado comercial detectado para esta conversa.")
        lines += ["", "O QUE O HISTÓRICO SUGERE"]
'''
one(old_assist,new_assist,'assist crm state')

old_crm='''        txt=QPlainTextEdit();txt.setReadOnly(True);rem=self._crm_open_reminders_payload();lines=["LEMBRETES ABERTOS"]
        if rem:
            for r in rem[:20]:lines.append(("⚠ " if r.get("overdue") else "• ")+f"{r.get('due')} • {r.get('client') or 'sem cliente'} — {r.get('text')}")
        else:lines.append("• Nenhum lembrete aberto.")
'''
new_crm='''        txt=QPlainTextEdit();txt.setReadOnly(True);rem=self._crm_open_reminders_payload();active=str(getattr(self,"_diagnostic_active_name","") or "").strip();state=self._crm_state_for_client(active) if active else {};live=self._crm_states_payload(12,True);lines=["ESTADO COMERCIAL ATUAL"]
        if active and state:
            lines.append(f"• {active}: {state.get('status')} → {state.get('next_action')} [confiança {state.get('confidence')}]")
        elif active:lines.append(f"• {active}: ainda sem classificação comercial.")
        else:lines.append("• Abra uma conversa para ver o estado comercial atual.")
        lines += ["", "PENDÊNCIAS DETECTADAS PELO OBSERVADOR"]
        if live:
            for x in live:lines.append(f"• {x.get('client')} — {x.get('status')} → {x.get('next_action')} ({x.get('owner')})")
        else:lines.append("• Nenhuma pendência comercial detectada nos últimos 7 dias.")
        lines += ["", "LEMBRETES ABERTOS"]
        if rem:
            for r in rem[:20]:lines.append(("⚠ " if r.get("overdue") else "• ")+f"{r.get('due')} • {r.get('client') or 'sem cliente'} — {r.get('text')}")
        else:lines.append("• Nenhum lembrete aberto.")
'''
one(old_crm,new_crm,'crm dialog')

old_ctx='''        learning=self._ai_learning_summary_payload(True)
        profile=self._ai_client_profile_payload(target) if target else {}
        reminders=self._crm_open_reminders_payload(target if mode in ("conversation","client_profile") else "")
        priority=self._ai_priority_for_client(target) if target else {}
        return {"generated_at":datetime.datetime.now().isoformat(timespec="seconds"),"mode":mode,"delta_only":bool(mode=="auto"),"active_contact":target,"active_recent_context":current_context,"client_profile":profile,"client_priority":priority,"open_reminders":reminders,"whatsapp_overview":overview,"waiting_now":waiting,"recent_events":events,"day_event_count":len(rows),"events_sent":len(events),"last_event_ts":last_event_ts,"accumulated_learning":learning,"working_hours":{"weekdays":"segunda a sexta","periods":["07:50-12:08","13:30-18:00"],"waiting_metrics_use_business_time":True},"goal":"atuar como copiloto/CRM assistido: priorizar clientes, aprofundar estrategia por cliente, conectar lembretes ao contexto comercial e sugerir proximas acoes sem enviar mensagens nem alterar lembretes automaticamente"}
'''
new_ctx='''        learning=self._ai_learning_summary_payload(True)
        profile=self._ai_client_profile_payload(target) if target else {}
        reminders=self._crm_open_reminders_payload(target if mode in ("conversation","client_profile") else "")
        priority=self._ai_priority_for_client(target) if target else {}
        commercial_state=self._crm_state_for_client(target) if target else {}
        commercial_pending=self._crm_states_payload(20,True) if mode in ("observer","auto","crm_reminders") else []
        return {"generated_at":datetime.datetime.now().isoformat(timespec="seconds"),"mode":mode,"delta_only":bool(mode=="auto"),"active_contact":target,"active_recent_context":current_context,"client_profile":profile,"client_priority":priority,"commercial_state":commercial_state,"commercial_pending":commercial_pending,"open_reminders":reminders,"whatsapp_overview":overview,"waiting_now":waiting,"recent_events":events,"day_event_count":len(rows),"events_sent":len(events),"last_event_ts":last_event_ts,"accumulated_learning":learning,"working_hours":{"weekdays":"segunda a sexta","periods":["07:50-12:08","13:30-18:00"],"waiting_metrics_use_business_time":True},"goal":"atuar como copiloto/CRM assistido: priorizar clientes, usar status comercial + proxima acao + pendencia, aprofundar estrategia por cliente, conectar lembretes ao contexto comercial e sugerir proximas acoes sem enviar mensagens nem alterar lembretes automaticamente"}
'''
one(old_ctx,new_ctx,'ai context crm')

text=text.replace('aliyvo_version="0.22.91"','aliyvo_version="0.22.92"')
main.write_text(text,encoding='utf-8')
print('PATCH_CRM_ASSISTIDO_V92=OK')
