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

one('ALIYVO_VERSION = "0.22.92"','ALIYVO_VERSION = "0.22.93"','version')

old='''        dlg=QDialog(self); dlg.setWindowTitle("⏰ Lembretes do ALIYVO — CRM visual"); dlg.resize(780,580); lay=QVBoxLayout(dlg)
        top=QHBoxLayout();top.addWidget(QLabel("Mostrar:"));filt=QComboBox();filt.addItems(["A fazer","Concluídos","Todos","Vencidos"]);filt.setCurrentText("A fazer");top.addWidget(filt)
        counts=QLabel("");counts.setStyleSheet("font-weight:800;");top.addWidget(counts);top.addStretch(1)
        today_btn=QPushButton("📌 Hoje");top.addWidget(today_btn);crm=QPushButton("🧭 CRM do dia");top.addWidget(crm);lay.addLayout(top)
        legend=QLabel("🔴 vencido   🟠 até 1h   🟡 hoje   🔵 futuro   🟢 concluído")
        legend.setStyleSheet("font-weight:700;color:#59636d;padding:2px 4px;");lay.addWidget(legend)
        lst=QListWidget();lst.setSpacing(5);lst.setStyleSheet("QListWidget{border:1px solid #d7dee5;background:#fff;} QListWidget::item{border:none;} QListWidget::item:selected{border:2px solid #1f6feb;border-radius:7px;}");lay.addWidget(lst,1)
'''
new='''        dlg=QDialog(self); dlg.setWindowTitle("📊 ALIYVO CRM — Lembretes e Oportunidades"); dlg.resize(940,690); lay=QVBoxLayout(dlg)

        # Cabeçalho visual do CRM
        crm_title=QLabel("ALIYVO CRM")
        crm_title.setStyleSheet("font-size:22px;font-weight:900;color:#0B3349;padding:2px 2px 0 2px;")
        crm_sub=QLabel("Lembretes, clientes esperando e oportunidades em um só lugar")
        crm_sub.setStyleSheet("font-size:11px;font-weight:600;color:#657784;padding:0 2px 8px 2px;")
        lay.addWidget(crm_title);lay.addWidget(crm_sub)

        cards=QHBoxLayout();cards.setSpacing(8)
        card_over=QLabel();card_today=QLabel();card_wait=QLabel();card_ai=QLabel()
        for c in (card_over,card_today,card_wait,card_ai):
            c.setMinimumHeight(72);c.setWordWrap(True);c.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cards.addWidget(c,1)
        lay.addLayout(cards)

        top=QHBoxLayout();top.addWidget(QLabel("Mostrar:"));filt=QComboBox();filt.addItems(["A fazer","Concluídos","Todos","Vencidos"]);filt.setCurrentText("A fazer");top.addWidget(filt)
        counts=QLabel("");counts.setStyleSheet("font-weight:800;color:#44515b;");top.addWidget(counts);top.addStretch(1)
        today_btn=QPushButton("📌 Hoje");top.addWidget(today_btn);crm=QPushButton("🤖 Pendências da IA");top.addWidget(crm);lay.addLayout(top)

        legend=QLabel("🔴 vencido   🟠 até 1h   🟡 hoje   🔵 futuro   🟢 concluído   •   status CRM aparece no cartão")
        legend.setStyleSheet("font-weight:700;color:#59636d;padding:2px 4px;");lay.addWidget(legend)
        lst=QListWidget();lst.setSpacing(7);lst.setStyleSheet("QListWidget{border:1px solid #d7dee5;background:#F7FAFC;padding:4px;} QListWidget::item{border:none;} QListWidget::item:selected{border:2px solid #1f6feb;border-radius:9px;}");lay.addWidget(lst,1)
'''
one(old,new,'reminder visual shell')

