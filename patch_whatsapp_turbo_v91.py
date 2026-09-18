from pathlib import Path
import sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
text=main.read_text(encoding='utf-8')

def one(old,new,label):
    global text
    n=text.count(old)
    if n!=1:
        raise SystemExit(f'{label}: esperado 1, encontrado {n}')
    text=text.replace(old,new,1)

one('ALIYVO_VERSION = "0.22.90"','ALIYVO_VERSION = "0.22.91"','version')

old_start='''        # 5 s preserva o acompanhamento quase em tempo real e reduz em 40%
        # as consultas ao DOM do WhatsApp executadas durante todo o expediente.
        self._diagnostic_timer=QTimer(self); self._diagnostic_timer.setInterval(5000)
        self._diagnostic_timer.timeout.connect(self._diagnostic_scan); self._diagnostic_timer.start()
        QTimer.singleShot(1200,self._diagnostic_scan)
'''
new_start='''        # WhatsApp Turbo 0.22.91:
        # - o extrator grande fica pronto uma unica vez, em vez de ser reconstruido a cada scan;
        # - a leitura completa do DOM cai de 12 para no maximo 3 vezes por minuto;
        # - antes da leitura pesada fazemos apenas um guard minimo e pulamos o ciclo
        #   quando o usuario esta digitando ou quando a pagina esta oculta.
        self._diagnostic_extract_script=self._attendance_extract_js()
        self._diagnostic_guard_script=r"""(() => {
          try{
            const a=document.activeElement;
            const tag=String((a&&a.tagName)||'').toUpperCase();
            const typing=!!(a && (
              a.isContentEditable ||
              a.getAttribute('contenteditable')==='true' ||
              a.getAttribute('role')==='textbox' ||
              tag==='INPUT' || tag==='TEXTAREA'
            ));
            return {typing:typing,hidden:document.visibilityState==='hidden'};
          }catch(e){return {typing:false,hidden:false};}
        })();"""
        self._diagnostic_timer=QTimer(self); self._diagnostic_timer.setInterval(20000)
        self._diagnostic_timer.timeout.connect(self._diagnostic_scan); self._diagnostic_timer.start()
        # Evita disputar CPU/DOM com a montagem inicial do WhatsApp.
        QTimer.singleShot(4000,self._diagnostic_scan)
'''
one(old_start,new_start,'diagnostic turbo start')

old_scan='''    def _diagnostic_scan(self):
        if getattr(self,"_diagnostic_busy",False): return
        try:
            self._diagnostic_busy=True
            self.web.page().runJavaScript(self._attendance_extract_js(),self._diagnostic_scan_done)
        except Exception:
            self._diagnostic_busy=False

'''
new_scan='''    def _diagnostic_scan(self):
        if getattr(self,"_diagnostic_busy",False): return
        try:
            self._diagnostic_busy=True
            guard=getattr(self,"_diagnostic_guard_script","")
            if guard:
                self.web.page().runJavaScript(guard,self._diagnostic_scan_guard_done)
            else:
                self._diagnostic_scan_guard_done({})
        except Exception:
            self._diagnostic_busy=False

    def _diagnostic_scan_guard_done(self,result):
        try:
            # Prioridade absoluta para uso humano do WhatsApp.
            # Se o cursor esta no editor de mensagem, nao percorremos conversa/lista.
            if isinstance(result,dict) and (bool(result.get("typing")) or bool(result.get("hidden"))):
                self._diagnostic_busy=False
                return
            script=getattr(self,"_diagnostic_extract_script","") or self._attendance_extract_js()
            self.web.page().runJavaScript(script,self._diagnostic_scan_done)
        except Exception:
            self._diagnostic_busy=False

'''
one(old_scan,new_scan,'diagnostic turbo scan')

# O diagnostico WebEngine da 0.22.90 e preservado, mas passa a registrar a versao atual.
text=text.replace('aliyvo_version="0.22.90"', 'aliyvo_version="0.22.91"')

main.write_text(text,encoding='utf-8')
print('PATCH_WHATSAPP_TURBO_V91=OK')
