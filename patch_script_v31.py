from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v31.json').read_text(encoding='utf-8'))
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
            const parseDuration=(raw)=>{
              const s=clean(raw).toLowerCase();
              let total=0, found=false;
              const h=s.match(/(\d+)\s*h(?:ora|oras)?\b/); if(h){total+=parseInt(h[1],10)*3600;found=true;}
              const m=s.match(/(\d+)\s*min(?:uto|utos)?\b/); if(m){total+=parseInt(m[1],10)*60;found=true;}
              const sec=s.match(/(\d+)\s*s(?:egundo|egundos)?\b/); if(sec){total+=parseInt(sec[1],10);found=true;}
              return found?total:0;
            };
            const callInfo=(raw)=>{
              const s=clean(raw); const l=s.toLowerCase();
              const isCall=/(liga[cç][aã]o|chamada|voice call|video call)/i.test(s);
              if(!isCall)return null;
              const type=/(v[ií]deo|video)/i.test(s)?'video':'voice';
              const missed=/(n[aã]o atendid|perdid|missed|sem resposta|cancelad)/i.test(s);
              return {is_call:true,call_type:type,missed:missed,duration_seconds:parseDuration(s)};
            };
            const main=document.querySelector('#main') || document.querySelector('[data-testid="conversation-panel-wrapper"]');
            if(main){
              let name='';
              const h=main.querySelector('header [data-testid="conversation-info-header-chat-title"]') ||
                      main.querySelector('header span[title]') || main.querySelector('header [title]');
              if(h) name=clean(h.getAttribute('title')||h.textContent||'');
              const ctx=[];
              const mr=main.getBoundingClientRect(); const mid=mr.left+mr.width*0.50;
              const push=(side,txt,extra)=>{txt=clean(txt);if(!txt||txt.length<2)return;const o={side:side,text:txt.slice(0,1200)};if(extra)Object.assign(o,extra);ctx.push(o);};
              const bubbles=Array.from(main.querySelectorAll('div.message-in,div.message-out,[data-pre-plain-text]')).slice(-24);
              const seen=new Set();
              for(const b of bubbles){
                const holder=b.closest('div.message-in,div.message-out')||b;
                if(seen.has(holder))continue; seen.add(holder);
                let side='';
                if(holder.classList&&holder.classList.contains('message-out'))side='seller';
                else if(holder.classList&&holder.classList.contains('message-in'))side='customer';
                else {const r=holder.getBoundingClientRect(); side=((r.left+r.right)/2)>=mid?'seller':'customer';}
                const ns=Array.from(holder.querySelectorAll('span.selectable-text,[data-testid="selectable-text"]'));
                let parts=[];
                for(const n of ns){const t=clean(n.innerText||n.textContent||'');if(t&&!parts.includes(t))parts.push(t);}
                const raw=clean(holder.innerText||holder.textContent||'');
                const ci=callInfo(raw);
                if(ci){
                  let key='';
                  const did=holder.getAttribute('data-id') || (holder.querySelector('[data-id]')&&holder.querySelector('[data-id]').getAttribute('data-id')) || '';
                  const pre=holder.getAttribute('data-pre-plain-text') || (holder.querySelector('[data-pre-plain-text]')&&holder.querySelector('[data-pre-plain-text]').getAttribute('data-pre-plain-text')) || '';
                  key=clean(did||pre||raw);
                  ci.call_key=key.slice(0,500);
                  push(side,raw,ci);
                }else if(parts.length){
                  push(side,parts.join(' '),null);
                }
              }
              if(name) out.active={name:name,context:ctx.slice(-18)};
            }
            const pane=document.querySelector('#pane-side');
            if(pane){
              const rows=Array.from(pane.querySelectorAll('[role="listitem"],[role="row"],[data-testid="cell-frame-container"]')).slice(0,90);
              const seen=new Set();
              for(const row of rows){
                const n=row.querySelector('span[title]');
                const name=n?clean(n.getAttribute('title')||n.textContent||''):'';
                if(!name||seen.has(name))continue; seen.add(name);
                let unread=false;
                const els=Array.from(row.querySelectorAll('[aria-label],[data-testid],[data-icon]'));
                for(const e of els){
                  const a=(String(e.getAttribute('aria-label')||'')+' '+String(e.getAttribute('data-testid')||'')+' '+String(e.getAttribute('data-icon')||'')).toLowerCase();
                  if(a.includes('unread')||a.includes('não lida')||a.includes('não lidas')||a.includes('não lido')||a.includes('não lidos')){unread=true;break;}
                }
                if(unread){
                  let snippet=clean(row.innerText||row.textContent||''); if(snippet.length>180)snippet=snippet.slice(-180);
                  out.unread.push({name:name,snippet:snippet});
                }
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
            for row in self._diagnostic_read()[-1500:]:
                if isinstance(row,dict) and row.get("event")=="call":
                    k=str(row.get("call_key") or "").strip()
                    if k:self._diagnostic_seen_calls.add(k)
        except Exception:
            pass
        self._diagnostic_timer=QTimer(self)
        self._diagnostic_timer.setInterval(3000)
        self._diagnostic_timer.timeout.connect(self._diagnostic_scan)
        self._diagnostic_timer.start()
        QTimer.singleShot(1200,self._diagnostic_scan)
        try:
            for attr,tool in (("plate_toggle","plate"),("lens_toggle","image")):
                b=getattr(self,attr,None)
                if b: b.clicked.connect(lambda _=False,t=tool:self._diagnostic_log("tool_opened",client=getattr(self,"_diagnostic_active_name","") or "",tool=t))
        except Exception:
            pass
'''
text=replace_method(text,'MainWindow','_diagnostic_start',new_start)

new_scan=r'''    def _diagnostic_scan_done(self,result):
        self._diagnostic_busy=False
        if not isinstance(result,dict) or not result.get("ok"): return
        import time
        now=time.time()
        active=result.get("active") or {}
        name=str(active.get("name") or "").strip()
        context=active.get("context") or []
        self._diagnostic_active_name=name
        if name and name!=getattr(self,"_diagnostic_last_active",""):
            self._diagnostic_log("chat_opened",client=name,previous=getattr(self,"_diagnostic_last_active","") or "")
            self._diagnostic_last_active=name

        if name and context:
            # Registra chamadas visiveis no historico da conversa sem duplica-las.
            seen=getattr(self,"_diagnostic_seen_calls",set())
            for idx,x in enumerate(context):
                if not isinstance(x,dict) or not x.get("is_call"): continue
                side=str(x.get("side") or "")
                raw=str(x.get("text") or "").strip()
                base=str(x.get("call_key") or raw or f"call-{idx}")
                call_key=(name+'|'+side+'|'+base)[-900:]
                if call_key in seen: continue
                seen.add(call_key)
                direction="outgoing" if side=="seller" else "incoming" if side=="customer" else "unknown"
                missed=bool(x.get("missed"))
                duration=int(x.get("duration_seconds") or 0)
                self._diagnostic_log("call",client=name,direction=direction,call_type=str(x.get("call_type") or "voice"),missed=missed,duration_seconds=duration,text=raw[:500],call_key=call_key)
                # Chamada recebida e não atendida também significa cliente aguardando retorno.
                if direction=="incoming" and missed:
                    self._diagnostic_pending[name]=now
            self._diagnostic_seen_calls=seen

            last=context[-1] if isinstance(context[-1],dict) else {}
            side=str(last.get("side") or "")
            msg=str(last.get("text") or "").strip()
            sig=(side+"|"+msg)[-1800:]
            prev=self._diagnostic_signatures.get(name)
            if prev is None:
                self._diagnostic_signatures[name]=sig
            elif sig and sig!=prev:
                self._diagnostic_signatures[name]=sig
                if not last.get("is_call"):
                    ev="message_customer" if side=="customer" else "message_seller" if side=="seller" else "message"
                    self._diagnostic_log(ev,client=name,text=msg[:500])
                    if side=="customer":
                        self._diagnostic_pending[name]=now
                    elif side=="seller" and name in self._diagnostic_pending:
                        secs=max(0,int(now-float(self._diagnostic_pending.pop(name))))
                        self._diagnostic_log("response",client=name,response_seconds=secs)

        unread_now=set()
        for row in (result.get("unread") or []):
            if isinstance(row,dict):
                n=str(row.get("name") or "").strip()
                if n: unread_now.add(n)
        old=set(getattr(self,"_diagnostic_unread",set()) or set())
        if unread_now!=old:
            self._diagnostic_log("unread_snapshot",count=len(unread_now),names=sorted(unread_now)[:40],new=sorted(unread_now-old)[:20],cleared=sorted(old-unread_now)[:20])
            self._diagnostic_unread=unread_now
'''
text=replace_method(text,'MainWindow','_diagnostic_scan_done',new_scan)

new_summary=r'''    def _diagnostic_summary_text(self,rows):
        import datetime,statistics
        today=datetime.date.today().isoformat()
        day=[x for x in rows if str(x.get("time") or "").startswith(today)]
        clients=set(str(x.get("client") or "") for x in day if x.get("client"))
        responses=[int(x.get("response_seconds") or 0) for x in day if x.get("event")=="response" and int(x.get("response_seconds") or 0)>=0]
        tools={}
        for x in day:
            if x.get("event")=="tool_opened":
                t=str(x.get("tool") or "outro"); tools[t]=tools.get(t,0)+1
        calls=[x for x in day if x.get("event")=="call"]
        incoming=sum(1 for x in calls if x.get("direction")=="incoming")
        outgoing=sum(1 for x in calls if x.get("direction")=="outgoing")
        missed=sum(1 for x in calls if bool(x.get("missed")))
        voice=sum(1 for x in calls if str(x.get("call_type") or "voice")=="voice")
        video=sum(1 for x in calls if str(x.get("call_type") or "")=="video")
        call_seconds=sum(max(0,int(x.get("duration_seconds") or 0)) for x in calls)
        max_unread=max([int(x.get("count") or 0) for x in day if x.get("event")=="unread_snapshot"] or [0])
        cust=sum(1 for x in day if x.get("event")=="message_customer")
        seller=sum(1 for x in day if x.get("event")=="message_seller")
        opens=sum(1 for x in day if x.get("event")=="chat_opened")
        avg=(sum(responses)/len(responses)) if responses else 0
        med=statistics.median(responses) if responses else 0
        def fmt(s):
            s=int(s); return f"{s//60}m {s%60:02d}s" if s>=60 else f"{s}s"
        def fmt_long(s):
            s=int(s); h=s//3600; m=(s%3600)//60; sec=s%60
            if h:return f"{h}h {m:02d}m"
            if m:return f"{m}m {sec:02d}s"
            return f"{sec}s"
        tool_line=", ".join(f"{k}: {v}" for k,v in sorted(tools.items(),key=lambda z:-z[1])) or "nenhuma registrada"
        call_line=(f"{len(calls)} total • {incoming} recebidas • {outgoing} feitas • {missed} não atendidas • {fmt_long(call_seconds)} detectados"
                   if calls else "nenhuma detectada ainda")
        return (f"DIAGNÓSTICO DE HOJE\n\n"
                f"Clientes observados: {len(clients)}\n"
                f"Trocas/aberturas de conversa: {opens}\n"
                f"Mensagens novas de clientes detectadas: {cust}\n"
                f"Respostas suas detectadas: {seller}\n"
                f"Maior quantidade de não lidos observada: {max_unread}\n"
                f"Tempo médio de resposta medido: {fmt(avg) if responses else 'ainda sem amostra'}\n"
                f"Mediana de resposta: {fmt(med) if responses else 'ainda sem amostra'}\n\n"
                f"LIGAÇÕES DO WHATSAPP\n{call_line}\n"
                f"Voz: {voice} • Vídeo: {video}\n\n"
                f"Ferramentas usadas: {tool_line}\n\n"
                f"Eventos guardados no histórico: {len(rows)}\n\n"
                "O analisador trabalha em segundo plano. Continue usando Lido/Não lido normalmente.")
'''
text=replace_method(text,'MainWindow','_diagnostic_summary_text',new_summary)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched call diagnostics',version)