old='''        def make_card(r,now):
            due_ts=float(r.get('due_ts') or 0);due=datetime.datetime.fromtimestamp(due_ts).strftime('%d/%m/%Y %H:%M') if due_ts else 'Sem data';client=str(r.get('client') or '').strip();rank,label,icon,bg,fg=urgency(r,now);title=str(r.get('text') or '').strip()
            card=QWidget();card.setStyleSheet(f"QWidget{{background:{bg};border-radius:7px;}}")
            vl=QVBoxLayout(card);vl.setContentsMargins(11,7,11,7);vl.setSpacing(2)
            top_line=QHBoxLayout();top_line.setContentsMargins(0,0,0,0);top_line.setSpacing(8)
            badge=QLabel(f"{icon} {label}");badge.setStyleSheet(f"font-size:10px;font-weight:900;color:{fg};background:transparent;")
            title_lab=QLabel(title);title_lab.setWordWrap(True);title_lab.setStyleSheet(f"font-size:14px;font-weight:900;color:{fg};background:transparent;")
            top_line.addWidget(badge,0);top_line.addWidget(title_lab,1);vl.addLayout(top_line)
            meta=(f"{due}" + (f"   •   {client}" if client else ""))
            meta_lab=QLabel(meta);meta_lab.setStyleSheet(f"font-size:10px;font-weight:600;color:{fg};background:transparent;opacity:0.8;");vl.addWidget(meta_lab)
            return card
'''
new='''        def make_card(r,now):
            due_ts=float(r.get('due_ts') or 0);due=datetime.datetime.fromtimestamp(due_ts).strftime('%d/%m/%Y %H:%M') if due_ts else 'Sem data';client=str(r.get('client') or '').strip();rank,label,icon,bg,fg=urgency(r,now);title=str(r.get('text') or '').strip()
            card=QWidget();card.setStyleSheet(f"QWidget{{background:{bg};border-radius:9px;}}")
            vl=QVBoxLayout(card);vl.setContentsMargins(12,8,12,8);vl.setSpacing(3)
            top_line=QHBoxLayout();top_line.setContentsMargins(0,0,0,0);top_line.setSpacing(8)
            badge=QLabel(f"{icon} {label}");badge.setStyleSheet(f"font-size:10px;font-weight:900;color:{fg};background:transparent;")
            title_lab=QLabel(title);title_lab.setWordWrap(True);title_lab.setStyleSheet(f"font-size:14px;font-weight:900;color:{fg};background:transparent;")
            top_line.addWidget(badge,0);top_line.addWidget(title_lab,1);vl.addLayout(top_line)
            meta=(f"{due}" + (f"   •   {client}" if client else ""))
            meta_lab=QLabel(meta);meta_lab.setStyleSheet(f"font-size:10px;font-weight:600;color:{fg};background:transparent;");vl.addWidget(meta_lab)
            if client:
                try:state=self._crm_state_for_client(client) or {}
                except Exception:state={}
                if state:
                    owner=str(state.get('owner') or '-')
                    st=str(state.get('status') or 'Sem classificação')
                    action=str(state.get('next_action') or '')
                    crm_lab=QLabel(f"CRM: {st}   •   responsável: {owner}" + (f"\\nPróxima ação: {action}" if action else ""))
                    crm_lab.setWordWrap(True)
                    crm_lab.setStyleSheet("font-size:10px;font-weight:800;color:#173B52;background:rgba(255,255,255,0.55);border-radius:6px;padding:5px 7px;")
                    vl.addWidget(crm_lab)
            return card
'''
one(old,new,'reminder card crm status')

old='''        def refresh():
            lst.clear();now=time.time();allrows=[x for x in self._reminders if isinstance(x,dict)];pending=[x for x in allrows if not x.get('done')];done_rows=[x for x in allrows if x.get('done')];overdue=[x for x in pending if float(x.get('due_ts') or 0)<now]
            counts.setText(f"A fazer: {len(pending)}   •   Concluídos: {len(done_rows)}   •   Vencidos: {len(overdue)}")
'''
new='''        def refresh():
            lst.clear();now=time.time();allrows=[x for x in self._reminders if isinstance(x,dict)];pending=[x for x in allrows if not x.get('done')];done_rows=[x for x in allrows if x.get('done')];overdue=[x for x in pending if float(x.get('due_ts') or 0)<now]
            today_count=0
            for _r in pending:
                try:
                    _d=float(_r.get('due_ts') or 0)
                    if _d and datetime.datetime.fromtimestamp(_d).date()==datetime.datetime.now().date():today_count+=1
                except Exception:pass
            try:waiting_count=len(self._diagnostic_waiting_snapshot() or [])
            except Exception:waiting_count=0
            try:ai_pending=len(self._crm_states_payload(100,True) or [])
            except Exception:ai_pending=0
            card_over.setText(f"🔴\\n{len(overdue)}\\nVENCIDOS")
            card_over.setStyleSheet("background:#FFD9DE;color:#9E1027;border-radius:10px;font-size:13px;font-weight:900;padding:7px;")
            card_today.setText(f"🟡\\n{today_count}\\nHOJE")
            card_today.setStyleSheet("background:#FFF2B7;color:#6A5600;border-radius:10px;font-size:13px;font-weight:900;padding:7px;")
            card_wait.setText(f"💬\\n{waiting_count}\\nESPERANDO")
            card_wait.setStyleSheet("background:#DDEEFF;color:#155B8A;border-radius:10px;font-size:13px;font-weight:900;padding:7px;")
            card_ai.setText(f"🤖\\n{ai_pending}\\nPENDÊNCIAS IA")
            card_ai.setStyleSheet("background:#DFF5E8;color:#176B3A;border-radius:10px;font-size:13px;font-weight:900;padding:7px;")
            counts.setText(f"A fazer: {len(pending)}   •   Concluídos: {len(done_rows)}")
'''
one(old,new,'reminder dashboard refresh')

text=text.replace('aliyvo_version="0.22.92"','aliyvo_version="0.22.93"')
main.write_text(text,encoding='utf-8')
print('PATCH_CRM_VISUAL_V93=OK')
