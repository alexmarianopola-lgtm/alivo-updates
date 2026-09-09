from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v40.json').read_text(encoding='utf-8'))
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

# Enriquece o inspetor: total da aba Nao lidas, quantidade por contato, horario e tipo do snippet.
ms=method_source(text,'MainWindow','_attendance_extract_js')
marker='            return out;\n'
pos=ms.rfind(marker)
if pos<0: raise SystemExit('JS final return out anchor not found')
extra=r'''            // Panorama da barra lateral inteira sem clicar ou rolar automaticamente.
            try{
              let totalUnread=0;
              const candidates=Array.from(document.querySelectorAll('button,[role="tab"],[aria-label],span,div'));
              for(const e of candidates){
                let s=clean((e.getAttribute&&e.getAttribute('aria-label')||'')+' '+(e.innerText||e.textContent||''));
                if(s.length>80)continue;
                let m=s.match(/n[aã]o\s+lidas?\s*(\d{1,4})/i) || s.match(/(\d{1,4})\s+n[aã]o\s+lidas?/i);
                if(m)totalUnread=Math.max(totalUnread,parseInt(m[1],10)||0);
              }
              const pane2=document.querySelector('#pane-side');
              const details={};
              if(pane2){
                const rows2=Array.from(pane2.querySelectorAll('[role="listitem"],[role="row"],[data-testid="cell-frame-container"]')).slice(0,120);
                for(const row of rows2){
                  const n=row.querySelector('span[title]');
                  const nm=n?clean(n.getAttribute('title')||n.textContent||''):'';
                  if(!nm)continue;
                  const rowText=clean(row.innerText||row.textContent||'');
                  const attrs=Array.from(row.querySelectorAll('[aria-label],[data-testid],[data-icon]')).map(x=>clean((x.getAttribute('aria-label')||'')+' '+(x.getAttribute('data-testid')||'')+' '+(x.getAttribute('data-icon')||''))).join(' ');
                  let cnt=0;
                  let cm=attrs.match(/(\d{1,4})\s+mensage(?:m|ns)\s+n[aã]o\s+lid[ao]s?/i) || attrs.match(/n[aã]o\s+lid[ao]s?[^0-9]{0,20}(\d{1,4})/i);
                  if(cm)cnt=parseInt(cm[1],10)||0;
                  if(!cnt){
                    const badges=Array.from(row.querySelectorAll('span,div')).filter(x=>/^\d{1,3}$/.test(clean(x.textContent||'')));
                    for(const b of badges){
                      const v=parseInt(clean(b.textContent||''),10)||0;
                      const r=b.getBoundingClientRect();
                      if(v>0&&r.width<=55&&r.height<=45){cnt=Math.max(cnt,v);}
                    }
                  }
                  const tm=rowText.match(/(?:^|\s)([0-2]?\d:[0-5]\d)(?:\s|$)/);
                  let ctype='text';
                  if(/mensagem apagada/i.test(rowText))ctype='deleted';
                  else if(/\bfoto\b/i.test(rowText))ctype='image';
                  else if(/\b(v[ií]deo|video)\b/i.test(rowText))ctype='video';
                  else if(/\b(documento|pdf)\b/i.test(rowText))ctype='document';
                  else if(/\b(sticker|figurinha)\b/i.test(rowText))ctype='sticker';
                  else if(/\b(liga[cç][aã]o|chamada)\b/i.test(rowText))ctype='call';
                  else if(/\b\d{1,3}:\d{2}\b/.test(rowText)&&/(microfone|audio|áudio|voice)/i.test(attrs+' '+rowText))ctype='audio';
                  details[nm]={unread_count:cnt||1,row_time:tm?tm[1]:'',content_type:ctype,row_text:rowText.slice(-360)};
                }
              }
              for(const u of (out.unread||[])){
                const d=details[u.name]||{};
                Object.assign(u,d);
              }
              out.unread_total=Math.max(totalUnread,(out.unread||[]).length);
              out.unread_visible=(out.unread||[]).length;
              out.unread_messages_visible=(out.unread||[]).reduce((a,u)=>a+Math.max(1,parseInt(u.unread_count||1,10)||1),0);
            }catch(_overviewErr){}
'''
ms=ms[:pos]+extra+ms[pos:]
text=replace_method(text,'MainWindow','_attendance_extract_js',ms)

