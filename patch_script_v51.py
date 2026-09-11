from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v51.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

def replace_method(src,class_name,method_name,new_code):
    tree=ast.parse(src)
    cls=next((n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==class_name),None)
    if cls is None: raise SystemExit(f'class {class_name} not found')
    target=next((n for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==method_name),None)
    if target is None: raise SystemExit(f'method {class_name}.{method_name} not found')
    lines=src.splitlines(keepends=True)
    start=sum(len(x) for x in lines[:target.lineno-1]); end=sum(len(x) for x in lines[:target.end_lineno])
    if not new_code.endswith('\n'):new_code+='\n'
    return src[:start]+new_code+src[end:]

anchor='    def _ai_build_context(self,mode="observer"):\n'
if anchor not in text: raise SystemExit('_ai_build_context anchor missing')
helpers=r'''    def _crm_open_reminders_payload(self,client_name=""):
        import time,datetime
        name=str(client_name or "").strip(); now=time.time(); out=[]
        for r in getattr(self,"_reminders",[]) or []:
            if not isinstance(r,dict) or r.get("done"):continue
            client=str(r.get("client") or "").strip()
            if name and client!=name:continue
            try:due=float(r.get("due_ts") or 0)
            except Exception:due=0
            out.append({"id":str(r.get("id") or ""),"text":str(r.get("text") or "")[:180],"client":client,"due_ts":due,"due":datetime.datetime.fromtimestamp(due).strftime("%d/%m %H:%M") if due else "sem data","overdue":bool(due and due<now),"context":str(r.get("context") or "")[-350:]})
        out.sort(key=lambda x:(not x["overdue"],x["due_ts"] or 9e18))
        return out[:30]

    def _ai_priority_for_client(self,client_name):
        import time
        name=str(client_name or "").strip()
        if not name:return {"level":"baixa","score":0,"reasons":[]}
        p=self._ai_client_profile_payload(name) or {}
        reasons=[];score=0
        # Espera atual pesa mais que historico.
        try:
            for w in self._diagnostic_waiting_snapshot() or []:
                if str(w.get("client") or "").strip()!=name:continue
                sec=float(w.get("wait_seconds") or w.get("business_wait_seconds") or w.get("total_wait_seconds") or 0)
                if sec>=900:score+=45;reasons.append("aguardando há mais de 15 min úteis")
                elif sec>=300:score+=30;reasons.append("aguardando há mais de 5 min úteis")
                elif sec>0:score+=15;reasons.append("aguardando resposta agora")
        except Exception:pass
        rem=self._crm_open_reminders_payload(name)
        if any(x.get("overdue") for x in rem):score+=35;reasons.append("tem lembrete vencido")
        elif rem:score+=15;reasons.append("tem lembrete pendente")
        pats={x.get("key"):int(x.get("count") or 0) for x in (p.get("patterns") or [])}
        if pats.get("consulta_preco",0)>=3:score+=8;reasons.append("cliente recorrente em preço/orçamento")
        if pats.get("pre_venda",0)>=2:score+=8;reasons.append("pré-venda/reserva aparece com frequência")
        if any(x.get("key")=="sinal_fechamento" for x in (p.get("outcomes") or [])):score+=10;reasons.append("há sinais observados de pedido/fechamento")
        if int(p.get("interaction_cases") or 0)>=10:score+=6;reasons.append("cliente com histórico frequente")
        level="alta" if score>=45 else ("média" if score>=22 else "baixa")
        return {"level":level,"score":score,"reasons":reasons[:4]}

    def _ai_current_assist_text(self,client_name=""):
        name=str(client_name or getattr(self,"_diagnostic_active_name","") or "").strip()
        if not name:return "Abra uma conversa individual no WhatsApp para ver a assistência rápida."
        p=self._ai_client_profile_payload(name) or {};pri=self._ai_priority_for_client(name);pats={x.get("key"):int(x.get("count") or 0) for x in (p.get("patterns") or [])}
        lines=[f"ASSISTÊNCIA RÁPIDA — {name}",f"Prioridade agora: {pri['level'].upper()} • índice {pri['score']}"]
        if pri.get("reasons"):
            lines.append("Motivos: "+"; ".join(pri["reasons"]))
        lines += ["", "O QUE O HISTÓRICO SUGERE"]
        tips=[]
        if pats.get("consulta_preco",0)>=2 and pats.get("prazo_pagamento",0)>=2:tips.append("Preço e prazo aparecem juntos com frequência; quando couber, responda os dois de uma vez.")
        elif pats.get("consulta_preco",0)>=2:tips.append("Preço/orçamento é recorrente neste cliente.")
        if pats.get("codigo_aplicacao",0)>=2:tips.append("Código/original/aplicação aparece bastante; deixe essa busca pronta.")
        if pats.get("negociacao",0)>=2:tips.append("Negociação aparece com frequência; vale conferir seu limite antes de responder.")
        if pats.get("pre_venda",0)>=2:tips.append("Pré-venda/reserva é recorrente; confirme disponibilidade junto da resposta.")
        if int(p.get("audio") or 0)>=3:tips.append("Esse cliente usa bastante áudio.")
        if not tips:tips.append("Ainda não há padrão forte; observe a conversa atual antes de antecipar uma ação.")
        for x in tips[:4]:lines.append("• "+x)
        rem=self._crm_open_reminders_payload(name)
        lines += ["", "LEMBRETES DESTE CLIENTE"]
        if rem:
            for x in rem[:5]:lines.append(("⚠ " if x.get("overdue") else "• ")+f"{x.get('due')} — {x.get('text')}")
        else:lines.append("• Nenhum lembrete pendente vinculado.")
        lines += ["", "Essas dicas são regras locais baseadas no diagnóstico; não enviam mensagens nem alteram lembretes."]
        return "\n".join(lines)

    def _ai_current_assist_dialog(self,parent=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QPlainTextEdit,QPushButton,QHBoxLayout
        dlg=QDialog(parent or self);dlg.setWindowTitle("💡 Assistência rápida do cliente");dlg.resize(720,560)
        lay=QVBoxLayout(dlg);txt=QPlainTextEdit();txt.setReadOnly(True);txt.setPlainText(self._ai_current_assist_text());lay.addWidget(txt,1)
        row=QHBoxLayout();deep=QPushButton("🤖 Estratégia IA completa");refresh=QPushButton("↻ Atualizar");close=QPushButton("Fechar");row.addWidget(deep);row.addWidget(refresh);row.addStretch(1);row.addWidget(close);lay.addLayout(row)
        def do_ai():
            name=str(getattr(self,"_diagnostic_active_name","") or "").strip()
            if not name:return
            self._ai_profile_target=name;self._ai_observer_text_widget=txt;self._ai_observer_status_widget=None;self._ai_observer_analyze("client_profile",False)
        deep.clicked.connect(do_ai);refresh.clicked.connect(lambda:txt.setPlainText(self._ai_current_assist_text()));close.clicked.connect(dlg.accept);dlg.finished.connect(lambda _=0:self._ai_observer_dialog_closed(txt,None));dlg.exec()

    def _ai_crm_reminders_dialog(self,parent=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QPlainTextEdit,QPushButton,QHBoxLayout,QLabel
        dlg=QDialog(parent or self);dlg.setWindowTitle("🧭 CRM do dia — IA + Lembretes");dlg.resize(820,620)
        lay=QVBoxLayout(dlg);status=QLabel("A IA usa lembretes abertos + perfis locais + atendimento recente. Ela não altera nada sozinha.");lay.addWidget(status)
        txt=QPlainTextEdit();txt.setReadOnly(True);rem=self._crm_open_reminders_payload();lines=["LEMBRETES ABERTOS"]
        if rem:
            for r in rem[:20]:lines.append(("⚠ " if r.get("overdue") else "• ")+f"{r.get('due')} • {r.get('client') or 'sem cliente'} — {r.get('text')}")
        else:lines.append("• Nenhum lembrete aberto.")
        txt.setPlainText("\n".join(lines));lay.addWidget(txt,1)
        row=QHBoxLayout();an=QPushButton("🤖 Analisar meu CRM agora");close=QPushButton("Fechar");row.addWidget(an);row.addStretch(1);row.addWidget(close);lay.addLayout(row)
        def run():
            self._ai_observer_text_widget=txt;self._ai_observer_status_widget=status;self._ai_observer_analyze("crm_reminders",False)
        an.clicked.connect(run);close.clicked.connect(dlg.accept);dlg.finished.connect(lambda _=0:self._ai_observer_dialog_closed(txt,status));dlg.exec()

'''
text=text.replace(anchor,helpers+anchor,1)

