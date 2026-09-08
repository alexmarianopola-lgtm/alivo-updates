from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v32.json').read_text(encoding='utf-8'))
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

new_extract=r'''    def _attendance_extract_js(self):
        return r"""
        (() => {
          try{
            const clean=t=>String(t||'').replace(/\s+/g,' ').trim();
            const out={ok:true,active:null,unread:[]};
            const parseStamp=(holder)=>{
              try{
                let pre=holder.getAttribute&&holder.getAttribute('data-pre-plain-text');
                if(!pre){const q=holder.querySelector&&holder.querySelector('[data-pre-plain-text]'); if(q)pre=q.getAttribute('data-pre-plain-text');}
                pre=String(pre||'');
                const m=pre.match(/\[(\d{1,2}):(\d{2})(?::(\d{2}))?,\s*(\d{1,2})\/(\d{1,2})\/(\d{4})\]/);
                if(!m)return 0;
                const d=new Date(parseInt(m[6],10),parseInt(m[5],10)-1,parseInt(m[4],10),parseInt(m[1],10),parseInt(m[2],10),parseInt(m[3]||'0',10));
                const ts=Math.floor(d.getTime()/1000); return Number.isFinite(ts)?ts:0;
              }catch(e){return 0;}
            };
            const parseDuration=(raw)=>{
              const s=clean(raw).toLowerCase(); let total=0,found=false;
              const h=s.match(/(\d+)\s*h(?:ora|oras)?\b/); if(h){total+=parseInt(h[1],10)*3600;found=true;}
              const m=s.match(/(\d+)\s*min(?:uto|utos)?\b/); if(m){total+=parseInt(m[1],10)*60;found=true;}
              const sec=s.match(/(\d+)\s*s(?:egundo|egundos)?\b/); if(sec){total+=parseInt(sec[1],10);found=true;}
              return found?total:0;
            };
            const callInfo=(raw)=>{
              const s=clean(raw); const isCall=/(liga[cç][aã]o|chamada|voice call|video call)/i.test(s);
              if(!isCall)return null;
              const type=/(v[ií]deo|video)/i.test(s)?'video':'voice';
              const missed=/(n[aã]o atendid|perdid|missed|sem resposta|cancelad)/i.test(s);
              return {is_call:true,call_type:type,missed:missed,duration_seconds:parseDuration(s)};
            };
            const main=document.querySelector('#main') || document.querySelector('[data-testid="conversation-panel-wrapper"]');
            if(main){
              let name='';
              const h=main.querySelector('header [data-testid="conversation-info-header-chat-title"]') || main.querySelector('header span[title]') || main.querySelector('header [title]');
              if(h)name=clean(h.getAttribute('title')||h.textContent||'');
              const ctx=[]; const mr=main.getBoundingClientRect(); const mid=mr.left+mr.width*0.50;
              const push=(side,txt,extra,ts)=>{txt=clean(txt);if(!txt||txt.length<2)return;const o={side:side,text:txt.slice(0,1200),message_ts:Number(ts||0)};if(extra)Object.assign(o,extra);ctx.push(o);};
              const bubbles=Array.from(main.querySelectorAll('div.message-in,div.message-out,[data-pre-plain-text]')).slice(-28);
              const seen=new Set();
              for(const b of bubbles){
                const holder=b.closest('div.message-in,div.message-out')||b;
                if(seen.has(holder))continue; seen.add(holder);
                let side='';
                if(holder.classList&&holder.classList.contains('message-out'))side='seller';
                else if(holder.classList&&holder.classList.contains('message-in'))side='customer';
                else {const r=holder.getBoundingClientRect(); side=((r.left+r.right)/2)>=mid?'seller':'customer';}
                const ns=Array.from(holder.querySelectorAll('span.selectable-text,[data-testid="selectable-text"]'));
                let parts=[]; for(const n of ns){const t=clean(n.innerText||n.textContent||'');if(t&&!parts.includes(t))parts.push(t);}
                const raw=clean(holder.innerText||holder.textContent||''); const ts=parseStamp(holder); const ci=callInfo(raw);
                if(ci){
                  const did=holder.getAttribute('data-id') || (holder.querySelector('[data-id]')&&holder.querySelector('[data-id]').getAttribute('data-id')) || '';
                  const pre=holder.getAttribute('data-pre-plain-text') || (holder.querySelector('[data-pre-plain-text]')&&holder.querySelector('[data-pre-plain-text]').getAttribute('data-pre-plain-text')) || '';
                  ci.call_key=clean(did||pre||raw).slice(0,500); push(side,raw,ci,ts);
                }else if(parts.length){push(side,parts.join(' '),null,ts);}
              }
              if(name)out.active={name:name,context:ctx.slice(-20)};
            }
            const pane=document.querySelector('#pane-side');
            if(pane){
              const rows=Array.from(pane.querySelectorAll('[role="listitem"],[role="row"],[data-testid="cell-frame-container"]')).slice(0,90);
              const seen=new Set();
              for(const row of rows){
                const n=row.querySelector('span[title]'); const name=n?clean(n.getAttribute('title')||n.textContent||''):'';
                if(!name||seen.has(name))continue; seen.add(name);
                let unread=false; const els=Array.from(row.querySelectorAll('[aria-label],[data-testid],[data-icon]'));
                for(const e of els){const a=(String(e.getAttribute('aria-label')||'')+' '+String(e.getAttribute('data-testid')||'')+' '+String(e.getAttribute('data-icon')||'')).toLowerCase();if(a.includes('unread')||a.includes('não lida')||a.includes('não lidas')||a.includes('não lido')||a.includes('não lidos')){unread=true;break;}}
                if(unread){let snippet=clean(row.innerText||row.textContent||'');if(snippet.length>220)snippet=snippet.slice(-220);out.unread.push({name:name,snippet:snippet});}
              }
            }
            return out;
          }catch(e){return {ok:false,error:String(e)};}
        })();
        """
'''
text=replace_method(text,'MainWindow','_attendance_extract_js',new_extract)

