from pathlib import Path
import sys,ast

s=(Path(sys.argv[1])/'main.py').read_text(encoding='utf-8')

for x in [
 'ALIYVO_VERSION = "0.23.13"',
 'class WhatsAppView(QtWebView2Widget):',
 'def setUrl(self,url):',
 'return self.load_url(url)',
 'self.web.load_url(url)',
 'open_chat_direct',
 'webview2_load_url',
 'def _attendance_open_chat(self,name):',
 'main.clicked.connect(lambda _=False,r=dict(rem):open_today_reminder(r))',
 'Resolvido — concluir e tirar da lista',
 'Ainda não fiz — manter na lista',
 'def _radar_show_dialog(self):'
]:
    assert x in s,x

# Garante que o caminho direto por telefone nao depende mais de self.web.setUrl.
start=s.index('    def _attendance_open_chat(self,name):')
end=s.index('    def _attendance_open_tool(self,tool):',start)
src=s[start:end]
assert 'self.web.load_url(url)' in src
assert 'self.web.setUrl(QUrl(url))' not in src

print('WEBVIEW2_SETURL_COMPAT=OK')
print('DIRECT_CHAT_USES_LOAD_URL=OK')
print('TODAY_CLICK_PRESERVED=OK')
print('RADAR_PRESERVED=OK')
print('ALIYVO_V2313=OK')
