from pathlib import Path
import sys, json, re, ast

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update.json').read_text(encoding='utf-8')) if (root/'update.json').exists() else {'version':'0.22.11'}
version=str(meta.get('version') or '0.22.11')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

if 'start_network_capture' not in text:
    old='''        self._last_search_token=0\n        self._background_mode=False\n        CATALOG_PROFILE_DIR.mkdir(parents=True,exist_ok=True)'''
    new='''        self._last_search_token=0\n        self._background_mode=False\n        self._capture_started=False\n        CATALOG_PROFILE_DIR.mkdir(parents=True,exist_ok=True)'''
    text=text.replace(old,new,1)

    anchor='''    def _read_if_current(self,token,callback):\n        if token!=self._last_search_token: return\n        self.read_current(callback)\n\n    def read_current(self,callback):'''
    methods=r"""    def _read_if_current(self,token,callback):
        if token!=self._last_search_token: return
        self.read_current(callback)

    def start_network_capture(self,callback=None):
        self._capture_started=True
        js=r'''return (() => {
          try{
            const PREFIX="ALIYVO_CAPTURE::";
            const redact=(v)=>{
              let s=String(v==null?"":v);
              s=s.replace(/((?:password|senha|token|csrf|authorization|session|sessao)[^=&:\\s]{0,30}[=:]\\s*)[^&\\s,}]+/gi,"$1***");
              return s.slice(0,5000);
            };
            const read=()=>{ try{ if((window.name||"").startsWith(PREFIX)) return JSON.parse(window.name.slice(PREFIX.length)||"[]"); }catch(e){} return []; };
            const save=(arr)=>{ try{ window.name=PREFIX+JSON.stringify(arr.slice(-120)); }catch(e){} };
            const log=(kind,obj)=>{ const arr=read(); arr.push(Object.assign({time:new Date().toISOString(),kind:kind,url:location.href},obj||{})); save(arr); };
            save([]); log("capture_start",{title:document.title||""});
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
                try{ const f=ev.target; const fd=new FormData(f); const vals=[]; for(const [k,v] of fd.entries()){ if(/pass|senha|token|csrf|auth|session|sessao/i.test(k)) vals.push(k+'=***'); else vals.push(k+'='+String(v).slice(0,300)); } log("form_submit",{method:String((f.method||'GET').toUpperCase()),requestUrl:String(f.action||location.href),body:redact(vals.join('&'))}); }catch(e){}
              },true);
              document.addEventListener('click',function(ev){
                try{ const el=ev.target&&ev.target.closest?ev.target.closest('button,a,[role="button"],input[type="submit"]'):null; if(!el) return; const label=((el.innerText||el.textContent||el.value||'').trim()).slice(0,120); const href=el.href||''; if(/buscar|pesquisar|consultar|placa|detalh|descri|ve[ií]culo/i.test(label+' '+href)) log("click",{label:label,requestUrl:String(href)}); }catch(e){}
              },true);
              const oldOpenWin=window.open;
              window.open=function(url){ log("window_open",{requestUrl:String(url||'')}); return oldOpenWin.apply(this,arguments); };
            }
            return {ok:true,message:"Captura iniciada"};
          }catch(e){ return {ok:false,error:String(e)}; }
        })();'''
        def done(payload):
            result=self._unwrap_js(payload)
            if callback: callback(result)
        self.evaluate(js,done)

    def read_network_capture(self,callback):
        js=r'''return (() => {
          try{ const PREFIX="ALIYVO_CAPTURE::"; let arr=[]; try{ if((window.name||"").startsWith(PREFIX)) arr=JSON.parse(window.name.slice(PREFIX.length)||"[]"); }catch(e){} return {ok:true,events:arr,currentUrl:location.href||"",title:document.title||"",text:(document.body&&document.body.innerText||"").slice(0,8000)}; }
          catch(e){return {ok:false,error:String(e)};}
        })();'''
        def done(payload): callback(self._unwrap_js(payload))
        self.evaluate(js,done)

    def read_current(self,callback):"""
    if anchor not in text: raise SystemExit('anchor capture methods not found')
    text=text.replace(anchor,methods,1)