# Estado acumulado do panorama.
ms=method_source(text,'MainWindow','_diagnostic_start')
anchor='        self._diagnostic_recent_live_calls=[]\n'
if anchor not in ms:
    anchor='        self._diagnostic_last_context_by_contact={}\n'
if anchor not in ms: raise SystemExit('diagnostic start overview anchor not found')
ins=('        self._diagnostic_unread_registry={}\n'
     '        self._diagnostic_unread_total_whatsapp=0\n'
     '        self._diagnostic_unread_visible=0\n'
     '        self._diagnostic_unread_message_total=0\n'
     '        self._diagnostic_current_unread_names=set()\n')
ms=ms.replace(anchor,anchor+ins,1)
text=replace_method(text,'MainWindow','_diagnostic_start',ms)

# Helpers do panorama: registra todos os contatos nao lidos que o WhatsApp montou na tela e mantem memoria ao rolar.
anchor='    def _diagnostic_scan_done(self,result):\n'
if anchor not in text: raise SystemExit('scan done anchor not found')
helpers=r'''    def _diagnostic_update_whatsapp_overview(self,result,now=None):
        import time
        now=float(now or time.time())
        groups=set(getattr(self,"_diagnostic_groups",set()) or set())
        rows=result.get("unread") if isinstance(result,dict) else []
        if not isinstance(rows,list):rows=[]
        try:total=max(0,int(result.get("unread_total") or 0))
        except Exception:total=0
        registry=dict(getattr(self,"_diagnostic_unread_registry",{}) or {})
        current=set(); visible_messages=0
        for row in rows:
            if not isinstance(row,dict):continue
            name=str(row.get("name") or "").strip()
            if not name or name in groups or bool(row.get("is_group")):continue
            snippet=str(row.get("snippet") or row.get("row_text") or "").strip()
            try:count=max(1,int(row.get("unread_count") or 1))
            except Exception:count=1
            closing=False
            try:closing=bool(self._diagnostic_unread_is_closing(snippet))
            except Exception:pass
            cur=registry.get(name) if isinstance(registry.get(name),dict) else {}
            previous_sig=(str(cur.get("snippet") or ""),int(cur.get("unread_count") or 0),str(cur.get("row_time") or ""))
            first=float(cur.get("first_seen_ts") or now)
            cur.update({
                "name":name,"first_seen_ts":first,"last_seen_ts":now,
                "snippet":snippet[:360],"unread_count":count,
                "row_time":str(row.get("row_time") or ""),
                "content_type":str(row.get("content_type") or "text"),
                "needs_reply":not closing,
            })
            registry[name]=cur; current.add(name); visible_messages+=count
            new_sig=(cur.get("snippet"),cur.get("unread_count"),cur.get("row_time"))
            if new_sig!=previous_sig:
                self._diagnostic_log("unread_contact_observed",client=name,unread_count=count,row_time=cur.get("row_time"),content_type=cur.get("content_type"),needs_reply=bool(cur.get("needs_reply")),snippet=snippet[:240])
        self._diagnostic_unread_registry=registry
        self._diagnostic_unread_total_whatsapp=max(total,len(current))
        self._diagnostic_unread_visible=len(current)
        self._diagnostic_unread_message_total=visible_messages
        self._diagnostic_current_unread_names=current

    def _diagnostic_whatsapp_overview_payload(self):
        import time
        now=time.time(); reg=dict(getattr(self,"_diagnostic_unread_registry",{}) or {}); names=set(getattr(self,"_diagnostic_current_unread_names",set()) or set())
        items=[]
        for n in names:
            d=reg.get(n) if isinstance(reg.get(n),dict) else {}
            items.append({"client":n,"unread_count":int(d.get("unread_count") or 1),"row_time":str(d.get("row_time") or ""),"content_type":str(d.get("content_type") or "text"),"needs_reply":bool(d.get("needs_reply",True)),"snippet":str(d.get("snippet") or ""),"first_seen_ts":float(d.get("first_seen_ts") or now),"waiting_visible_seconds":max(0,int(now-float(d.get("first_seen_ts") or now)))})
        items.sort(key=lambda x:(not x.get("needs_reply",True),x.get("first_seen_ts",now)))
        live=getattr(self,"_diagnostic_live_call",None)
        live_payload=None
        if isinstance(live,dict):
            start=float(live.get("start_ts") or now); live_payload={"client":str(live.get("client") or ""),"call_type":str(live.get("call_type") or "voice"),"duration_seconds":max(int(live.get("duration_seconds") or 0),max(0,int(now-start)))}
        return {"whatsapp_unread_total":int(getattr(self,"_diagnostic_unread_total_whatsapp",0) or 0),"detailed_visible_now":len(items),"unread_messages_visible":int(getattr(self,"_diagnostic_unread_message_total",0) or 0),"live_call":live_payload,"unread_contacts":items}

    def _diagnostic_whatsapp_overview_text(self):
        import time
        p=self._diagnostic_whatsapp_overview_payload(); total=int(p.get("whatsapp_unread_total") or 0); items=list(p.get("unread_contacts") or []); live=p.get("live_call")
        def fmt(s):
            s=max(0,int(s or 0));h=s//3600;m=(s%3600)//60;sec=s%60
            if h:return f"{h}h {m:02d}m"
            if m:return f"{m}m {sec:02d}s"
            return f"{sec}s"
        out=["PANORAMA DO WHATSAPP AGORA",f"Não lidas no WhatsApp: {total}",f"Detalhadas na tela agora: {len(items)} contato(s) • {int(p.get('unread_messages_visible') or 0)} mensagem(ns) não lida(s) visível(is)"]
        if live:out.append(f"📞 Ligação ativa: {str(live.get('client') or 'Contato')} — {fmt(live.get('duration_seconds') or 0)}")
        if total>len(items):out.append(f"ℹ O WhatsApp indica {total}, mas mantém só parte das linhas carregadas; o ALIYVO acumula os detalhes conforme elas aparecem/rolam.")
        if not items:
            out.append("Nenhum contato individual não lido detalhado neste instante.")
            return "\n".join(out)
        out.append("")
        for i,d in enumerate(items[:20],1):
            status="aguarda ação" if d.get("needs_reply",True) else "encerramento / sem resposta necessária"
            cnt=max(1,int(d.get("unread_count") or 1));tm=str(d.get("row_time") or "");sn=str(d.get("snippet") or "").replace("\n"," ").strip()
            if len(sn)>105:sn=sn[:102]+"..."
            out.append(f"{i}. {d.get('client')} — {cnt} msg • {tm or '-'} • {status}")
            if sn:out.append(f"   {sn}")
        return "\n".join(out)

'''
text=text.replace(anchor,helpers+anchor,1)