text=replace_method(text,'MainWindow','_ai_build_context',r'''    def _ai_build_context(self,mode="observer"):
        import datetime,time
        today=datetime.date.today().isoformat();groups=set(self._diagnostic_groups_load());rows=[]
        for x in self._diagnostic_read():
            if not isinstance(x,dict):continue
            if not str(x.get("time") or "").startswith(today):continue
            if str(x.get("client") or "").strip() in groups:continue
            rows.append(x)
        active=str(getattr(self,"_diagnostic_active_name","") or "").strip()
        target=str(getattr(self,"_ai_profile_target","") or "").strip() if mode=="client_profile" else active
        last_ai=float(getattr(self,"_ai_last_analyzed_event_ts",0) or 0)
        if mode in ("conversation","client_profile") and target:
            selected=[x for x in rows if str(x.get("client") or "").strip()==target][-90:]
        elif mode=="auto":
            selected=[]
            for x in rows:
                try:ts=float(x.get("ts") or 0)
                except Exception:ts=0
                if ts>last_ai:selected.append(x)
            selected=selected[-90:]
        else:selected=rows[-140:]
        events=[self._ai_compact_event(x) for x in selected];events=[x for x in events if x]
        last_event_ts=max([float(x.get("ts") or 0) for x in rows] or [0])
        try:overview=self._diagnostic_whatsapp_overview_payload()
        except Exception:overview={}
        try:waiting=self._diagnostic_waiting_snapshot()[:25]
        except Exception:waiting=[]
        try:current_context=str((getattr(self,"_diagnostic_last_context_by_contact",{}) or {}).get(target) or "")[-1800:]
        except Exception:current_context=""
        learning=self._ai_learning_summary_payload(True)
        profile=self._ai_client_profile_payload(target) if target else {}
        reminders=self._crm_open_reminders_payload(target if mode in ("conversation","client_profile") else "")
        priority=self._ai_priority_for_client(target) if target else {}
        return {"generated_at":datetime.datetime.now().isoformat(timespec="seconds"),"mode":mode,"delta_only":bool(mode=="auto"),"active_contact":target,"active_recent_context":current_context,"client_profile":profile,"client_priority":priority,"open_reminders":reminders,"whatsapp_overview":overview,"waiting_now":waiting,"recent_events":events,"day_event_count":len(rows),"events_sent":len(events),"last_event_ts":last_event_ts,"accumulated_learning":learning,"working_hours":{"weekdays":"segunda a sexta","periods":["07:50-12:08","13:30-18:00"],"waiting_metrics_use_business_time":True},"goal":"atuar como copiloto/CRM assistido: priorizar clientes, aprofundar estrategia por cliente, conectar lembretes ao contexto comercial e sugerir proximas acoes sem enviar mensagens nem alterar lembretes automaticamente"}
''')

