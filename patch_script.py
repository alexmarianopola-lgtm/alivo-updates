from pathlib import Path
import sys, json, re, ast

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v2.json').read_text(encoding='utf-8')) if (root/'update-v2.json').exists() else {'version':'0.22.12'}
version=str(meta.get('version') or '0.22.12')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# Update only existing diagnostic methods from 0.22.11.
start=text.find('    def start_network_capture(self,callback=None):')
end=text.find('    def read_network_capture(self,callback):', start)
if start==-1 or end==-1:
    raise SystemExit('start_network_capture not found')

new_start=r'''    def start_network_capture(self,callback=None,reset=True):
        self._capture_started=True
        reset_js='true' if reset else 'false'
        js=r'''return (() => {
          try{
            const PREFIX="ALIYVO_CAPTURE::";
            const doReset=__RESET__;
            const redact=(v)=>{
              let s=String(v==null?"":v);
              s=s.replace(/((?:password|senha|token|csrf|authorization|session|sessao)[^=&:\\s]{0,30}[=:]\\s*)[^&\\s,}]+/gi,"$1***");
              return s.slice(0,6000);
            };
            const read=()=>{ try{ if((window.name||"").startsWith(PREFIX)) return JSON.parse(window.name.slice(PREFIX.length)||"[]"); }catch(e){} return []; };
            const save=(arr)=>{ try{ window.name=PREFIX+JSON.stringify(arr.slice(-220)); }catch(e){} };
            const log=(kind,obj)=>{ const arr=read(); arr.push(Object.assign({time:new Date().toISOString(),kind:kind,url:location.href},obj||{})); save(arr); };
            if(doReset) save([]);
            log("capture_page",{title:document.title||"",href:location.href});

            // Snapshot forms/fields without exposing secret values.
            try{
              const forms=[...document.forms].map((f,i)=>({
                index:i,
                method:String((f.method||'GET').toUpperCase()),
                action:String(f.action||location.href),
                fields:[...f.elements].map(e=>({name:String(e.name||''),type:String(e.type||''),id:String(e.id||'')})).filter(x=>x.name||x.id)
              }));
              log("forms_snapshot",{forms:forms});
            }catch(e){}

            if(!window.__aliyvoNetCaptureInstalled){
              window.__aliyvoNetCaptureInstalled=true;

              const oldFetch=window.fetch;
              if(oldFetch){
                window.fetch=async function(input,init){
                  const url=typeof input==='string'?input:(input&&input.url)||'';
                  const method=(init&&init.method)||((input&&input.method)||'GET');
                  const body=redact(init&&init.body);
                  log("fetch_request",{method:String(method),requestUrl:String(url),body:body});
                  try{
                    const resp=await oldFetch.apply(this,arguments);
                    try{ const clone=resp.clone(); const txt=await clone.text(); log("fetch_response",{method:String(method),requestUrl:String(url),status:resp.status,response:redact(txt)}); }catch(e){}
                    return resp;
                  }catch(e){ log("fetch_error",{requestUrl:String(url),error:String(e)}); throw e; }
                };
              }

              const X=window.XMLHttpRequest;
              if(X){
                const oldOpen=X.prototype.open, oldSend=X.prototype.send;
                X.prototype.open=function(method,url){ this.__aliyvoMethod=method; this.__aliyvoUrl=url; return oldOpen.apply(this,arguments); };
                X.prototype.send=function(body){
                  const xhr=this;
                  log("xhr_request",{method:String(xhr.__aliyvoMethod||'GET'),requestUrl:String(xhr.__aliyvoUrl||''),body:redact(body)});
                  xhr.addEventListener('load',function(){ let txt=''; try{txt=xhr.responseText||'';}catch(e){} log("xhr_response",{method:String(xhr.__aliyvoMethod||'GET'),requestUrl:String(xhr.__aliyvoUrl||''),status:xhr.status,response:redact(txt)}); });
                  return oldSend.apply(this,arguments);
                };
              }

              document.addEventListener('submit',function(ev){
                try{
                  const f=ev.target; const fd=new FormData(f); const vals=[];
                  for(const [k,v] of fd.entries()){
                    if(/pass|senha|token|csrf|auth|session|sessao/i.test(k)) vals.push(k+'=***');
                    else vals.push(k+'='+String(v).slice(0,300));
                  }
                  log("form_submit",{method:String((f.method||'GET').toUpperCase()),requestUrl:String(f.action||location.href),body:redact(vals.join('&'))});
                }catch(e){}
              },true);

              document.addEventListener('click',function(ev){
                try{
                  const el=ev.target&&ev.target.closest?ev.target.closest('button,a,[role="button"],input[type="submit"]'):null;
                  if(!el) return;
                  const label=((el.innerText||el.textContent||el.value||'').trim()).slice(0,140);
                  const href=el.href||'';
                  const form=el.form||null;
                  log("click",{label:label,requestUrl:String(href),formAction:String(form&&form.action||''),formMethod:String(form&&form.method||'')});
                }catch(e){}
              },true);

              const oldOpenWin=window.open;
              window.open=function(url){ log("window_open",{requestUrl:String(url||'')}); return oldOpenWin.apply(this,arguments); };

              const oldPush=history.pushState, oldReplace=history.replaceState;
              history.pushState=function(){ log("push_state",{requestUrl:String(arguments[2]||'')}); return oldPush.apply(this,arguments); };
              history.replaceState=function(){ log("replace_state",{requestUrl:String(arguments[2]||'')}); return oldReplace.apply(this,arguments); };

              window.addEventListener('beforeunload',()=>log("before_unload",{href:location.href}));
            }

            // Existing resource entries often reveal server endpoints loaded by the page.
            try{
              const entries=performance.getEntriesByType('resource').slice(-80).map(e=>({name:e.name,initiatorType:e.initiatorType}));
              log("resources_snapshot",{entries:entries});
            }catch(e){}

            return {ok:true,message:"Captura ativa nesta página",href:location.href};
          }catch(e){ return {ok:false,error:String(e)}; }
        })();'''.replace('__RESET__',reset_js)
        def done(payload):
            result=self._unwrap_js(payload)
            if callback: callback(result)
        self.evaluate(js,done)

'''
text=text[:start]+new_start+text[end:]