# Atualiza o panorama em cada scan depois que grupos foram aprendidos, antes da fila de nao lidos.
ms=method_source(text,'MainWindow','_diagnostic_scan_done')
scan_anchor='        unread_rows={}\n'
if scan_anchor not in ms: raise SystemExit('scan unread_rows anchor not found')
ms=ms.replace(scan_anchor,'        try:self._diagnostic_update_whatsapp_overview(result,now)\n        except Exception:pass\n\n'+scan_anchor,1)
text=replace_method(text,'MainWindow','_diagnostic_scan_done',ms)

# Mostra panorama no topo do Diagnostico ao vivo.
ms=method_source(text,'MainWindow','_diagnostic_show_dialog')
old='            txt.setPlainText(self._diagnostic_enhanced_text(filtered_rows()))\n'
if old not in ms: raise SystemExit('diagnostic dialog text anchor not found')
ms=ms.replace(old,'            txt.setPlainText(self._diagnostic_whatsapp_overview_text()+"\\n\\n"+self._diagnostic_enhanced_text(filtered_rows()))\n',1)
text=replace_method(text,'MainWindow','_diagnostic_show_dialog',ms)

# O backup automatico leva tambem o panorama atual e os dados estruturados da lista nao lida.
ms=method_source(text,'MainWindow','_diagnostic_daily_backup')
old='                "full_diagnostic":self._diagnostic_enhanced_text(rows),\n'
if old not in ms: raise SystemExit('backup full diagnostic anchor not found')
ms=ms.replace(old,'                "full_diagnostic":self._diagnostic_whatsapp_overview_text()+"\\n\\n"+self._diagnostic_enhanced_text(rows),\n                "whatsapp_overview":self._diagnostic_whatsapp_overview_payload(),\n',1)
text=replace_method(text,'MainWindow','_diagnostic_daily_backup',ms)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched complete WhatsApp overview',version)
