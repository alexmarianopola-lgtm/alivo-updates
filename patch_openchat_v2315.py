from pathlib import Path
import sys,re

p=Path(sys.argv[1])/"_app"/"main.py"
s=p.read_text(encoding="utf-8")
if 'ALIYVO_VERSION = "0.23.14"' not in s:
    raise SystemExit("base 0.23.14 nao encontrada")
s=s.replace('ALIYVO_VERSION = "0.23.14"','ALIYVO_VERSION = "0.23.15"',1)
s=s.replace('aliyvo_version="0.23.14"','aliyvo_version="0.23.15"')

old="""            if not client:return
            dlg.accept()
            QTimer.singleShot(180,lambda c=client:self._attendance_open_chat(c))
"""
new="""            if not client:return
            self._attendance_open_chat(client)
            QTimer.singleShot(300,dlg.accept)
"""
if old not in s:
    raise SystemExit("fluxo Hoje nao encontrado")
s=s.replace(old,new,1)

anchor='    def _attendance_open_tool(self,tool):\n'
idx=s.index(anchor)
helper='''    def _attendance_open_chat_name_result(self,name):
        import json
        name=str(name or "").strip()
        if not name:return
        js=r"""
        (() => {
          const wanted=__NAME__;
          const norm=s=>String(s||'').replace(/\\s+/g,' ').trim().toLowerCase();
          const want=norm(wanted);
          const pane=document.querySelector('#pane-side')||document;
          const els=[...pane.querySelectorAll('span[title],[role="gridcell"] span,[dir="auto"]')];
          let partial=null;
          for(const el of els){
            const got=norm(el.getAttribute('title')||el.textContent||'');
            if(!got)continue;
            if(got===want){
              const row=el.closest('[role="listitem"],[role="row"],[data-testid="cell-frame-container"]')||el.closest('div');
              if(row){row.click();return {ok:true,mode:'exact'};}
            }
            if(!partial && (got.includes(want)||want.includes(got)))partial=el;
          }
          if(partial){
            const row=partial.closest('[role="listitem"],[role="row"],[data-testid="cell-frame-container"]')||partial.closest('div');
            if(row){row.click();return {ok:true,mode:'partial'};}
          }
          return {ok:false,reason:'result_not_found'};
        })();
        """.replace('__NAME__',json.dumps(name,ensure_ascii=False))
        def done(result):
            try:self._diagnostic_log("open_chat_name_stage2",client=name,result=result)
            except Exception:pass
            if isinstance(result,dict) and result.get("ok"):
                try:self._attendance_scan(force=True)
                except Exception:pass
            else:
                QMessageBox.information(self,"Abrir conversa",f"A busca por '{name}' foi feita, mas não encontrei um resultado para clicar.")
        self.web.page().runJavaScript(js,done)

'''
s=s[:idx]+helper+s[idx:]

# Ajusta o callback do caminho por nome da 0.23.14 para clicar no resultado depois.
needle="""                if isinstance(result,dict) and result.get("ok"):
                    QTimer.singleShot(700,lambda:self._attendance_scan(force=True))
"""
replacement="""                if isinstance(result,dict) and result.get("ok"):
                    if result.get("mode")=="search_filled":
                        QTimer.singleShot(850,lambda n=name:self._attendance_open_chat_name_result(n))
                    else:
                        QTimer.singleShot(500,lambda:self._attendance_scan(force=True))
"""
if needle not in s:
    raise SystemExit("callback nome nao encontrado")
s=s.replace(needle,replacement,1)

p.write_text(s,encoding="utf-8")
print("PATCH_OPENCHAT_V2315=OK")
