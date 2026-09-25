from pathlib import Path
import sys,re

p=Path(sys.argv[1])/'_app'/'main.py'
s=p.read_text(encoding='utf-8')
if 'ALIYVO_VERSION = "0.23.11"' not in s:
    raise SystemExit('base 0.23.11 nao encontrada')
s=s.replace('ALIYVO_VERSION = "0.23.11"','ALIYVO_VERSION = "0.23.12"',1)
s=s.replace('aliyvo_version="0.23.11"','aliyvo_version="0.23.12"')

pat=r'(?ms)^    def _attendance_open_chat\(self,name\):.*?(?=^    def _attendance_open_tool\(self,tool\):)'
m=re.search(pat,s)
if not m: raise SystemExit('_attendance_open_chat nao encontrado')

new=r'''    def _attendance_phone_for_contact(self,name):
        import re
        raw=str(name or "").strip()
        digits=re.sub(r"\D","",raw)
        if len(digits)>=10:
            phone=digits
        else:
            phone=""
            try:
                con=self.db();cur=con.cursor()
                row=cur.execute("""
                    SELECT telefone
                    FROM campanha_contatos
                    WHERE ativo=1
                      AND (
                        lower(trim(coalesce(whatsapp_nome,'')))=lower(trim(?))
                        OR lower(trim(coalesce(nome,'')))=lower(trim(?))
                      )
                      AND telefone NOT LIKE 'pendente:%'
                    ORDER BY id DESC
                    LIMIT 1
                """,(raw,raw)).fetchone()
                con.close()
                if row: phone=re.sub(r"\D","",str(row[0] or ""))
            except Exception:
                phone=""
        if not phone:return ""
        # Brasil: contatos locais salvos com DDD (10/11 dígitos) recebem DDI 55.
        if len(phone) in (10,11):phone="55"+phone
        return phone if len(phone)>=12 else ""

    def _attendance_open_chat(self,name):
        from PyQt6.QtCore import QUrl
        name=str(name or "").strip()
        if not name:return

        phone=self._attendance_phone_for_contact(name)
        if phone:
            # Caminho determinístico: o próprio WhatsApp Web abre o chat pelo número.
            url=f"https://web.whatsapp.com/send?phone={phone}"
            try:
                self.web.setUrl(QUrl(url))
                QTimer.singleShot(1800,lambda:self._attendance_scan(force=True))
                return
            except Exception:
                pass

        # Fallback para contatos conhecidos apenas pelo nome.
        js=r"""
        ((wanted)=>{
          const clean=t=>String(t||'').replace(/\s+/g,' ').trim();
          const clickMatch=()=>{
            const spans=Array.from(document.querySelectorAll('#pane-side span[title], span[title]'));
            for(const sp of spans){
              const n=clean(sp.getAttribute('title')||sp.textContent||'');
              if(n===wanted){
                const row=sp.closest('[role="listitem"],[role="row"],[data-testid="cell-frame-container"]') || sp.closest('div');
                if(row){row.click();return true;}
              }
            }
            return false;
          };
          if(clickMatch())return {ok:true,via:'visible'};

          const boxes=Array.from(document.querySelectorAll('div[contenteditable="true"][role="textbox"],div[contenteditable="true"][data-tab]'));
          let search=null;
          for(const el of boxes){
            const a=clean(el.getAttribute('aria-label')||el.getAttribute('title')||el.getAttribute('data-placeholder')||'').toLowerCase();
            const r=el.getBoundingClientRect();
            if(a.includes('pesquis')||a.includes('search')||(r.top<180&&r.left<650&&r.width>150)){search=el;break;}
          }
          if(!search)return {ok:false,reason:'search_not_found'};
          try{
            search.focus();
            search.textContent='';
            search.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'deleteContentBackward'}));
            search.textContent=wanted;
            search.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:wanted}));
            search.dispatchEvent(new KeyboardEvent('keyup',{bubbles:true,key:'a'}));
          }catch(e){return {ok:false,reason:'search_fill_failed'};}

          return new Promise(resolve=>{
            let n=0;
            const timer=setInterval(()=>{
              n++;
              if(clickMatch()){clearInterval(timer);resolve({ok:true,via:'search'});return;}
              if(n>=20){clearInterval(timer);resolve({ok:false,reason:'contact_not_found'});}
            },250);
          });
        })(__NAME__));
        """.replace('__NAME__',json.dumps(name,ensure_ascii=False))

        def done(result):
            ok=bool(result.get("ok")) if isinstance(result,dict) else bool(result)
            if ok:
                QTimer.singleShot(650,lambda:self._attendance_scan(force=True))
            else:
                reason=str((result or {}).get("reason") or "") if isinstance(result,dict) else ""
                QMessageBox.information(self,"WhatsApp",f"Não consegui abrir a conversa de {name} automaticamente."+("\n\nMotivo técnico: "+reason if reason else ""))
        try:self.web.page().runJavaScript(js,done)
        except Exception:pass

'''
s=s[:m.start()]+new+s[m.end():]
p.write_text(s,encoding='utf-8')
print('PATCH_DIRECT_CHAT_V2312=OK')
