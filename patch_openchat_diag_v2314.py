from pathlib import Path
import sys,re

p=Path(sys.argv[1])/'_app'/'main.py'
s=p.read_text(encoding='utf-8')
if 'ALIYVO_VERSION = "0.23.13"' not in s:
    raise SystemExit('base 0.23.13 nao encontrada')
s=s.replace('ALIYVO_VERSION = "0.23.13"','ALIYVO_VERSION = "0.23.14"',1)
s=s.replace('aliyvo_version="0.23.13"','aliyvo_version="0.23.14"')

# Troca somente a função central de abertura de chat.
pat=r'(?ms)^    def _attendance_open_chat\(self,name\):.*?(?=^    def _attendance_open_tool\(self,tool\):)'
m=re.search(pat,s)
if not m: raise SystemExit('_attendance_open_chat nao encontrado')

new=r'''    def _attendance_open_chat(self,name):
        from PyQt6.QtCore import QTimer
        import re,time,json
        name=str(name or "").strip()
        if not name:
            QMessageBox.information(self,"Abrir conversa","O clique chegou ao ALIYVO, mas este lembrete não tem cliente/número associado.")
            return

        phone=self._attendance_phone_for_contact(name)
        url=f"https://web.whatsapp.com/send?phone={phone}" if phone else ""

        # Diagnóstico persistente do clique real do usuário.
        try:
            self._diagnostic_log(
                "open_chat_click",
                client=name,
                resolved_phone=phone,
                target_url=url,
                web_class=type(self.web).__name__,
                has_core=bool(getattr(self.web,"_core_webview2",None)),
                has_load_url=bool(hasattr(self.web,"load_url"))
            )
        except Exception:pass

        if not phone:
            # Para nome puro, mantém o mecanismo por busca.
            js=r"""
            ((wanted)=>{
              const norm=s=>String(s||'').replace(/\s+/g,' ').trim().toLowerCase();
              const want=norm(wanted);
              const clickVisible=()=>{
                const els=[...document.querySelectorAll('#pane-side span[title],#pane-side [role="gridcell"] span,span[title]')];
                for(const el of els){
                  const got=norm(el.getAttribute('title')||el.textContent||'');
                  if(got===want){
                    const row=el.closest('[role="listitem"],[role="row"],[data-testid="cell-frame-container"]')||el.closest('div');
                    if(row){row.click();return true;}
                  }
                }
                return false;
              };
              if(clickVisible())return {ok:true,mode:'visible'};
              const inputs=[...document.querySelectorAll('[contenteditable="true"][role="textbox"]')];
              const search=inputs.find(el=>{
                const r=el.getBoundingClientRect();
                const a=norm(el.getAttribute('aria-label')||el.getAttribute('data-placeholder')||'');
                return a.includes('pesquis')||a.includes('search')||(r.top<180&&r.left<700&&r.width>150);
              });
              if(!search)return {ok:false,reason:'search_not_found'};
              search.focus();
              try{document.execCommand('selectAll',false,null);document.execCommand('delete',false,null);}catch(e){}
              try{document.execCommand('insertText',false,wanted);}catch(e){search.textContent=wanted;}
              search.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:wanted}));
              return {ok:true,mode:'search_filled'};
            })(__NAME__));
            """.replace('__NAME__',json.dumps(name,ensure_ascii=False))
            def name_done(result):
                try:self._diagnostic_log("open_chat_name_result",client=name,result=result)
                except Exception:pass
                if isinstance(result,dict) and result.get("ok"):
                    QTimer.singleShot(700,lambda:self._attendance_scan(force=True))
                else:
                    QMessageBox.information(self,"Abrir conversa",f"O clique chegou, mas não consegui localizar '{name}' no WhatsApp.\n\nDiagnóstico: {result}")
            try:self.web.page().runJavaScript(js,name_done)
            except Exception as e:
                QMessageBox.warning(self,"Abrir conversa","Falha ao executar busca do WhatsApp:\n"+str(e))
            return

        # Telefone: tenta 3 níveis de navegação, do mais nativo para o compatível.
        results=[]
        navigated=False

        core=getattr(self.web,"_core_webview2",None)
        if core is not None:
            try:
                core.Navigate(url)
                results.append("CoreWebView2.Navigate=OK")
                navigated=True
            except Exception as e:
                results.append("CoreWebView2.Navigate=ERRO:"+str(e)[:100])

        if not navigated:
            try:
                self.web.load_url(url)
                results.append("load_url=OK")
                navigated=True
            except Exception as e:
                results.append("load_url=ERRO:"+str(e)[:100])

        if not navigated:
            try:
                js_nav="window.location.href="+json.dumps(url,ensure_ascii=False)+"; true;"
                self.web.page().runJavaScript(js_nav)
                results.append("window.location.href=DISPARADO")
                navigated=True
            except Exception as e:
                results.append("window.location.href=ERRO:"+str(e)[:100])

        try:self._diagnostic_log("open_chat_navigation",client=name,phone=phone,results=results,navigated=navigated)
        except Exception:pass

        if not navigated:
            QMessageBox.warning(
                self,"Abrir conversa",
                "O clique chegou ao ALIYVO, mas o navegador recusou todos os métodos de abertura.\n\n"
                +"\n".join(results)
            )
            return

        # Confere depois se a navegação realmente mudou a página.
        def verify():
            js=r"""(() => {
              try{
                const h=(location.href||'');
                const main=document.querySelector('#main');
                let title='';
                if(main){
                  const el=main.querySelector('header span[title]')||main.querySelector('header [dir="auto"]');
                  title=el ? (el.getAttribute('title')||el.textContent||'') : '';
                }
                return {href:h,title:String(title||'').trim(),hasMain:!!main};
              }catch(e){return {error:String(e)};}
            })();"""
            def checked(result):
                try:self._diagnostic_log("open_chat_verify",client=name,phone=phone,result=result,methods=results)
                except Exception:pass
                ok=isinstance(result,dict) and (phone in re.sub(r"\D","",str(result.get("href") or "")) or bool(result.get("hasMain")))
                if not ok:
                    QMessageBox.information(
                        self,"Diagnóstico do clique",
                        "O clique FOI recebido pelo ALIYVO e a navegação foi enviada ao WebView2, "
                        "mas o WhatsApp não confirmou a abertura.\n\n"
                        f"Cliente: {name}\nNúmero resolvido: {phone}\n"
                        f"Método: {' | '.join(results)}\nRetorno: {result}"
                    )
                else:
                    try:self._attendance_scan(force=True)
                    except Exception:pass
            try:self.web.page().runJavaScript(js,checked)
            except Exception as e:
                QMessageBox.information(
                    self,"Diagnóstico do clique",
                    f"O comando de abrir foi enviado.\nCliente: {name}\nNúmero: {phone}\n"
                    f"Método: {' | '.join(results)}\nNão consegui ler o retorno: {e}"
                )
        QTimer.singleShot(1800,verify)

'''
s=s[:m.start()]+new+s[m.end():]

p.write_text(s,encoding='utf-8')
print('PATCH_OPENCHAT_DIAG_V2314=OK')