text=replace_method(text,'MainWindow','_ai_prompt',r'''    def _ai_prompt(self,mode):
        base=("Você é a IA Observadora do ALIYVO, um copiloto comercial para vendas de autopeças pesadas pelo WhatsApp. "
              "Analise somente os dados fornecidos. Não invente fatos, peças, preços, venda fechada ou intenção do cliente. "
              "O vendedor trabalha rápido e usa respostas curtas; não critique abreviações ou informalidade se não prejudicarem a venda. "
              "Mensagens de encerramento como ok, show, obrigado, valeu e equivalentes normalmente não exigem resposta. "
              "Diferencie sempre FATO OBSERVADO, INDÍCIO e SUGESTÃO. Um sinal textual de fechamento não prova faturamento. "
              "Gargalos de atendimento não são automações por si só. Lembretes são tarefas do usuário: você pode priorizar e sugerir, mas nunca afirmar que criou, adiou, concluiu ou enviou algo. "
              "Nunca envie nada ao cliente.")
        if mode=="conversation":
            return base+("\nAnalise a conversa atual e responda em português com: 1) PRIORIDADE AGORA e motivo; 2) SITUAÇÃO; 3) O QUE FALTA FAZER/RESPONDER; 4) RESPOSTA SUGERIDA curta, se couber; 5) AÇÃO/FERRAMENTA; 6) se existe lembrete relacionado; 7) oportunidade de automação. Seja objetivo.")
        if mode=="client_profile":
            return base+("\nVocê recebeu o perfil acumulado, prioridade atual, lembretes e eventos recentes de UM cliente. Produza: 1) FATOS CONFIRMADOS; 2) PADRÕES; 3) DESFECHOS OBSERVADOS; 4) PRIORIDADE ATUAL e motivo; 5) COMO ABORDAR MELHOR; 6) O QUE ANTECIPAR NESTA CONVERSA; 7) LEMBRETES/TAREFAS RELACIONADOS; 8) O QUE AINDA NÃO SABEMOS; 9) AUTOMAÇÃO/FERRAMENTA útil. Não atribua características sensíveis ou personalidade ao cliente.")
        if mode=="crm_reminders":
            return base+("\nVocê recebeu os lembretes abertos, panorama do WhatsApp, clientes aguardando e perfis aprendidos. Monte um CRM do dia: 1) FAZER PRIMEIRO (máx. 5 itens, com motivo); 2) LEMBRETES VENCIDOS/URGENTES; 3) CLIENTES QUE MERECEM RETORNO; 4) TAREFAS QUE PODEM ESPERAR; 5) RISCOS DE ESQUECIMENTO; 6) uma sugestão de organização para hoje. Não invente prazos nem resultados.")
        return base+("\nFaça uma auditoria do fluxo recente com: 1) ATENÇÃO AGORA; 2) PADRÕES COMERCIAIS; 3) GARGALOS; 4) DESFECHOS OBSERVÁVEIS; 5) LEMBRETES/CRM; 6) TAREFAS REPETITIVAS; 7) FERRAMENTAS/ATALHOS; 8) AUTOMAÇÕES FUTURAS; 9) O QUE CONTINUAR OBSERVANDO.")
''')

