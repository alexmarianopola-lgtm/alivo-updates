from pathlib import Path
import sys,re

p=Path(sys.argv[1])/'_app'/'main.py'
s=p.read_text(encoding='utf-8')

if 'ALIYVO_VERSION = "0.23.12"' not in s:
    raise SystemExit('base 0.23.12 nao encontrada')

s=s.replace('ALIYVO_VERSION = "0.23.12"','ALIYVO_VERSION = "0.23.13"',1)
s=s.replace('aliyvo_version="0.23.12"','aliyvo_version="0.23.13"')

# 1) Compatibilidade central: QtWebView2 0.5 usa load_url(), nao setUrl().
anchor='''    def _configure_webview2_core(self,core):
        self._core_webview2=core
'''
if anchor not in s:
    raise SystemExit('anchor WhatsAppView nao encontrado')

shim='''    def setUrl(self,url):
        """Compatibilidade com chamadas antigas no estilo QWebEngineView."""
        try:
            if hasattr(url,"toString"):
                url=url.toString()
        except Exception:
            pass
        url=str(url or "").strip()
        if not url:
            return
        self._current_url=url
        return self.load_url(url)

'''
s=s.replace(anchor,shim+anchor,1)

# 2) Clique do CRM/lembrete usa a API nativa de WebView2 diretamente.
old='''        if phone:
            # Caminho determinístico: o próprio WhatsApp Web abre o chat pelo número.
            url=f"https://web.whatsapp.com/send?phone={phone}"
            try:
                self.web.setUrl(QUrl(url))
                QTimer.singleShot(1800,lambda:self._attendance_scan(force=True))
                return
            except Exception:
                pass
'''
new='''        if phone:
            # Caminho determinístico usando a API NATIVA do QtWebView2 0.5.
            url=f"https://web.whatsapp.com/send?phone={phone}"
            try:
                self._diagnostic_log("open_chat_direct",client=name,phone_tail=phone[-4:],url_mode="webview2_load_url")
            except Exception:
                pass
            try:
                self.web.load_url(url)
                QTimer.singleShot(1800,lambda:self._attendance_scan(force=True))
                return
            except Exception as e:
                try:self._diagnostic_log("open_chat_direct_error",client=name,error=str(e)[:240])
                except Exception:pass
'''
if old not in s:
    raise SystemExit('bloco direct chat nao encontrado')
s=s.replace(old,new,1)

p.write_text(s,encoding='utf-8')
print('PATCH_WEBVIEW2_NAV_V2313=OK')
