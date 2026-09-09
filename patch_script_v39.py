from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v39.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)


def method_source(src,class_name,method_name):
    tree=ast.parse(src)
    cls=next((n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==class_name),None)
    if cls is None: raise SystemExit(f'class {class_name} not found')
    target=next((n for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==method_name),None)
    if target is None: raise SystemExit(f'method {class_name}.{method_name} not found')
    lines=src.splitlines(keepends=True)
    return ''.join(lines[target.lineno-1:target.end_lineno])


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

# 1) O inspetor do WhatsApp passa a procurar o overlay de uma ligacao ATIVA.
# O sinal principal e o botao visivel de encerrar/desligar a chamada, evitando
# confundir o simples icone de telefone do cabecalho da conversa.
ms=method_source(text,'MainWindow','_attendance_extract_js')
marker='''            return out;\n'''
if marker not in ms: raise SystemExit('JS return out anchor not found')
live_js=r'''            // Ligacao/chamada ativa: procura o controle de desligar que so aparece durante a chamada.
            try{
              const vis=(e)=>{try{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&r.bottom>0&&r.right>0&&s.display!=='none'&&s.visibility!=='hidden'&&Number(s.opacity||1)>0;}catch(_){return false;}};
              const meta=(e)=>clean((e.getAttribute&&e.getAttribute('aria-label')||'')+' '+(e.getAttribute&&e.getAttribute('data-testid')||'')+' '+(e.getAttribute&&e.getAttribute('data-icon')||'')+' '+(e.getAttribute&&e.getAttribute('title')||''));
              const controls=Array.from(document.querySelectorAll('[aria-label],[data-testid],[data-icon],button'));
              const hang=controls.find(e=>vis(e)&&/(encerrar\s*(?:a\s*)?(?:liga[cç][aã]o|chamada)|desligar|finalizar\s*(?:liga[cç][aã]o|chamada)|end[-_ ]?call|call[-_ ]?end|hang[-_ ]?up)/i.test(meta(e)));
              if(hang){
                let box=hang, best=hang.parentElement||hang;
                for(let i=0;i<10&&box&&box.parentElement;i++){
                  box=box.parentElement;
                  if(!vis(box))continue;
                  const r=box.getBoundingClientRect();
                  const t=String(box.innerText||box.textContent||'');
                  if(r.width>=220&&r.width<=760&&r.height>=80&&r.height<=700&&/\b\d{1,2}:\d{2}(?::\d{2})?\b/.test(t))best=box;
                }
                const rawText=String(best.innerText||best.textContent||'');
                const lines=rawText.split(/\n+/).map(clean).filter(Boolean);
                let duration=0;
                for(const ln of lines){
                  let m=ln.match(/^\s*(\d{1,2}):(\d{2}):(\d{2})\s*$/);
                  if(m){duration=parseInt(m[1],10)*3600+parseInt(m[2],10)*60+parseInt(m[3],10);break;}
                  m=ln.match(/^\s*(\d{1,3}):(\d{2})\s*$/);
                  if(m){duration=parseInt(m[1],10)*60+parseInt(m[2],10);break;}
                }
                let cname='';
                const titled=Array.from(best.querySelectorAll('span[title],[title]')).filter(vis);
                for(const e of titled){
                  const v=clean(e.getAttribute('title')||e.textContent||'');
                  if(v&&v.length>=2&&!/^\d{1,3}:\d{2}(?::\d{2})?$/.test(v)&&!/(encerrar|desligar|microfone|c[aâ]mera|camera|ligação|chamada|call)/i.test(v)){cname=v;break;}
                }
                if(!cname){
                  for(const ln of lines){
                    if(ln.length<2||ln.length>90)continue;
                    if(/^\d{1,3}:\d{2}(?::\d{2})?$/.test(ln))continue;
                    if(/(encerrar|desligar|microfone|c[aâ]mera|camera|ligação|chamada|call|silenciar|mute)/i.test(ln))continue;
                    if(/[A-Za-zÀ-ÿ]/.test(ln)){cname=ln;break;}
                  }
                }
                if(!cname&&out.active)cname=clean(out.active.name||'');
                const allMeta=controls.filter(e=>vis(e)&&best.contains(e)).map(meta).join(' ');
                const callType=/(chamada de v[ií]deo|video call)/i.test(rawText+' '+allMeta)?'video':'voice';
                out.live_call={active:true,client:cname,duration_seconds:Math.max(0,duration||0),call_type:callType,raw:clean(rawText).slice(0,500)};
              }
            }catch(_liveErr){}
'''
ms=ms.replace(marker,live_js+marker,1)
text=replace_method(text,'MainWindow','_attendance_extract_js',ms)

