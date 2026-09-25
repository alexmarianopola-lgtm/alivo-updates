from pathlib import Path
import sys

p=Path(sys.argv[1])/'_app'/'main.py'
s=p.read_text(encoding='utf-8')
if 'ALIYVO_VERSION = "0.23.09"' not in s:
    raise SystemExit('base 0.23.09 nao encontrada')
s=s.replace('ALIYVO_VERSION = "0.23.09"','ALIYVO_VERSION = "0.23.10"',1)
s=s.replace('aliyvo_version="0.23.09"','aliyvo_version="0.23.10"')

old="""        def open_today_reminder(rem):
            client=str(rem.get('client') or '').strip()
            if not client:return
            dlg.accept();QTimer.singleShot(150,lambda c=client:self._attendance_open_chat(c))
"""
new="""        def open_today_reminder(rem):
            import re
            client=str(rem.get('client') or '').strip()
            txt=str(rem.get('text') or '').strip()
            # Compatibilidade com lembretes antigos: alguns guardaram o contato
            # no próprio texto depois de um travessão, sem preencher client.
            if not client and txt:
                m=re.search(r'\\s+[—-]\\s+(.+?)\\s*$',txt)
                if m:client=str(m.group(1) or '').strip()
            if not client:return
            dlg.accept()
            QTimer.singleShot(180,lambda c=client:self._attendance_open_chat(c))
"""
if old not in s: raise SystemExit('open_today_reminder nao encontrado')
s=s.replace(old,new,1)

old2="""            main=QPushButton(f"{hh}  •  {txt}"+(f"  — {client}" if client else ''))
            main.setToolTip('Abrir conversa do cliente para resolver este lembrete')
            main.setStyleSheet(f'QPushButton{{text-align:left;background:transparent;color:{fg};border:none;padding:6px;font-weight:800;}}')
"""
new2="""            main=QPushButton(f"{hh}  •  {txt}"+(f"  — {client}" if client else ''))
            main.setCursor(Qt.CursorShape.PointingHandCursor)
            main.setToolTip('Clique para abrir a conversa deste cliente no WhatsApp')
            main.setMinimumHeight(38)
            main.setStyleSheet(f'QPushButton{{text-align:left;background:transparent;color:{fg};border:none;padding:8px;font-weight:800;}}QPushButton:hover{{background:rgba(255,255,255,90);border-radius:6px;text-decoration:underline;}}')
"""
if old2 not in s: raise SystemExit('botao do card nao encontrado')
s=s.replace(old2,new2,1)

p.write_text(s,encoding='utf-8')
print('PATCH_TODAY_CLICK_V2310=OK')