# Corrige seleção de prompt por modo (antes client_profile caía em observer).
ms=ast.parse(text)
old='"instructions":self._ai_prompt("conversation" if mode=="conversation" else "observer"),'
if old not in text: raise SystemExit('ai instructions mapping anchor missing')
text=text.replace(old,'"instructions":self._ai_prompt(mode if mode in ("conversation","client_profile","crm_reminders") else "observer"),',1)

text=replace_method(text,'MainWindow','_ai_observer_dialog',r'''    def _ai_observer_dialog(self,parent=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPlainTextEdit,QPushButton
        dlg=QDialog(parent or self);dlg.setWindowTitle("🤖 IA Observadora do ALIYVO");dlg.resize(940,720)
        lay=QVBoxLayout(dlg);cfg=self._ai_config_load();key_ok=bool(self._ai_api_key())
        status=QLabel(("✅ IA configurada" if key_ok else "⚠ Configure a chave da API")+(f" • automático a cada {cfg.get('interval_minutes')} min" if key_ok and cfg.get("enabled") else " • automático desligado"))
        lay.addWidget(status);txt=QPlainTextEdit();txt.setReadOnly(True);lay.addWidget(txt,1)
        self._ai_observer_text_widget=txt;self._ai_observer_status_widget=status
        latest=self._ai_history_latest()
        if isinstance(latest,dict) and latest.get("ok"):txt.setPlainText(f"Última análise: {latest.get('time','')}\nModelo: {latest.get('model','')}\n\n{latest.get('analysis','')}")
        else:txt.setPlainText("A IA acumula padrões locais, perfis por cliente e agora também pode cruzar lembretes com o atendimento. Nenhuma mensagem é enviada automaticamente.")
        bar=QHBoxLayout();settings=QPushButton("⚙ Configurar");now_btn=QPushButton("🧠 Analisar trabalho");chat_btn=QPushButton("💬 Conversa atual");assist_btn=QPushButton("💡 Assistência atual");crm_btn=QPushButton("🧭 CRM do dia");learn_btn=QPushButton("📚 Aprendizado");close=QPushButton("Fechar")
        for b in (settings,now_btn,chat_btn,assist_btn,crm_btn,learn_btn):bar.addWidget(b)
        bar.addStretch(1);bar.addWidget(close);lay.addLayout(bar)
        settings.clicked.connect(lambda:self._ai_settings_dialog(dlg));now_btn.clicked.connect(lambda:self._ai_observer_analyze("observer",False));chat_btn.clicked.connect(lambda:self._ai_observer_analyze("conversation",False));assist_btn.clicked.connect(lambda:self._ai_current_assist_dialog(dlg));crm_btn.clicked.connect(lambda:self._ai_crm_reminders_dialog(dlg));learn_btn.clicked.connect(lambda:self._ai_learning_dialog(dlg));close.clicked.connect(dlg.accept)
        dlg.finished.connect(lambda _=0:self._ai_observer_dialog_closed(txt,status));dlg.exec()
''')