# 2) Estado em memoria da ligacao ativa e uma pequena janela para impedir que
# o cartao que aparece no historico logo apos desligar seja contado novamente.
ms=method_source(text,'MainWindow','_diagnostic_start')
start_anchor='''        self._diagnostic_last_context_by_contact={}\n'''
if start_anchor not in ms: raise SystemExit('diagnostic start context anchor not found')
ms=ms.replace(start_anchor,start_anchor+'''        self._diagnostic_live_call=None\n        self._diagnostic_live_missing=0\n        self._diagnostic_recent_live_calls=[]\n''',1)
text=replace_method(text,'MainWindow','_diagnostic_start',ms)

# 3) Helpers para iniciar/acompanhar/finalizar a ligacao detectada no overlay.
anchor='    def _diagnostic_scan_done(self,result):\n'
if anchor not in text: raise SystemExit('scan done anchor not found')
helpers=r'''    def _diagnostic_finish_live_call(self,now=None,reason="overlay_gone"):
        import time
        now=float(now or time.time())
        cur=getattr(self,"_diagnostic_live_call",None)
        if not isinstance(cur,dict):
            self._diagnostic_live_call=None; self._diagnostic_live_missing=0; return
        client=str(cur.get("client") or "").strip() or "Contato"
        start=float(cur.get("start_ts") or now)
        visible=max(0,int(cur.get("duration_seconds") or 0))
        elapsed=max(0,int(now-start))
        duration=max(visible,elapsed)
        session=str(cur.get("session_id") or f"live|{client}|{int(start)}")
        self._diagnostic_log("call",client=client,direction=str(cur.get("direction") or "unknown"),call_type=str(cur.get("call_type") or "voice"),missed=False,duration_seconds=duration,call_key=session,source="live_overlay",started_ts=start,ended_ts=now,end_reason=reason)
        recent=list(getattr(self,"_diagnostic_recent_live_calls",[]) or [])
        recent.append({"client":client,"ended_ts":now,"duration_seconds":duration,"call_type":str(cur.get("call_type") or "voice")})
        self._diagnostic_recent_live_calls=[x for x in recent[-12:] if now-float(x.get("ended_ts") or now)<900]
        self._diagnostic_live_call=None; self._diagnostic_live_missing=0

    def _diagnostic_live_call_update(self,live,now=None,fallback_name=""):
        import time
        now=float(now or time.time())
        if isinstance(live,dict) and bool(live.get("active")):
            self._diagnostic_live_missing=0
            client=str(live.get("client") or fallback_name or "").strip() or "Contato"
            duration=max(0,int(live.get("duration_seconds") or 0))
            ctype=str(live.get("call_type") or "voice")
            cur=getattr(self,"_diagnostic_live_call",None)
            if isinstance(cur,dict) and str(cur.get("client") or "").strip()!=client:
                self._diagnostic_finish_live_call(now,"contact_changed")
                cur=None
            if not isinstance(cur,dict):
                start=now-duration if duration>0 else now
                session=f"live|{client}|{int(start)}"
                cur={"client":client,"start_ts":start,"duration_seconds":duration,"last_seen_ts":now,"call_type":ctype,"direction":"unknown","session_id":session}
                self._diagnostic_live_call=cur
                self._diagnostic_log("call_live_started",client=client,call_type=ctype,started_ts=start,visible_duration_seconds=duration,call_key=session)
            else:
                cur["last_seen_ts"]=now
                cur["duration_seconds"]=max(int(cur.get("duration_seconds") or 0),duration)
                cur["call_type"]=ctype or str(cur.get("call_type") or "voice")
                # Se o ALIYVO entrou no meio da chamada, corrige o inicio pelo cronometro visivel.
                if duration>0:
                    estimated=now-duration
                    if estimated<float(cur.get("start_ts") or now):cur["start_ts"]=estimated
            return
        cur=getattr(self,"_diagnostic_live_call",None)
        if isinstance(cur,dict):
            self._diagnostic_live_missing=int(getattr(self,"_diagnostic_live_missing",0) or 0)+1
            # Dois scans ausentes (~6s) evitam finalizar por uma piscada/re-render do WhatsApp.
            if self._diagnostic_live_missing>=2:self._diagnostic_finish_live_call(now,"overlay_gone")
        else:
            self._diagnostic_live_missing=0

'''
text=text.replace(anchor,helpers+anchor,1)