if 'self.on_capture=None' not in text:
    text=text.replace('''        self.on_search=None\n        self.on_read_current=None''','''        self.on_search=None\n        self.on_read_current=None\n        self.on_capture=None''',1)
    text=text.replace('''        self.search_btn=QPushButton("🔎 Buscar placa")\n        self.connect_btn=QPushButton("🔑 Reconectar")\n        row.addWidget(self.search_btn,1); row.addWidget(self.connect_btn)''','''        self.search_btn=QPushButton("🔎 Buscar placa")\n        self.connect_btn=QPushButton("🔑 Reconectar")\n        self.capture_btn=QPushButton("🧪 Diagnóstico")\n        row.addWidget(self.search_btn,1); row.addWidget(self.capture_btn); row.addWidget(self.connect_btn)''',1)
    text=text.replace('''        self.raw=QTextEdit(); self.raw.setReadOnly(True)\n        self.raw.setStyleSheet("font-family:Consolas;font-size:9px;background:#0F172A;color:#E2E8F0;")\n        self.tabs.addTab(self.result,"Resultado")\n        self.tabs.addTab(self.soma,"Base Soma")\n        self.tabs.addTab(self.raw,"Detalhes")''','''        self.raw=QTextEdit(); self.raw.setReadOnly(True)\n        self.raw.setStyleSheet("font-family:Consolas;font-size:9px;background:#0F172A;color:#E2E8F0;")\n        self.capture=QTextEdit(); self.capture.setReadOnly(True)\n        self.capture.setStyleSheet("font-family:Consolas;font-size:9px;background:#111827;color:#E5E7EB;")\n        self.tabs.addTab(self.result,"Resultado")\n        self.tabs.addTab(self.soma,"Base Soma")\n        self.tabs.addTab(self.raw,"Detalhes")\n        self.tabs.addTab(self.capture,"Diagnóstico")''',1)
    text=text.replace('''        self.search_btn.clicked.connect(self._search)\n        self.connect_btn.clicked.connect(self._connect)\n        self.plate.returnPressed.connect(self._search)''','''        self.search_btn.clicked.connect(self._search)\n        self.connect_btn.clicked.connect(self._connect)\n        self.capture_btn.clicked.connect(self._capture)\n        self.plate.returnPressed.connect(self._search)''',1)
    text=text.replace('''    def _connect(self):\n        if self.on_connect: self.on_connect()\n    def _open(self):''','''    def _connect(self):\n        if self.on_connect: self.on_connect()\n    def _capture(self):\n        if self.on_capture: self.on_capture()\n    def _open(self):''',1)
    text=text.replace('''        self.plate_panel.on_search=self._catalog_search_plate\n        self.plate_panel.on_read_current=self._catalog_read_current''','''        self.plate_panel.on_search=self._catalog_search_plate\n        self.plate_panel.on_read_current=self._catalog_read_current\n        self.plate_panel.on_capture=self._catalog_capture_start''',1)

if 'def _catalog_capture_start(self):' not in text:
    anchor='''    def _catalog_read_current(self):\n        browser=self._get_catalog_window(False)\n        self.plate_panel.status.setText("Lendo o resultado técnico...")\n        browser.read_current(self._catalog_receive_page)\n\n    def _catalog_extract(self,text):'''
    insert=r"""    def _catalog_read_current(self):
        browser=self._get_catalog_window(False)
        self.plate_panel.status.setText("Lendo o resultado técnico...")
        browser.read_current(self._catalog_receive_page)

    def _catalog_capture_start(self):
        browser=self._get_catalog_window(False)
        try:
            browser._background_mode=False; browser.setWindowOpacity(1.0); browser.resize(1280,820)
            screen=QApplication.primaryScreen().availableGeometry()
            browser.move(max(0,screen.x()+(screen.width()-browser.width())//2), max(0,screen.y()+(screen.height()-browser.height())//2))
        except Exception: pass
        self.plate_panel.tabs.setCurrentWidget(self.plate_panel.capture)
        self.plate_panel.capture.setPlainText("DIAGNÓSTICO DA CONSULTA\n\nA janela técnica vai abrir. Faça UMA busca manual por uma placa conhecida.\nNão faça login novamente durante este teste. Aguarde alguns segundos.\n\nO objetivo é descobrir a chamada real usada pelo site e eliminar os cliques manuais depois deste teste.")
        self.plate_panel.status.setText("🧪 Preparando captura da consulta...")
        def started(res):
            if not res.get("ok"):
                self.plate_panel.status.setText("⚠ Não consegui iniciar o diagnóstico: "+str(res.get("error") or "erro")); return
            self.plate_panel.status.setText("🧪 Captura ativa. Faça UMA busca manual na janela que abriu.")
            browser.show(); browser.raise_(); browser.activateWindow()
            for delay in (3500,6500,10000,15000): QTimer.singleShot(delay,lambda b=browser:self._catalog_capture_read(b))
        browser.start_network_capture(started)

    def _catalog_capture_read(self,browser):
        def got(res):
            if not res.get("ok"): return
            events=res.get("events") or []; lines=["CAPTURA DA CONSULTA","","Página atual: "+str(res.get("currentUrl") or ""),""]; useful=0
            for ev in events:
                if not isinstance(ev,dict): continue
                kind=str(ev.get("kind") or ""); url=str(ev.get("requestUrl") or ev.get("url") or ""); method=str(ev.get("method") or ""); body=str(ev.get("body") or ""); response=str(ev.get("response") or ""); label=str(ev.get("label") or "")
                rx=r'(?i)(password|senha|token|csrf|authorization|session|sessao)([^=&:\\s]{0,30}[=:]\\s*)[^&\\s,}]+'
                body=re.sub(rx,lambda m:m.group(1)+m.group(2)+"***",body); response=re.sub(rx,lambda m:m.group(1)+m.group(2)+"***",response)
                if kind in ("fetch_request","fetch_response","xhr_request","xhr_response","form_submit","window_open"):
                    useful+=1; lines.append(f"[{kind}] {method} {url}".strip())
                    if body: lines.append("BODY: "+body[:1800])
                    if response: lines.append("RESPOSTA: "+response[:2500])
                    lines.append("")
                elif kind=="click" and label: lines.append("[click] "+label+((' -> '+url) if url else ''))
            if not useful: lines += ["Ainda não apareceu uma chamada HTTP útil.","Faça a busca manual e aguarde até 15 segundos."]
            self.plate_panel.capture.setPlainText("\n".join(lines)); self.plate_panel.tabs.setCurrentWidget(self.plate_panel.capture)
            if useful: self.plate_panel.status.setText(f"✅ Diagnóstico capturou {useful} chamada(s).")
        browser.read_network_capture(got)

    def _catalog_extract(self,text):"""
    if anchor not in text: raise SystemExit('anchor main capture not found')
    text=text.replace(anchor,insert,1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched',version)