# Lembretes visuais e CRM.
text=replace_method(text,'MainWindow','_reminder_show_dialog',r'''    def _reminder_show_dialog(self):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QListWidget,QListWidgetItem,QPushButton,QComboBox,QLabel
        from PyQt6.QtGui import QColor,QFont,QBrush
        import datetime
        dlg=QDialog(self); dlg.setWindowTitle("⏰ Lembretes do ALIYVO — CRM visual"); dlg.resize(820,590); lay=QVBoxLayout(dlg)
        top=QHBoxLayout();top.addWidget(QLabel("Mostrar:"));filt=QComboBox();filt.addItems(["A fazer","Concluídos","Todos","Vencidos"]);filt.setCurrentText("A fazer");top.addWidget(filt)
        counts=QLabel("");counts.setStyleSheet("font-weight:700;");top.addWidget(counts);top.addStretch(1);crm=QPushButton("🧭 CRM do dia");top.addWidget(crm);lay.addLayout(top)
        legend=QLabel("🔴 vencido   🟠 hoje   🔵 futuro   🟢 concluído  •  cores leves para leitura rápida")
        legend.setStyleSheet("font-weight:700;color:#425466;padding:3px;");lay.addWidget(legend)
        lst=QListWidget();lst.setSpacing(3);lay.addWidget(lst,1)
        def refresh():
            lst.clear();now=datetime.datetime.now();nowts=now.timestamp();today=now.date();allrows=[x for x in self._reminders if isinstance(x,dict)];pending=[x for x in allrows if not x.get("done")];done_rows=[x for x in allrows if x.get("done")];overdue=[x for x in pending if float(x.get("due_ts") or 0)<nowts]
            counts.setText(f"A fazer: {len(pending)}   •   Concluídos: {len(done_rows)}   •   Vencidos: {len(overdue)}");mode=filt.currentText();rows=pending if mode=="A fazer" else done_rows if mode=="Concluídos" else overdue if mode=="Vencidos" else allrows
            rows=sorted(rows,key=lambda x:(bool(x.get("done")),float(x.get("due_ts") or 0)))
            for r in rows:
                due_ts=float(r.get("due_ts") or 0);due_dt=datetime.datetime.fromtimestamp(due_ts) if due_ts else None;due=due_dt.strftime("%d/%m/%Y %H:%M") if due_dt else "Sem data";client=str(r.get("client") or "").strip();is_done=bool(r.get("done"));is_over=(not is_done and due_ts and due_ts<nowts);is_today=bool(due_dt and due_dt.date()==today and not is_done and not is_over)
                icon="✅" if is_done else "🔴" if is_over else "🟠" if is_today else "🔵"
                title=str(r.get('text',''));line=f"{icon}  {title}\n     {due}"+(f"   •   {client}" if client else "")
                it=QListWidgetItem(line);it.setData(Qt.ItemDataRole.UserRole,str(r.get("id") or ""));font=QFont();font.setBold(True);font.setPointSize(10);it.setFont(font)
                if is_done:it.setBackground(QBrush(QColor("#E8F7EE")));it.setForeground(QBrush(QColor("#1E6B3A")))
                elif is_over:it.setBackground(QBrush(QColor("#FDECEC")));it.setForeground(QBrush(QColor("#9B1C1C")))
                elif is_today:it.setBackground(QBrush(QColor("#FFF4DF")));it.setForeground(QBrush(QColor("#8A4B00")))
                else:it.setBackground(QBrush(QColor("#EAF3FF")));it.setForeground(QBrush(QColor("#174A7E")))
                lst.addItem(it)
        refresh();filt.currentIndexChanged.connect(refresh)
        bar=QHBoxLayout();add_current=QPushButton("⏰ Desta conversa");add=QPushButton("＋ Novo");edit=QPushButton("✏ Editar");complete=QPushButton("✅ Concluir");reopen=QPushButton("↩ Reabrir");delete=QPushButton("🗑 Excluir");close=QPushButton("Fechar")
        for b in (add_current,add,edit,complete,reopen,delete):bar.addWidget(b)
        bar.addStretch(1);bar.addWidget(close);lay.addLayout(bar)
        def selected():
            it=lst.currentItem();return str(it.data(Qt.ItemDataRole.UserRole) or "") if it else ""
        def finish():
            rid=selected();
            if not rid:return
            for r in self._reminders:
                if str(r.get("id") or "")==rid:r["done"]=True;r["alerted"]=True;self._diagnostic_log("reminder_done",client=r.get("client",""),text=r.get("text",""));break
            self._reminder_save();self._reminder_update_button();refresh()
        def do_reopen():
            rid=selected();
            if not rid:return
            for r in self._reminders:
                if str(r.get("id") or "")==rid:r["done"]=False;r["alerted"]=False;self._diagnostic_log("reminder_reopened",client=r.get("client",""),text=r.get("text",""));break
            self._reminder_save();self._reminder_update_button();refresh()
        def remove():
            rid=selected();
            if not rid:return
            self._reminders=[r for r in self._reminders if str(r.get("id") or "")!=rid];self._reminder_save();self._reminder_update_button();refresh()
        def do_edit():
            rid=selected();
            if rid:self._reminder_edit(rid,dlg,refresh)
        add_current.clicked.connect(lambda:self._reminder_add_from_current(dlg,refresh));add.clicked.connect(lambda:self._reminder_add(dlg,refresh));edit.clicked.connect(do_edit);complete.clicked.connect(finish);reopen.clicked.connect(do_reopen);delete.clicked.connect(remove);crm.clicked.connect(lambda:self._ai_crm_reminders_dialog(dlg));close.clicked.connect(dlg.accept);lst.itemDoubleClicked.connect(lambda _it:do_edit());dlg.exec()
''')

