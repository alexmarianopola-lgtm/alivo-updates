from pathlib import Path
import sys

p=Path(sys.argv[1])/'_app'/'main.py'
s=p.read_text(encoding='utf-8')
if 'ALIYVO_VERSION = "0.23.08"' not in s:
    raise SystemExit('base 0.23.08 nao encontrada')
s=s.replace('ALIYVO_VERSION = "0.23.08"','ALIYVO_VERSION = "0.23.09"',1)
s=s.replace('aliyvo_version="0.23.08"','aliyvo_version="0.23.09"')

anchor="        over_items=[]\n"
insert="""        def finish_today_reminder(rid):
            rid=str(rid or '')
            for rr in self._reminders:
                if isinstance(rr,dict) and str(rr.get('id') or '')==rid:
                    rr['done']=True;rr['alerted']=True
                    try:self._diagnostic_log('reminder_done',client=rr.get('client',''),text=rr.get('text',''))
                    except Exception:pass
                    break
            self._reminder_save();self._reminder_update_button()
            dlg.accept();QTimer.singleShot(120,lambda:self._today_quick_panel(self))

        def open_today_reminder(rem):
            client=str(rem.get('client') or '').strip()
            if not client:return
            dlg.accept();QTimer.singleShot(150,lambda c=client:self._attendance_open_chat(c))

        def add_today_card(rem,bg,fg):
            from PyQt6.QtWidgets import QWidget,QHBoxLayout,QPushButton
            try:hh=datetime.datetime.fromtimestamp(float(rem.get('due_ts') or 0)).strftime('%H:%M')
            except Exception:hh='--:--'
            client=str(rem.get('client') or '').strip()
            txt=str(rem.get('text') or '').strip()
            rid=str(rem.get('id') or '')
            box=QWidget();box.setStyleSheet(f'QWidget{{background:{bg};border-radius:7px;}}')
            row=QHBoxLayout(box);row.setContentsMargins(7,5,7,5);row.setSpacing(5)
            main=QPushButton(f"{hh}  •  {txt}"+(f"  — {client}" if client else ''))
            main.setToolTip('Abrir conversa do cliente para resolver este lembrete')
            main.setStyleSheet(f'QPushButton{{text-align:left;background:transparent;color:{fg};border:none;padding:6px;font-weight:800;}}')
            main.clicked.connect(lambda _=False,r=dict(rem):open_today_reminder(r))
            yes=QPushButton('👍');yes.setFixedWidth(40);yes.setToolTip('Resolvido — concluir e tirar da lista')
            no=QPushButton('👎');no.setFixedWidth(40);no.setToolTip('Ainda não fiz — manter na lista')
            yes.clicked.connect(lambda _=False,x=rid:finish_today_reminder(x))
            no.clicked.connect(lambda _=False:None)
            row.addWidget(main,1);row.addWidget(yes);row.addWidget(no);lay.addWidget(box)

"""
if anchor not in s: raise SystemExit('anchor vencidos nao encontrado')
s=s.replace(anchor,insert+anchor,1)

old="""        over_items=[]
        for r in overdue[:6]:
            try:hh=datetime.datetime.fromtimestamp(float(r.get('due_ts') or 0)).strftime('%H:%M')
            except Exception:hh='--:--'
            over_items.append(f"{hh}  •  {str(r.get('text') or '')}"+(f"  — {r.get('client')}" if r.get('client') else ''))
        add_section(f'🔴 VENCIDOS ({len(overdue)})',over_items,'#ffd9de','#9e1027')
"""
new="""        over_head=QLabel(f'🔴 VENCIDOS ({len(overdue)})');over_head.setStyleSheet('font-size:12px;font-weight:900;color:#9e1027;margin-top:8px;');lay.addWidget(over_head)
        if overdue:
            for r in overdue[:6]:add_today_card(r,'#ffd9de','#9e1027')
        else:
            x=QLabel('Nenhum item agora.');x.setStyleSheet('color:#6c7780;padding:4px 10px;');lay.addWidget(x)
"""
s=s.replace(old,new,1)

old2="""        today_items=[]
        for r in today_rows:
            if r in overdue:continue
            try:hh=datetime.datetime.fromtimestamp(float(r.get('due_ts') or 0)).strftime('%H:%M')
            except Exception:hh='--:--'
            today_items.append(f"{hh}  •  {str(r.get('text') or '')}"+(f"  — {r.get('client')}" if r.get('client') else ''))
            if len(today_items)>=8:break
        add_section(f'🟡 TAREFAS DE HOJE ({len(today_rows)})',today_items,'#fff4bf','#715a00')
"""
new2="""        open_today=[r for r in today_rows if r not in overdue]
        today_head=QLabel(f'🟡 TAREFAS DE HOJE ({len(open_today)})');today_head.setStyleSheet('font-size:12px;font-weight:900;color:#715a00;margin-top:8px;');lay.addWidget(today_head)
        if open_today:
            for r in open_today[:8]:add_today_card(r,'#fff4bf','#715a00')
        else:
            x=QLabel('Nenhum item agora.');x.setStyleSheet('color:#6c7780;padding:4px 10px;');lay.addWidget(x)
"""
s=s.replace(old2,new2,1)

p.write_text(s,encoding='utf-8')
print('PATCH_TODAY_V2309=OK')
