from pathlib import Path
import sys,re,json
p=Path(sys.argv[1] if len(sys.argv)>1 else r'C:\temp\build\_app\main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v59.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

anchor='    def _ai_build_context(self,mode="observer"):\n'
if anchor not in text:
    raise SystemExit('_ai_build_context anchor missing')
helper=r'''    def _today_quick_panel(self,parent=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QLabel,QHBoxLayout,QPushButton
        import datetime,time
        now=time.time();today=datetime.date.today()
        pending=[r for r in getattr(self,'_reminders',[]) or [] if isinstance(r,dict) and not r.get('done')]
        overdue=[];today_rows=[]
        for r in pending:
            try:due=float(r.get('due_ts') or 0)
            except Exception:due=0
            if due and due<now:overdue.append(r)
            if due:
                try:
                    if datetime.datetime.fromtimestamp(due).date()==today:today_rows.append(r)
                except Exception:pass
        overdue.sort(key=lambda r:float(r.get('due_ts') or 0));today_rows.sort(key=lambda r:float(r.get('due_ts') or 0))
        try:waiting=self._diagnostic_waiting_snapshot() or []
        except Exception:waiting=[]
        candidates=set()
        for w in waiting:
            n=str(w.get('client') or '').strip()
            if n:candidates.add(n)
        for r in pending:
            n=str(r.get('client') or '').strip()
            if n:candidates.add(n)
        priorities=[]
        for n in candidates:
            try:
                pri=self._ai_priority_for_client(n) or {}
                priorities.append((int(pri.get('score') or 0),n,pri))
            except Exception:pass
        priorities.sort(reverse=True,key=lambda x:x[0]);priorities=priorities[:3]
        dlg=QDialog(parent or self);dlg.setWindowTitle('📌 Hoje — painel rápido');dlg.resize(660,650)
        lay=QVBoxLayout(dlg)
        title=QLabel('HOJE NO ALIYVO');title.setStyleSheet('font-size:17px;font-weight:900;color:#07344a;padding:2px 2px 6px 2px;');lay.addWidget(title)
        def add_section(title_txt,items,bg,fg):
            h=QLabel(title_txt);h.setStyleSheet(f'font-size:12px;font-weight:900;color:{fg};margin-top:8px;');lay.addWidget(h)
            if not items:
                x=QLabel('Nenhum item agora.');x.setStyleSheet('color:#6c7780;padding:4px 10px;');lay.addWidget(x);return
            for txt in items:
                x=QLabel(txt);x.setWordWrap(True);x.setStyleSheet(f'background:{bg};color:{fg};border-radius:7px;padding:8px 10px;font-weight:700;');lay.addWidget(x)
        wait_items=[]
        for w in waiting[:8]:
            n=str(w.get('client') or 'Cliente')
            try:sec=float(w.get('business_wait_seconds') or w.get('wait_seconds') or w.get('total_wait_seconds') or 0)
            except Exception:sec=0
            wait_items.append(f'{n}  •  aguardando {int(sec//60)} min úteis')
        add_section(f'💬 CLIENTES ESPERANDO ({len(waiting)})',wait_items,'#e7f3ff','#16558c')
        over_items=[]
        for r in overdue[:6]:
            try:hh=datetime.datetime.fromtimestamp(float(r.get('due_ts') or 0)).strftime('%H:%M')
            except Exception:hh='--:--'
            over_items.append(f"{hh}  •  {str(r.get('text') or '')}"+(f"  — {r.get('client')}" if r.get('client') else ''))
        add_section(f'🔴 VENCIDOS ({len(overdue)})',over_items,'#ffd9de','#9e1027')
        today_items=[]
        for r in today_rows:
            if r in overdue:continue
            try:hh=datetime.datetime.fromtimestamp(float(r.get('due_ts') or 0)).strftime('%H:%M')
            except Exception:hh='--:--'
            today_items.append(f"{hh}  •  {str(r.get('text') or '')}"+(f"  — {r.get('client')}" if r.get('client') else ''))
            if len(today_items)>=8:break
        add_section(f'🟡 TAREFAS DE HOJE ({len(today_rows)})',today_items,'#fff4bf','#715a00')
        pri_items=[]
        for score,n,pri in priorities:
            reasons='; '.join(pri.get('reasons') or []) or 'histórico e pendências atuais'
            pri_items.append(f"{n}  •  prioridade {str(pri.get('level') or '').upper()} ({score})\n{reasons}")
        add_section('⭐ 3 PRIORIDADES SUGERIDAS',pri_items,'#e8f7ee','#176b3a')
        row=QHBoxLayout();crm=QPushButton('🧭 CRM do dia');close=QPushButton('Fechar');row.addWidget(crm);row.addStretch(1);row.addWidget(close);lay.addLayout(row)
        crm.clicked.connect(lambda:self._ai_crm_reminders_dialog(dlg));close.clicked.connect(dlg.accept);dlg.exec()

'''
text=text.replace(anchor,helper+anchor,1)

old='crm=QPushButton("🧭 CRM do dia");top.addWidget(crm);lay.addLayout(top)'
new='today_btn=QPushButton("📌 Hoje");top.addWidget(today_btn);crm=QPushButton("🧭 CRM do dia");top.addWidget(crm);lay.addLayout(top)'
if old not in text:
    raise SystemExit('linha CRM no dialogo de lembretes nao encontrada')
text=text.replace(old,new,1)
old2='try:crm.clicked.connect(lambda:self._ai_crm_reminders_dialog(dlg))\n        except Exception:crm.setEnabled(False)'
new2='today_btn.clicked.connect(lambda:self._today_quick_panel(dlg))\n        try:crm.clicked.connect(lambda:self._ai_crm_reminders_dialog(dlg))\n        except Exception:crm.setEnabled(False)'
if old2 not in text:
    raise SystemExit('conexao CRM no dialogo de lembretes nao encontrada')
text=text.replace(old2,new2,1)

# Seguranca: esta versao nao deve inserir nada novo no __init__.
if '_smart_crm_init' in text or '_smart_crm_timer' in text:
    raise SystemExit('detector automatico inesperado encontrado na base')
p.write_text(text,encoding='utf-8')
print('patched manual today panel only',version)
