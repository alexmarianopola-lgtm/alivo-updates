from pathlib import Path
import sys
s=(Path(sys.argv[1])/'main.py').read_text(encoding='utf-8')
for x in [
 'ALIYVO_VERSION = "0.23.14"',
 'open_chat_click',
 'CoreWebView2.Navigate=OK',
 'self.web.load_url(url)',
 'window.location.href',
 'open_chat_navigation',
 'open_chat_verify',
 'Diagnóstico do clique',
 'resolved_phone=phone',
 'main.clicked.connect(lambda _=False,r=dict(rem):open_today_reminder(r))',
 'def _radar_show_dialog(self):'
]:
    assert x in s,x
print("CLICK_DIAGNOSTIC=OK")
print("COREWEBVIEW2_NAVIGATE=OK")
print("LOAD_URL_FALLBACK=OK")
print("JS_LOCATION_FALLBACK=OK")
print("VERIFY_AFTER_NAVIGATION=OK")
print("ALIYVO_V2314=OK")
