from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v38.json').read_text(encoding='utf-8'))
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

# Fortalece a deteccao de grupos. O DOM do WhatsApp nem sempre expoe @g.us,
# entao tambem usamos sinais do proprio texto da linha: nome com "Grupo" ou
# prefixo de participante depois do horario (padrao tipico de conversa em grupo).
old='out.unread.push({name:name,snippet:snippet,is_group:isGroup});'
new='''if(!isGroup){
                    try{
                      if(/\\bgrupo\\b/i.test(name) || /(?:\\b\\d{1,2}:\\d{2}\\b|\\bontem\\b)\\s+~?[^:]{1,60}\\s*:\\s/i.test(snippet)) isGroup=true;
                    }catch(e){}
                  }
                  out.unread.push({name:name,snippet:snippet,is_group:isGroup});'''
if old not in text: raise SystemExit('unread group push anchor not found')
text=text.replace(old,new,1)
old='if(name)out.active={name:name,context:ctx.slice(-20),is_group:isGroup};'
new='''if(name){
                try{if(/\\bgrupo\\b/i.test(name))isGroup=true;}catch(e){}
                out.active={name:name,context:ctx.slice(-20),is_group:isGroup};
              }'''
if old not in text: raise SystemExit('active group anchor not found')
text=text.replace(old,new,1)

# Helpers para distinguir encerramento de conversa e validar o timestamp real.
anchor='    def _diagnostic_scan_done(self,result):\n'
if anchor not in text: raise SystemExit('scan done anchor not found')
helpers=r'''    def _diagnostic_is_closing_message(self,text):
        import re,unicodedata
        raw=str(text or "").strip()
        if not raw:return False
        # Reacoes/emojis sozinhos tambem encerram naturalmente a conversa.
        if not re.search(r"[A-Za-zÀ-ÿ0-9]",raw):
            return any(x in raw for x in ("👍","🙏","✅","👌","🤝","👏","❤️","❤"))
        try:s=unicodedata.normalize("NFKD",raw).encode("ascii","ignore").decode("ascii").lower()
        except Exception:s=raw.lower()
        s=re.sub(r"[^a-z0-9]+"," ",s).strip()
        if not s or len(s)>90:return False
        words=s.split()
        core_re=re.compile(r"^(?:ok+|okay|blz|beleza+|show+|valeu+|vlw+|obrigad[oa]+|obg+|perfeito|certo|combinado|tranquilo|fechou|fechado|top+|joia|amem|tmj|maravilha)$")
        modifiers={"muito","mt","mesmo","alex","amigo","amiga","amigos","meu","minha","irmao","irma","pela","pelo","atencao","de","bola","ta","tudo"}
        has_core=False
        for w in words:
            if core_re.match(w):has_core=True;continue
            if w in modifiers:continue
            return False
        return has_core

    def _diagnostic_unread_is_closing(self,snippet):
        import re
        s=str(snippet or "").strip()
        if not s:return False
        # A linha do WhatsApp termina normalmente com "texto da mensagem + contador".
        s=re.sub(r"\\s+\\d+\\s*$","",s).strip()
        # Testa os ultimos termos, evitando depender do nome/tamanho do contato.
        words=s.split()
        for n in range(1,min(7,len(words))+1):
            if self._diagnostic_is_closing_message(" ".join(words[-n:])):return True
        return False

    def _diagnostic_plausible_message_ts(self,mts,now,pending=None,snippet=""):
        import datetime,re
        try:mts=float(mts or 0); now=float(now or 0)
        except Exception:return False
        if mts<=0 or mts>now+90:return False
        # Para o diagnostico diario, timestamps com mais de 48h sao tratados como
        # contexto antigo da conversa, nunca como a nova mensagem que gerou o nao lido.
        if now-mts>48*3600:return False
        p=pending if isinstance(pending,dict) else {}
        sn=str(snippet or p.get("unread_snippet") or "")
        low=sn.lower()
        try:
            md=datetime.datetime.fromtimestamp(mts).date(); nd=datetime.datetime.fromtimestamp(now).date()
            if "ontem" in low:
                return md==(nd-datetime.timedelta(days=1))
            # Quando a barra lateral mostra HH:MM, esse horario e a referencia mais confiavel.
            times=re.findall(r"(?<!\\d)([01]?\\d|2[0-3]):([0-5]\\d)(?!\\d)",sn)
            if times:
                hh,mm=map(int,times[0])
                base=datetime.datetime.combine(nd,datetime.time(hh,mm))
                cand=base.timestamp()
                return abs(mts-cand)<=20*60
        except Exception:pass
        return True

'''
text=text.replace(anchor,helpers+anchor,1)