# Campos de data e hora separados, com hora inteira selecionada ao clicar.
edit_code=r'''    def _reminder_edit(self,rid,parent=None,refresh=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QFormLayout,QLineEdit,QDateEdit,QHBoxLayout,QPushButton,QMessageBox
        from PyQt6.QtCore import QDate,QTimer
        import time,datetime
        class TimeEdit(QLineEdit):
            def mousePressEvent(self,e):
                super().mousePressEvent(e);QTimer.singleShot(0,self.selectAll)
            def focusInEvent(self,e):
                super().focusInEvent(e);QTimer.singleShot(0,self.selectAll)
        reminder=None
        for r in getattr(self,"_reminders",[]):
            if isinstance(r,dict) and str(r.get("id") or "")==str(rid or ""):reminder=r;break
        if reminder is None:return
        dlg=QDialog(parent or self);dlg.setWindowTitle("✏ Editar lembrete");dlg.resize(560,300);lay=QVBoxLayout(dlg);form=QFormLayout()
        textw=QLineEdit(str(reminder.get("text") or ""));old=datetime.datetime.fromtimestamp(float(reminder.get("due_ts") or time.time()))
        datew=QDateEdit(QDate(old.year,old.month,old.day));datew.setDisplayFormat("dd/MM/yyyy");datew.setCalendarPopup(True)
        timew=TimeEdit(old.strftime("%H:%M"));timew.setInputMask("00:00");timew.setMaximumWidth(100);timew.setToolTip("Clique uma vez e digite a hora inteira, por exemplo 14:30")
        clientw=QLineEdit(str(reminder.get("client") or ""));clientw.setPlaceholderText("Opcional — ex.: Antiqueira")
        form.addRow("Lembrete:",textw);form.addRow("Data:",datew);form.addRow("Hora:",timew);form.addRow("Cliente:",clientw);lay.addLayout(form)
        bar=QHBoxLayout();save=QPushButton("💾 Salvar alterações");cancel=QPushButton("Cancelar");bar.addStretch(1);bar.addWidget(save);bar.addWidget(cancel);lay.addLayout(bar)
        def do_save():
            txt=textw.text().strip()
            if not txt:QMessageBox.information(dlg,"Lembrete","Digite o que você precisa lembrar.");return
            try:
                hh,mm=[int(x) for x in timew.text().split(':')]
                if not (0<=hh<=23 and 0<=mm<=59):raise ValueError
            except Exception:QMessageBox.information(dlg,"Lembrete","Digite uma hora válida no formato HH:MM.");return
            qd=datew.date();due=datetime.datetime(qd.year(),qd.month(),qd.day(),hh,mm).timestamp();old_text=str(reminder.get("text") or "");old_due=float(reminder.get("due_ts") or 0)
            reminder["text"]=txt;reminder["due_ts"]=due;reminder["client"]=clientw.text().strip();reminder["updated_at"]=time.time();reminder["alerted"]=False
            self._reminder_save();self._reminder_update_button();self._diagnostic_log("reminder_edited",client=reminder.get("client","") or "",text=txt,due_ts=due,old_text=old_text,old_due_ts=old_due);dlg.accept()
            if callable(refresh):refresh()
        save.clicked.connect(do_save);cancel.clicked.connect(dlg.reject);dlg.exec()
'''
text=replace_method(text,'MainWindow','_reminder_edit',edit_code)