# Replace diagnostic start/read loop so hooks are reinstalled after every navigation.
start=text.find('    def _catalog_capture_start(self):')
end=text.find('    def _catalog_extract(self,text):', start)
if start==-1 or end==-1:
    raise SystemExit('catalog capture methods not found')

new_catalog=r'''    def _catalog_capture_start(self):
        browser=self._get_catalog_window(False)
        try:
            browser._background_mode=False; browser.setWindowOpacity(1.0); browser.resize(1280,820)
            screen=QApplication.primaryScreen().availableGeometry()
            browser.move(max(0,screen.x()+(screen.width()-browser.width())//2), max(0,screen.y()+(screen.height()-browser.height())//2))
        except Exception: pass
        self.plate_panel.tabs.setCurrentWidget(self.plate_panel.capture)
        self.plate_panel.capture.setPlainText("DIAGNÓSTICO DA CONSULTA 2\n\nFaça o caminho completo UMA vez:\n1) clique em Buscar pela Placa no catálogo\n2) digite uma placa\n3) clique Buscar\n4) abra o veículo se o site pedir\n\nO ALIYVO vai se reinstalar sozinho em cada página e registrar o caminho.")
        self.plate_panel.status.setText("🧪 Preparando captura persistente...")
        self._capture_generation=getattr(self,'_capture_generation',0)+1
        generation=self._capture_generation

        def started(res):
            if not res.get("ok"):
                self.plate_panel.status.setText("⚠ Não consegui iniciar: "+str(res.get("error") or "erro")); return
            self.plate_panel.status.setText("🧪 Captura ativa. Faça o caminho completo da consulta uma vez.")
            browser.show(); browser.raise_(); browser.activateWindow()
            # Reinject after navigations. First call already reset capture; all others preserve log in window.name.
            for delay in (900,1800,3000,4500,6500,8500,11000,14000,18000,23000,28000):
                QTimer.singleShot(delay,lambda b=browser,g=generation:self._catalog_capture_rearm(b,g))
            for delay in (2500,5000,8000,12000,16000,21000,27000,32000):
                QTimer.singleShot(delay,lambda b=browser,g=generation:self._catalog_capture_read(b,g))
        browser.start_network_capture(started,True)

    def _catalog_capture_rearm(self,browser,generation):
        if generation!=getattr(self,'_capture_generation',None): return
        try: browser.start_network_capture(None,False)
        except Exception: pass

    def _catalog_capture_read(self,browser,generation=None):
        if generation is not None and generation!=getattr(self,'_capture_generation',None): return
        def got(res):
            if not res.get("ok"): return
            events=res.get("events") or []
            lines=["CAPTURA DA CONSULTA 2","","Página atual: "+str(res.get("currentUrl") or ""),""]
            useful=0
            for ev in events:
                if not isinstance(ev,dict): continue
                kind=str(ev.get("kind") or "")
                url=str(ev.get("requestUrl") or ev.get("href") or ev.get("url") or "")
                method=str(ev.get("method") or "")
                body=str(ev.get("body") or "")
                response=str(ev.get("response") or "")
                label=str(ev.get("label") or "")
                if kind in ("form_submit","fetch_request","fetch_response","xhr_request","xhr_response","window_open","push_state","replace_state","before_unload"):
                    # Ignore known analytics noise unless it is the only thing available.
                    if 'clarity.ms' in url.lower():
                        continue
                    useful+=1
                    lines.append(f"[{kind}] {method} {url}".strip())
                    if body: lines.append("BODY: "+body[:2200])
                    if response: lines.append("RESPOSTA: "+response[:2800])
                    lines.append("")
                elif kind=="click" and label:
                    lines.append("[click] "+label+((' -> '+url) if url else ''))
                    fa=str(ev.get('formAction') or '')
                    fm=str(ev.get('formMethod') or '')
                    if fa or fm: lines.append("  form: "+fm.upper()+" "+fa)
                elif kind=="forms_snapshot":
                    forms=ev.get('forms') or []
                    if forms:
                        lines.append("[forms_snapshot]")
                        for f in forms[:8]:
                            lines.append("  "+str(f.get('method') or '')+" "+str(f.get('action') or ''))
                            fields=f.get('fields') or []
                            if fields:
                                lines.append("  campos: "+", ".join((str(x.get('name') or x.get('id') or '')+":"+str(x.get('type') or '')) for x in fields[:30]))
                        lines.append("")
                elif kind=="resources_snapshot":
                    entries=ev.get('entries') or []
                    interesting=[]
                    for x in entries:
                        u=str((x or {}).get('name') or '')
                        if u and 'clarity.ms' not in u.lower() and ('catalogofraga' in u.lower() or '/api/' in u.lower() or 'plac' in u.lower() or 'veic' in u.lower()):
                            interesting.append(u)
                    if interesting:
                        lines.append('[resources]')
                        lines.extend('  '+u for u in interesting[-20:])
                        lines.append('')
            if not useful:
                lines += ["Ainda não apareceu POST/XHR útil.","Complete a busca manual e aguarde até 30 segundos."]
            self.plate_panel.capture.setPlainText("\n".join(lines))
            self.plate_panel.tabs.setCurrentWidget(self.plate_panel.capture)
            if useful:
                self.plate_panel.status.setText(f"✅ Diagnóstico capturou {useful} evento(s) útil(eis).")
        browser.read_network_capture(got)

'''
text=text[:start]+new_catalog+text[end:]

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched',version)