new_scan=r'''    def _diagnostic_scan_done(self,result):
        self._diagnostic_busy=False
        if not isinstance(result,dict) or not result.get("ok"): return
        import time
        now=time.time(); active=result.get("active") or {}; name=str(active.get("name") or "").strip(); context=active.get("context") or []
        self._diagnostic_active_name=name
        if name and context:
            try:
                _parts=[]
                for _m in context[-6:]:
                    if isinstance(_m,dict):
                        _t=str(_m.get("text") or "").strip()
                        if _t:_parts.append(_t)
                if _parts:self._diagnostic_last_context_by_contact[name]=" | ".join(_parts)[-900:]
            except Exception: pass

        groups=set(getattr(self,"_diagnostic_groups",set()) or set())
        learned=False
        if name and bool(active.get("is_group")) and name not in groups:
            groups.add(name); learned=True
        for _row in (result.get("unread") or []):
            if isinstance(_row,dict) and bool(_row.get("is_group")):
                _n=str(_row.get("name") or "").strip()
                if _n and _n not in groups: groups.add(_n); learned=True
        if learned:
            self._diagnostic_groups=groups; self._diagnostic_groups_save(groups)
            for _g in list(groups):
                self._diagnostic_pending.pop(_g,None)

        # Monta a lista de nao lidos antes de analisar a conversa ativa. Isso evita
        # criar uma pendencia apenas porque o usuario abriu uma conversa antiga.
        unread_rows={}
        for row in (result.get("unread") or []):
            if isinstance(row,dict):
                n=str(row.get("name") or "").strip()
                if n and n not in groups and not bool(row.get("is_group")): unread_rows[n]=row
        unread_pre=set(unread_rows)

        changed_chat=bool(name and name not in groups and name!=getattr(self,"_diagnostic_last_active",""))
        if changed_chat:
            previous=getattr(self,"_diagnostic_last_active","") or ""
            self._diagnostic_log("chat_opened",client=name,previous=previous)
            self._diagnostic_last_active=name

            for _pn,_pd in list(self._diagnostic_pending.items()):
                if not isinstance(_pd,dict) or _pn==name or _pn in groups: continue
                if _pd.get("opened_ts"):
                    _pd["other_chat_opens"]=int(_pd.get("other_chat_opens") or 0)+1
                    _ch=list(_pd.get("other_chats") or [])
                    if name and name not in _ch:
                        _ch.append(name); _pd["other_chats"]=_ch[-20:]

            _prev_pending=self._diagnostic_pending.get(previous)
            if previous and previous!=name and previous not in groups and isinstance(_prev_pending,dict) and _prev_pending.get("opened_ts"):
                _prev_pending["interruptions"]=int(_prev_pending.get("interruptions") or 0)+1
                _prev_pending["last_interruption_ts"]=now
                self._diagnostic_log("attendance_interrupted",client=previous,switched_to=name,interruptions=int(_prev_pending.get("interruptions") or 0),wait_so_far_seconds=max(0,int(now-float(_prev_pending.get("received_ts") or now))))

            p=self._diagnostic_pending.get(name)
            if isinstance(p,dict) and not p.get("opened_ts"):
                p["opened_ts"]=now
                wait=max(0,int(now-float(p.get("received_ts") or now)))
                self._diagnostic_log("pending_opened",client=name,until_open_seconds=wait,source=str(p.get("source") or ""))

        if name and name not in groups and context:
            seen=getattr(self,"_diagnostic_seen_calls",set())
            for idx,x in enumerate(context):
                if not isinstance(x,dict) or not x.get("is_call"): continue
                side=str(x.get("side") or ""); raw=str(x.get("text") or "").strip(); base=str(x.get("call_key") or raw or f"call-{idx}")
                call_key=(name+'|'+side+'|'+base)[-900:]
                if call_key in seen:continue
                seen.add(call_key); direction="outgoing" if side=="seller" else "incoming" if side=="customer" else "unknown"
                _call_msg_ts=float(x.get("message_ts") or 0); _call_duration=int(x.get("duration_seconds") or 0)
                self._diagnostic_log("call",client=name,direction=direction,call_type=str(x.get("call_type") or "voice"),missed=bool(x.get("missed")),duration_seconds=_call_duration,text=raw[:500],call_key=call_key,message_ts=_call_msg_ts or None)
                if _call_msg_ts>0:
                    for _pn,_pd in list(self._diagnostic_pending.items()):
                        if not isinstance(_pd,dict): continue
                        _recv=float(_pd.get("received_ts") or now)
                        if _recv<=_call_msg_ts<=now:
                            _pd["calls_during_wait"]=int(_pd.get("calls_during_wait") or 0)+1
                            _pd["call_seconds_during_wait"]=int(_pd.get("call_seconds_during_wait") or 0)+max(0,_call_duration)
                if direction=="incoming" and bool(x.get("missed")) and name not in self._diagnostic_pending:
                    self._diagnostic_pending[name]={"received_ts":now,"opened_ts":now if name==self._diagnostic_active_name else None,"source":"missed_call"}
            self._diagnostic_seen_calls=seen

            last=context[-1] if isinstance(context[-1],dict) else {}; side=str(last.get("side") or ""); msg=str(last.get("text") or "").strip(); mts=float(last.get("message_ts") or 0)
            closing=bool(side=="customer" and not last.get("is_call") and self._diagnostic_is_closing_message(msg))

            if side=="customer" and not last.get("is_call") and not closing:
                p=self._diagnostic_pending.get(name)
                if isinstance(p,dict) and self._diagnostic_plausible_message_ts(mts,now,p):
                    old=float(p.get("received_ts") or now)
                    if str(p.get("source") or "")!="message_timestamp" or mts<old:
                        p["received_ts"]=mts; p["source"]="message_timestamp"; p["timestamp_validated"]=True
                        if p.get("opened_ts"):
                            self._diagnostic_log("pending_refined",client=name,received_ts=mts,until_open_seconds=max(0,int(float(p.get("opened_ts"))-mts)))

            sig=(side+"|"+msg)[-1800:]; prev=self._diagnostic_signatures.get(name)
            if prev is None:
                self._diagnostic_signatures[name]=sig
                if side=="customer" and not last.get("is_call"):
                    if closing:
                        if self._diagnostic_pending.pop(name,None) is not None:
                            self._diagnostic_log("customer_closing_message",client=name,text=msg[:200],action="cleared_pending")
                    # Primeira leitura so cria espera se a conversa estava realmente nao lida
                    # (ou se ja existia pendencia criada pela barra lateral).
                    elif name in unread_pre or isinstance(self._diagnostic_pending.get(name),dict):
                        p=self._diagnostic_pending.get(name)
                        recv=mts if self._diagnostic_plausible_message_ts(mts,now,p) else (float(p.get("received_ts")) if isinstance(p,dict) and p.get("received_ts") else now)
                        if not isinstance(p,dict):
                            self._diagnostic_pending[name]={"received_ts":recv,"opened_ts":now,"source":"message_timestamp" if recv==mts and mts>0 else "active_detection","timestamp_validated":bool(recv==mts and mts>0)}
                        else:
                            if not p.get("opened_ts"):p["opened_ts"]=now
                            if self._diagnostic_plausible_message_ts(mts,now,p) and mts<float(p.get("received_ts") or now):p["received_ts"]=mts;p["source"]="message_timestamp";p["timestamp_validated"]=True
            elif sig and sig!=prev:
                self._diagnostic_signatures[name]=sig
                if not last.get("is_call"):
                    ev="message_customer" if side=="customer" else "message_seller" if side=="seller" else "message"; self._diagnostic_log(ev,client=name,text=msg[:500],message_ts=mts or None)
                    if side=="customer":
                        if closing:
                            had=self._diagnostic_pending.pop(name,None)
                            self._diagnostic_log("customer_closing_message",client=name,text=msg[:200],action="cleared_pending" if had else "no_reply_needed")
                        else:
                            p=self._diagnostic_pending.get(name)
                            recv=mts if self._diagnostic_plausible_message_ts(mts,now,p) else now
                            if not isinstance(p,dict):
                                self._diagnostic_pending[name]={"received_ts":recv,"opened_ts":now,"source":"message_timestamp" if recv==mts and mts>0 else "active_detection","timestamp_validated":bool(recv==mts and mts>0)}
                            else:
                                if self._diagnostic_plausible_message_ts(mts,now,p) and mts<float(p.get("received_ts") or now):p["received_ts"]=mts;p["source"]="message_timestamp";p["timestamp_validated"]=True
                                if not p.get("opened_ts"):p["opened_ts"]=now
                    elif side=="seller":
                        p=self._diagnostic_pending.pop(name,None)
                        if isinstance(p,dict):
                            received=float(p.get("received_ts") or now); opened=float(p.get("opened_ts") or now)
                            if opened<received:opened=received
                            total=max(0,int(now-received)); until_open=max(0,int(opened-received)); after_open=max(0,int(now-opened))
                            # Ultima trava de seguranca: nunca grava um tempo absurdo vindo de contexto antigo.
                            if total<=48*3600:
                                self._diagnostic_log("response",client=name,response_seconds=total,total_wait_seconds=total,until_open_seconds=until_open,after_open_seconds=after_open,received_ts=received,opened_ts=opened,response_ts=now,source=str(p.get("source") or ""),interruptions=int(p.get("interruptions") or 0),other_chat_opens=int(p.get("other_chat_opens") or 0),other_chats=list(p.get("other_chats") or [])[-20:],max_unread_during_wait=int(p.get("max_unread_during_wait") or 0),calls_during_wait=int(p.get("calls_during_wait") or 0),call_seconds_during_wait=int(p.get("call_seconds_during_wait") or 0),timestamp_validated=bool(p.get("timestamp_validated")))
                            else:
                                self._diagnostic_log("response_timing_discarded",client=name,discarded_seconds=total,reason="timestamp_antigo_inconsistente")

        unread_now=set(unread_rows); old=(set(getattr(self,"_diagnostic_unread",set()) or set())-groups); new_names=unread_now-old; cleared=old-unread_now
        _unread_count=len(unread_now)
        for _pn,_pd in list(self._diagnostic_pending.items()):
            if isinstance(_pd,dict):_pd["max_unread_during_wait"]=max(int(_pd.get("max_unread_during_wait") or 0),_unread_count)
        for n in new_names:
            row=unread_rows.get(n) or {}; snippet=str(row.get("snippet") or "")
            if self._diagnostic_unread_is_closing(snippet):
                had=self._diagnostic_pending.pop(n,None)
                self._diagnostic_log("customer_closing_message",client=n,text=snippet[-180:],action="cleared_pending" if had else "no_reply_needed")
                continue
            if not isinstance(self._diagnostic_pending.get(n),dict):
                self._diagnostic_pending[n]={"received_ts":now,"opened_ts":None,"source":"unread_detection","unread_snippet":snippet,"unread_detected_ts":now}
                self._diagnostic_log("customer_wait_started",client=n,received_ts=now,source="unread_detection",snippet=snippet[:240])
        if unread_now!=old:
            self._diagnostic_log("unread_snapshot",count=len(unread_now),names=sorted(unread_now)[:40],new=sorted(new_names)[:20],cleared=sorted(cleared)[:20]); self._diagnostic_unread=unread_now
'''
text=replace_method(text,'MainWindow','_diagnostic_scan_done',new_scan)

# Os eventos antigos absurdos continuam no arquivo bruto, mas deixam de contaminar
# medias/rankings dos relatorios depois desta versao.
new_read=r'''    def _diagnostic_read(self):
        rows=[]
        try:
            f=self._diagnostic_file()
            if not f.exists(): return rows
            for line in f.read_text(encoding="utf-8",errors="ignore").splitlines():
                try:
                    x=json.loads(line)
                    if not isinstance(x,dict):continue
                    if x.get("event")=="response":
                        try:
                            secs=int(x.get("total_wait_seconds") or x.get("response_seconds") or 0)
                            if secs>48*3600:continue
                        except Exception:pass
                    rows.append(x)
                except Exception: pass
        except Exception: pass
        return rows
'''
text=replace_method(text,'MainWindow','_diagnostic_read',new_read)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched timing validation + closing messages',version)