# 4) Cada scan atualiza o estado da chamada ao vivo.
ms=method_source(text,'MainWindow','_diagnostic_scan_done')
scan_anchor='''        self._diagnostic_active_name=name\n'''
if scan_anchor not in ms: raise SystemExit('active name anchor not found')
ms=ms.replace(scan_anchor,scan_anchor+'''        try:self._diagnostic_live_call_update(result.get("live_call"),now,name)\n        except Exception:pass\n''',1)

# 5) Depois de desligar, o WhatsApp costuma inserir um cartao da mesma ligacao
# na conversa. Suprime esse duplicado por contato/janela de tempo.
dup_anchor='''                if call_key in seen:continue\n                seen.add(call_key); direction="outgoing" if side=="seller" else "incoming" if side=="customer" else "unknown"\n'''
if dup_anchor not in ms: raise SystemExit('call dedupe anchor not found')
dup_new='''                if call_key in seen:continue\n                _hist_dur=max(0,int(x.get("duration_seconds") or 0))\n                _dup_live=False\n                for _lc in list(getattr(self,"_diagnostic_recent_live_calls",[]) or []):\n                    try:\n                        if str(_lc.get("client") or "").strip()==name and now-float(_lc.get("ended_ts") or 0)<=600:\n                            _ld=max(0,int(_lc.get("duration_seconds") or 0))\n                            if _hist_dur<=0 or _ld<=0 or abs(_hist_dur-_ld)<=180:\n                                _dup_live=True;break\n                    except Exception:pass\n                if _dup_live:\n                    seen.add(call_key);continue\n                seen.add(call_key); direction="outgoing" if side=="seller" else "incoming" if side=="customer" else "unknown"\n'''
ms=ms.replace(dup_anchor,dup_new,1)
text=replace_method(text,'MainWindow','_diagnostic_scan_done',ms)

# 6) O relatorio conta tambem a chamada que ainda esta em andamento e mostra
# sua duracao corrente. Quando ela termina, passa a existir como evento "call".
def add_live_to_day_calls(src,method_name):
    ms=method_source(src,'MainWindow',method_name)
    pat=r'(?m)^(?P<i>\s*)calls=\[x for x in day if x\.get\("event"\)=="call"\]\s*$'
    m=re.search(pat,ms)
    if not m: raise SystemExit(f'calls day anchor not found in {method_name}')
    ind=m.group('i')
    extra=(m.group(0)+'\n'+ind+'live=getattr(self,"_diagnostic_live_call",None)\n'+ind+'if isinstance(live,dict):\n'+ind+'    import time as _time\n'+ind+'    _now=_time.time(); _start=float(live.get("start_ts") or _now); _dur=max(int(live.get("duration_seconds") or 0),max(0,int(_now-_start)))\n'+ind+'    calls=calls+[{"event":"call","client":str(live.get("client") or ""),"direction":str(live.get("direction") or "unknown"),"call_type":str(live.get("call_type") or "voice"),"missed":False,"duration_seconds":_dur,"source":"live_overlay","live":True}]')
    ms=ms[:m.start()]+extra+ms[m.end():]
    return replace_method(src,'MainWindow',method_name,ms)

text=add_live_to_day_calls(text,'_diagnostic_summary_text')
text=add_live_to_day_calls(text,'_diagnostic_daily_summary_text')

# 7) O historico do contato atual tambem mostra a ligacao em andamento no bloco HOJE.
ms=method_source(text,'MainWindow','_diagnostic_contact_history_text')
contact_anchor='''            calls=[x for x in data if x.get("event")=="call"]\n'''
if contact_anchor in ms:
    ms=ms.replace(contact_anchor,contact_anchor+'''            if label=="HOJE":\n                live=getattr(self,"_diagnostic_live_call",None)\n                if isinstance(live,dict) and str(live.get("client") or "").strip()==name:\n                    import time as _time\n                    _now=_time.time();_start=float(live.get("start_ts") or _now);_dur=max(int(live.get("duration_seconds") or 0),max(0,int(_now-_start)))\n                    calls=calls+[{"event":"call","client":name,"direction":str(live.get("direction") or "unknown"),"call_type":str(live.get("call_type") or "voice"),"duration_seconds":_dur,"live":True}]\n''',1)
    text=replace_method(text,'MainWindow','_diagnostic_contact_history_text',ms)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched live WhatsApp call diagnostics',version)