add_code=r'''    def _reminder_add(self,parent=None,refresh=None,force_client=None,context=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QFormLayout,QLineEdit,QDateEdit,QCheckBox,QHBoxLayout,QPushButton,QMessageBox,QLabel
        from PyQt6.QtCore import QDate,QTimer
        import time,uuid,datetime
        class TimeEdit(QLineEdit):
            def mousePressEvent(self,e):
                super().mousePressEvent(e);QTimer.singleShot(0,self.selectAll)
            def focusInEvent(self,e):
                super().focusInEvent(e);QTimer.singleShot(0,self.selectAll)
        initial=datetime.datetime.now()+datetime.timedelta(hours=1)
        dlg=QDialog(parent or self);dlg.setWindowTitle("Novo lembrete");dlg.resize(590,350);lay=QVBoxLayout(dlg);form=QFormLayout();textw=QLineEdit();textw.setPlaceholderText("Ex.: fechar pedido Antiqueira")
        datew=QDateEdit(QDate(initial.year,initial.month,initial.day));datew.setDisplayFormat("dd/MM/yyyy");datew.setCalendarPopup(True)
        timew=TimeEdit(initial.strftime("%H:%M"));timew.setInputMask("00:00");timew.setMaximumWidth(100);timew.setToolTip("Clique uma vez e digite a hora inteira")
        current=str(force_client or getattr(self,"_diagnostic_active_name","") or "").strip();link=QCheckBox("Vincular ao contato atual");link.setChecked(bool(current));form.addRow("Lembrete:",textw);form.addRow("Data:",datew);form.addRow("Hora:",timew)
        if current:form.addRow("Contato:",QLabel(current));form.addRow("",link)
        ctx=str(context or "").strip()
        if ctx:
            lab=QLabel(ctx[-500:]);lab.setWordWrap(True);lab.setStyleSheet("color:#526777;font-size:10px;");form.addRow("Contexto salvo:",lab)
        lay.addLayout(form);bar=QHBoxLayout();save=QPushButton("Salvar lembrete");cancel=QPushButton("Cancelar");bar.addStretch(1);bar.addWidget(save);bar.addWidget(cancel);lay.addLayout(bar)
        def do_save():
            txt=textw.text().strip()
            if not txt:QMessageBox.information(dlg,"Lembrete","Digite o que você precisa lembrar.");return
            try:
                hh,mm=[int(x) for x in timew.text().split(':')]
                if not (0<=hh<=23 and 0<=mm<=59):raise ValueError
            except Exception:QMessageBox.information(dlg,"Lembrete","Digite uma hora válida no formato HH:MM.");return
            qd=datew.date();due=datetime.datetime(qd.year(),qd.month(),qd.day(),hh,mm).timestamp();client=current if (current and link.isChecked()) else "";r={"id":uuid.uuid4().hex,"text":txt,"due_ts":due,"client":client,"context":ctx if client else "","done":False,"alerted":False,"created_at":time.time()}
            if client:
                pri=self._ai_priority_for_client(client);r["ai_priority_at_creation"]=pri
            self._reminders.append(r);self._reminder_save();self._reminder_update_button();self._diagnostic_log("reminder_created",client=client,text=txt,due_ts=due);dlg.accept()
            if callable(refresh):refresh()
        save.clicked.connect(do_save);cancel.clicked.connect(dlg.reject);dlg.exec()
'''
text=replace_method(text,'MainWindow','_reminder_add',add_code)

