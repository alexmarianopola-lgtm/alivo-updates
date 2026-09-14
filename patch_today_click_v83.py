from pathlib import Path
import re,sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
s=main.read_text(encoding='utf-8')

# Versao
s2,n=re.subn(r'ALIYVO_VERSION\s*=\s*["\']0\.22\.82["\']','ALIYVO_VERSION = "0.22.83"',s,count=1)
if n!=1:
    raise SystemExit(f'Nao encontrei versao 0.22.82 exatamente uma vez: {n}')
s=s2

old="""        wait_items=[]
        for w in waiting[:8]:
            n=str(w.get('client') or 'Cliente')
            try:sec=max(0,float(w.get('waiting_seconds') or w.get('work_waiting_seconds') or 0))
            except Exception:sec=0
            if sec < 60: wait_txt='aguardando agora'
            elif sec < 3600: wait_txt=f'aguardando {int(sec//60)} min úteis'
            else:
                hh=int(sec//3600);mm=int((sec%3600)//60)
                wait_txt=f'aguardando {hh}h{mm:02d} úteis' if mm else f'aguardando {hh}h úteis'
            wait_items.append(f'{n}  •  {wait_txt}')
        add_section(f'💬 CLIENTES ESPERANDO ({len(waiting)})',wait_items,'#e7f3ff','#16558c')
"""

new="""        # Clientes esperando: cartões clicáveis para conferir a conversa no WhatsApp.
        wait_head=QLabel(f'💬 CLIENTES ESPERANDO ({len(waiting)})')
        wait_head.setStyleSheet('font-size:12px;font-weight:900;color:#16558c;margin-top:8px;')
        lay.addWidget(wait_head)
        wait_hint=QLabel('Clique em um cliente para abrir a conversa e conferir se ainda precisa de resposta.')
        wait_hint.setStyleSheet('color:#64748b;font-size:11px;padding:0 2px 3px 2px;')
        wait_hint.setWordWrap(True)
        lay.addWidget(wait_hint)
        if not waiting:
            x=QLabel('Nenhum item agora.');x.setStyleSheet('color:#6c7780;padding:4px 10px;');lay.addWidget(x)
        else:
            for w in waiting[:8]:
                n=str(w.get('client') or 'Cliente')
                try:sec=max(0,float(w.get('waiting_seconds') or w.get('work_waiting_seconds') or 0))
                except Exception:sec=0
                if sec < 60: wait_txt='aguardando agora'
                elif sec < 3600: wait_txt=f'aguardando {int(sec//60)} min úteis'
                else:
                    hh=int(sec//3600);mm=int((sec%3600)//60)
                    wait_txt=f'aguardando {hh}h{mm:02d} úteis' if mm else f'aguardando {hh}h úteis'
                btn=QPushButton(f'{n}  •  {wait_txt}')
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setToolTip(f'Abrir conversa de {n} no WhatsApp')
                btn.setStyleSheet(
                    'QPushButton{text-align:left;background:#e7f3ff;color:#16558c;'
                    'border:1px solid #d0e7fa;border-radius:7px;padding:8px 10px;font-weight:700;}'
                    'QPushButton:hover{background:#d8ecff;border:1px solid #16558c;}'
                    'QPushButton:pressed{background:#cbe4fb;}'
                )
                def open_waiting(_checked=False,client=n):
                    dlg.accept()
                    QTimer.singleShot(150,lambda client=client:self._attendance_open_chat(client))
                btn.clicked.connect(open_waiting)
                lay.addWidget(btn)
"""

if old not in s:
    raise SystemExit('Bloco de clientes esperando nao encontrado na 0.22.82')
s=s.replace(old,new,1)
main.write_text(s,encoding='utf-8')
print('patched today clickable clients 0.22.83')