new_start=r'''    def _diagnostic_start(self):
        self._diagnostic_busy=False
        self._diagnostic_active_name=""
        self._diagnostic_last_active=""
        self._diagnostic_signatures={}
        self._diagnostic_pending={}
        self._diagnostic_unread=set()
        self._diagnostic_seen_calls=set()
        try:
            for row in self._diagnostic_read()[-1800:]:
                if isinstance(row,dict) and row.get("event")=="call":
                    k=str(row.get("call_key") or "").strip()
                    if k:self._diagnostic_seen_calls.add(k)
        except Exception: pass
        self._diagnostic_timer=QTimer(self); self._diagnostic_timer.setInterval(3000)
        self._diagnostic_timer.timeout.connect(self._diagnostic_scan); self._diagnostic_timer.start()
        QTimer.singleShot(1200,self._diagnostic_scan)
        try:
            for attr,tool in (("plate_toggle","plate"),("lens_toggle","image")):
                b=getattr(self,attr,None)
                if b:b.clicked.connect(lambda _=False,t=tool:self._diagnostic_log("tool_opened",client=getattr(self,"_diagnostic_active_name","") or "",tool=t))
        except Exception: pass
'''
text=replace_method(text,'MainWindow','_diagnostic_start',new_start)

new_scan=r'''    def _diagnostic_scan_done(self,result):
        self._diagnostic_busy=False
        if not isinstance(result,dict) or not result.get("ok"): return
        import time
        now=time.time(); active=result.get("active") or {}; name=str(active.get("name") or "").strip(); context=active.get("context") or []
        self._diagnostic_active_name=name

        changed_chat=bool(name and name!=getattr(self,"_diagnostic_last_active",""))
        if changed_chat:
            previous=getattr(self,"_diagnostic_last_active","") or ""; self._diagnostic_log("chat_opened",client=name,previous=previous); self._diagnostic_last_active=name
            p=self._diagnostic_pending.get(name)
            if isinstance(p,dict) and not p.get("opened_ts"):
                p["opened_ts"]=now
                wait=max(0,int(now-float(p.get("received_ts") or now)))
                self._diagnostic_log("pending_opened",client=name,until_open_seconds=wait,source=str(p.get("source") or ""))

        if name and context:
            seen=getattr(self,"_diagnostic_seen_calls",set())
            for idx,x in enumerate(context):
                if not isinstance(x,dict) or not x.get("is_call"): continue
                side=str(x.get("side") or ""); raw=str(x.get("text") or "").strip(); base=str(x.get("call_key") or raw or f"call-{idx}")
                call_key=(name+'|'+side+'|'+base)[-900:]
                if call_key in seen:continue
                seen.add(call_key); direction="outgoing" if side=="seller" else "incoming" if side=="customer" else "unknown"
                self._diagnostic_log("call",client=name,direction=direction,call_type=str(x.get("call_type") or "voice"),missed=bool(x.get("missed")),duration_seconds=int(x.get("duration_seconds") or 0),text=raw[:500],call_key=call_key)
                if direction=="incoming" and bool(x.get("missed")) and name not in self._diagnostic_pending:
                    self._diagnostic_pending[name]={"received_ts":now,"opened_ts":now if name==self._diagnostic_active_name else None,"source":"missed_call"}
            self._diagnostic_seen_calls=seen

            last=context[-1] if isinstance(context[-1],dict) else {}; side=str(last.get("side") or ""); msg=str(last.get("text") or "").strip(); mts=float(last.get("message_ts") or 0)
            # Se abrimos uma conversa que já estava pendente, refina a hora real usando o timestamp do WhatsApp quando disponível.
            if side=="customer" and not last.get("is_call"):
                p=self._diagnostic_pending.get(name)
                if isinstance(p,dict) and mts>0:
                    old=float(p.get("received_ts") or now)
                    if mts<=now+60 and (str(p.get("source") or "")!="message_timestamp" or mts<old):
                        p["received_ts"]=mts; p["source"]="message_timestamp"
                        if p.get("opened_ts"):
                            self._diagnostic_log("pending_refined",client=name,received_ts=mts,until_open_seconds=max(0,int(float(p.get("opened_ts"))-mts)))

            sig=(side+"|"+msg)[-1800:]; prev=self._diagnostic_signatures.get(name)
            if prev is None:
                self._diagnostic_signatures[name]=sig
                # Mesmo na primeira leitura, se a última mensagem é do cliente, cria/refina a pendência.
                if side=="customer" and not last.get("is_call"):
                    recv=mts if mts>0 and mts<=now+60 else now
                    p=self._diagnostic_pending.get(name)
                    if not isinstance(p,dict):
                        self._diagnostic_pending[name]={"received_ts":recv,"opened_ts":now,"source":"message_timestamp" if mts>0 else "active_detection"}
                    else:
                        if not p.get("opened_ts"):p["opened_ts"]=now
                        if mts>0 and mts<float(p.get("received_ts") or now):p["received_ts"]=mts;p["source"]="message_timestamp"
            elif sig and sig!=prev:
                self._diagnostic_signatures[name]=sig
                if not last.get("is_call"):
                    ev="message_customer" if side=="customer" else "message_seller" if side=="seller" else "message"; self._diagnostic_log(ev,client=name,text=msg[:500],message_ts=mts or None)
                    if side=="customer":
                        recv=mts if mts>0 and mts<=now+60 else now
                        p=self._diagnostic_pending.get(name)
                        if not isinstance(p,dict):
                            self._diagnostic_pending[name]={"received_ts":recv,"opened_ts":now,"source":"message_timestamp" if mts>0 else "active_detection"}
                        else:
                            # Não reinicia a espera se o cliente mandar várias mensagens antes da resposta; mantém a primeira.
                            if mts>0 and mts<float(p.get("received_ts") or now):p["received_ts"]=mts;p["source"]="message_timestamp"
                            if not p.get("opened_ts"):p["opened_ts"]=now
                    elif side=="seller":
                        p=self._diagnostic_pending.pop(name,None)
                        if isinstance(p,dict):
                            received=float(p.get("received_ts") or now); opened=float(p.get("opened_ts") or now)
                            if opened<received:opened=received
                            total=max(0,int(now-received)); until_open=max(0,int(opened-received)); after_open=max(0,int(now-opened))
                            self._diagnostic_log("response",client=name,response_seconds=total,total_wait_seconds=total,until_open_seconds=until_open,after_open_seconds=after_open,received_ts=received,opened_ts=opened,response_ts=now,source=str(p.get("source") or ""))

        unread_rows={}
        for row in (result.get("unread") or []):
            if isinstance(row,dict):
                n=str(row.get("name") or "").strip()
                if n: unread_rows[n]=row
        unread_now=set(unread_rows); old=set(getattr(self,"_diagnostic_unread",set()) or set()); new_names=unread_now-old; cleared=old-unread_now
        for n in new_names:
            # Primeiro instante em que o ALIYVO viu o cliente tornar-se não lido. Depois refinamos ao abrir a conversa.
            if not isinstance(self._diagnostic_pending.get(n),dict):
                self._diagnostic_pending[n]={"received_ts":now,"opened_ts":None,"source":"unread_detection"}
                self._diagnostic_log("customer_wait_started",client=n,received_ts=now,source="unread_detection",snippet=str((unread_rows.get(n) or {}).get("snippet") or "")[:240])
        if unread_now!=old:
            self._diagnostic_log("unread_snapshot",count=len(unread_now),names=sorted(unread_now)[:40],new=sorted(new_names)[:20],cleared=sorted(cleared)[:20]); self._diagnostic_unread=unread_now
'''
text=replace_method(text,'MainWindow','_diagnostic_scan_done',new_scan)