text=replace_method(text,'MainWindow','_reminder_check',r'''    def _reminder_check(self):
        import time,datetime
        from PyQt6.QtWidgets import QMessageBox
        now=time.time();changed=False
        due=[r for r in getattr(self,"_reminders",[]) if isinstance(r,dict) and not r.get("done") and not r.get("alerted") and float(r.get("due_ts") or 0)<=now]
        for r in due[:3]:
            r["alerted"]=True;changed=True;client=str(r.get("client") or "").strip();ctx=str(r.get("context") or "").strip();body=(f"Cliente: {client}\n\n" if client else "")+str(r.get("text") or "")
            if client:
                pri=self._ai_priority_for_client(client);body+=f"\n\nPrioridade CRM: {pri.get('level','baixa').upper()}"+("\n"+"; ".join(pri.get("reasons") or []) if pri.get("reasons") else "")
            if ctx:body+="\n\nContexto:\n"+ctx[-500:]
            box=QMessageBox(self);box.setWindowTitle("⏰ Lembrete ALIYVO");box.setIcon(QMessageBox.Icon.Information);box.setText(body)
            done=box.addButton("✅ Concluir",QMessageBox.ButtonRole.AcceptRole);openb=box.addButton("↗ Abrir conversa",QMessageBox.ButtonRole.ActionRole) if client else None;m20=box.addButton("⏳ Adiar 20 min",QMessageBox.ButtonRole.ActionRole);h1=box.addButton("⏰ Adiar 1 hora",QMessageBox.ButtonRole.ActionRole);tom=box.addButton("🌅 Amanhã 09:00",QMessageBox.ButtonRole.ActionRole);box.addButton("Fechar",QMessageBox.ButtonRole.RejectRole)
            box.exec();clicked=box.clickedButton()
            if clicked==done:r["done"]=True;self._diagnostic_log("reminder_done",client=client,text=r.get("text",""))
            elif openb is not None and clicked==openb:
                try:self._attendance_open_chat(client)
                except Exception:pass
            elif clicked==m20:r["due_ts"]=now+1200;r["alerted"]=False;self._diagnostic_log("reminder_snoozed",client=client,text=r.get("text",""),minutes=20)
            elif clicked==h1:r["due_ts"]=now+3600;r["alerted"]=False;self._diagnostic_log("reminder_snoozed",client=client,text=r.get("text",""),minutes=60)
            elif clicked==tom:
                d=datetime.datetime.now()+datetime.timedelta(days=1);d=d.replace(hour=9,minute=0,second=0,microsecond=0);r["due_ts"]=d.timestamp();r["alerted"]=False;self._diagnostic_log("reminder_snoozed",client=client,text=r.get("text",""),until="tomorrow_0900")
        if changed:self._reminder_save();self._reminder_update_button()
''')

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched CRM AI + visual reminders',version)
