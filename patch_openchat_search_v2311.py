from pathlib import Path
import sys,re

p=Path(sys.argv[1])/'_app'/'main.py'
s=p.read_text(encoding='utf-8')
if 'ALIYVO_VERSION = "0.23.10"' not in s:
    raise SystemExit('base 0.23.10 nao encontrada')
s=s.replace('ALIYVO_VERSION = "0.23.10"','ALIYVO_VERSION = "0.23.11"',1)
s=s.replace('aliyvo_version="0.23.10"','aliyvo_version="0.23.11"')

pat=r'(?ms)^    def _attendance_open_chat\(self,name\):.*?(?=^    def _attendance_open_tool\(self,tool\):)'
m=re.search(pat,s)
if not m: raise SystemExit('_attendance_open_chat nao encontrado')

new=r'''    def _attendance_open_chat(self,name):
        name=str(name or "").strip()
        if not name:return
        js=r"""
        ((wanted)=>{
          const clean=t=>String(t||'').replace(/\s+/g,' ').trim();
          const digits=t=>String(t||'').replace(/\D+/g,'');
          const same=(a,b)=>{
            a=clean(a);b=clean(b);
            if(!a||!b)return false;
            if(a===b)return true;
            const da=digits(a),db=digits(b);
            if(da.length>=8 && db.length>=8 && (da===db || da.endsWith(db) || db.endsWith(da)))return true;
            return false;
          };
          const clickMatch=()=>{
            const pane=document.querySelector('#pane-side') || document;
            const spans=Array.from(pane.querySelectorAll('span[title]'));
            for(const sp of spans){
              const n=clean(sp.getAttribute('title')||sp.textContent||'');
              if(same(n,wanted)){
                const row=sp.closest('[role="listitem"],[role="row"],[data-testid="cell-frame-container"]') || sp.closest('div');
                if(row){row.click();return true;}
              }
            }
            return false;
          };
          const setSearch=(el,value)=>{
            try{
              el.focus();
              const sel=window.getSelection();sel.removeAllRanges();
              const r=document.createRange();r.selectNodeContents(el);sel.addRange(r);
              document.execCommand('insertText',false,value);
              el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:value}));
              el.dispatchEvent(new Event('change',{bubbles:true}));
              return true;
            }catch(e){return false;}
          };
          const findSearch=()=>{
            const candidates=[
              ...document.querySelectorAll('div[contenteditable="true"][role="textbox"]'),
              ...document.querySelectorAll('div[contenteditable="true"][data-tab]')
            ];
            for(const el of candidates){
              const aria=clean(el.getAttribute('aria-label')||'').toLowerCase();
              const title=clean(el.getAttribute('title')||'').toLowerCase();
              const ph=clean(el.getAttribute('data-placeholder')||'').toLowerCase();
              if(aria.includes('pesquis')||aria.includes('search')||title.includes('pesquis')||title.includes('search')||ph.includes('pesquis')||ph.includes('search'))return el;
            }
            return candidates.find(el=>{
              const box=el.getBoundingClientRect();
              return box.top<180 && box.width>120;
            }) || null;
          };
          const clickSearchButton=()=>{
            const all=Array.from(document.querySelectorAll('button,[role="button"]'));
            for(const el of all){
              const a=clean(el.getAttribute('aria-label')||el.getAttribute('title')||'').toLowerCase();
              if(a.includes('pesquis')||a.includes('search')){el.click();return true;}
            }
            return false;
          };
          return new Promise(resolve=>{
            try{
              if(clickMatch()){resolve({ok:true,via:'visible'});return;}
              clickSearchButton();
              setTimeout(()=>{
                const search=findSearch();
                if(!search){resolve({ok:false,reason:'search_not_found'});return;}
                setSearch(search,wanted);
                let tries=0;
                const timer=setInterval(()=>{
                  tries++;
                  if(clickMatch()){
                    clearInterval(timer);
                    try{
                      search.focus();
                      document.execCommand('selectAll',false,null);
                      document.execCommand('delete',false,null);
                    }catch(e){}
                    resolve({ok:true,via:'search'});
                    return;
                  }
                  if(tries>=15){
                    clearInterval(timer);
                    resolve({ok:false,reason:'contact_not_found'});
                  }
                },220);
              },300);
            }catch(e){resolve({ok:false,reason:String(e)});}
          });
        })(__NAME__));
        """.replace('__NAME__',json.dumps(name,ensure_ascii=False))
        def done(result):
            ok=bool(result.get("ok")) if isinstance(result,dict) else bool(result)
            if not ok:
                reason=str((result or {}).get("reason") or "") if isinstance(result,dict) else ""
                QMessageBox.information(self,"WhatsApp",f"Não consegui abrir a conversa de {name} automaticamente."+("\n\nMotivo técnico: "+reason if reason else ""))
            else:
                QTimer.singleShot(650,lambda:self._attendance_scan(force=True))
        try:self.web.page().runJavaScript(js,done)
        except Exception:pass

'''
s=s[:m.start()]+new+s[m.end():]
p.write_text(s,encoding='utf-8')
print('PATCH_OPENCHAT_SEARCH_V2311=OK')