new_summary=r'''    def _diagnostic_summary_text(self,rows):
        import datetime,statistics
        today=datetime.date.today().isoformat(); day=[x for x in rows if str(x.get("time") or "").startswith(today)]
        clients=set(str(x.get("client") or "") for x in day if x.get("client")); resp_rows=[x for x in day if x.get("event")=="response"]
        responses=[max(0,int(x.get("total_wait_seconds") if x.get("total_wait_seconds") is not None else x.get("response_seconds") or 0)) for x in resp_rows]
        split=[x for x in resp_rows if x.get("until_open_seconds") is not None and x.get("after_open_seconds") is not None]
        until_open=[max(0,int(x.get("until_open_seconds") or 0)) for x in split]; after_open=[max(0,int(x.get("after_open_seconds") or 0)) for x in split]
        tools={}
        for x in day:
            if x.get("event")=="tool_opened":t=str(x.get("tool") or "outro");tools[t]=tools.get(t,0)+1
        calls=[x for x in day if x.get("event")=="call"]; incoming=sum(1 for x in calls if x.get("direction")=="incoming"); outgoing=sum(1 for x in calls if x.get("direction")=="outgoing"); missed=sum(1 for x in calls if bool(x.get("missed"))); voice=sum(1 for x in calls if str(x.get("call_type") or "voice")=="voice"); video=sum(1 for x in calls if str(x.get("call_type") or "")=="video"); call_seconds=sum(max(0,int(x.get("duration_seconds") or 0)) for x in calls)
        max_unread=max([int(x.get("count") or 0) for x in day if x.get("event")=="unread_snapshot"] or [0]); cust=sum(1 for x in day if x.get("event")=="message_customer"); seller=sum(1 for x in day if x.get("event")=="message_seller"); opens=sum(1 for x in day if x.get("event")=="chat_opened")
        def fmt(s):
            s=int(round(float(s or 0))); h=s//3600;m=(s%3600)//60;sec=s%60
            if h:return f"{h}h {m:02d}m"
            if m:return f"{m}m {sec:02d}s"
            return f"{sec}s"
        avg=(sum(responses)/len(responses)) if responses else 0; med=statistics.median(responses) if responses else 0
        fastest=min(responses) if responses else 0; slowest=max(responses) if responses else 0; over5=sum(1 for s in responses if s>=300); over15=sum(1 for s in responses if s>=900)
        avg_open=(sum(until_open)/len(until_open)) if until_open else 0; avg_after=(sum(after_open)/len(after_open)) if after_open else 0
        per={}
        for x in resp_rows:
            c=str(x.get("client") or "").strip()
            if not c:continue
            s=max(0,int(x.get("total_wait_seconds") if x.get("total_wait_seconds") is not None else x.get("response_seconds") or 0)); d=per.setdefault(c,[]); d.append(s)
        rank=[]
        for c,vals in per.items():rank.append((max(vals),sum(vals)/len(vals),c,len(vals),sum(1 for s in vals if s>=300),sum(1 for s in vals if s>=900)))
        rank.sort(reverse=True)
        rank_lines=[]
        for i,(mx,av,c,n,o5,o15) in enumerate(rank[:5],1):rank_lines.append(f"{i}. {c} — maior {fmt(mx)} | média {fmt(av)} | {n} resposta(s) | >5min: {o5} | >15min: {o15}")
        rank_text="\n".join(rank_lines) if rank_lines else "Ainda sem respostas suficientes para montar o ranking."
        tool_line=", ".join(f"{k}: {v}" for k,v in sorted(tools.items(),key=lambda z:-z[1])) or "nenhuma registrada"; call_line=(f"{len(calls)} total • {incoming} recebidas • {outgoing} feitas • {missed} não atendidas • {fmt(call_seconds)} detectados" if calls else "nenhuma detectada ainda")
        return (f"DIAGNÓSTICO DE HOJE\n\n"
                f"Clientes observados: {len(clients)}\nTrocas/aberturas de conversa: {opens}\nMensagens novas de clientes detectadas: {cust}\nRespostas suas detectadas: {seller}\nMaior quantidade de não lidos observada: {max_unread}\n\n"
                f"TEMPO DE RESPOSTA\nEspera total média: {fmt(avg) if responses else 'ainda sem amostra'}\nMediana: {fmt(med) if responses else 'ainda sem amostra'}\nMais rápido: {fmt(fastest) if responses else '-'}\nMais demorado: {fmt(slowest) if responses else '-'}\nAcima de 5 min: {over5} • Acima de 15 min: {over15}\nTempo médio até você abrir: {fmt(avg_open) if until_open else 'começa a medir nesta versão'}\nTempo médio depois de abrir até responder: {fmt(avg_after) if after_open else 'começa a medir nesta versão'}\n\n"
                f"CLIENTES QUE MAIS ESPERARAM\n{rank_text}\n\n"
                f"LIGAÇÕES DO WHATSAPP\n{call_line}\nVoz: {voice} • Vídeo: {video}\n\n"
                f"Ferramentas usadas: {tool_line}\n\nEventos guardados no histórico: {len(rows)}\n\n"
                "Medição: mensagem do cliente → abertura da conversa → sua resposta. Quando o WhatsApp expõe o horário da mensagem, o ALIYVO usa esse horário; caso contrário usa o primeiro instante em que detectou o não lido.")
'''
text=replace_method(text,'MainWindow','_diagnostic_summary_text',new_summary)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched detailed response timing + wait ranking',version)
