from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v41.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)


def method_source(src,class_name,method_name):
    tree=ast.parse(src)
    cls=next((n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==class_name),None)
    if cls is None: raise SystemExit(f'class {class_name} not found')
    target=next((n for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==method_name),None)
    if target is None: raise SystemExit(f'method {class_name}.{method_name} not found')
    lines=src.splitlines(keepends=True)
    return ''.join(lines[target.lineno-1:target.end_lineno])


def replace_method(src,class_name,method_name,new_code):
    tree=ast.parse(src)
    cls=next((n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==class_name),None)
    if cls is None: raise SystemExit(f'class {class_name} not found')
    target=next((n for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==method_name),None)
    if target is None: raise SystemExit(f'method {class_name}.{method_name} not found')
    lines=src.splitlines(keepends=True)
    start=sum(len(x) for x in lines[:target.lineno-1]); end=sum(len(x) for x in lines[:target.end_lineno])
    if not new_code.endswith('\n'): new_code+='\n'
    return src[:start]+new_code+src[end:]

# Estado da IA Observadora no bootstrap do diagnostico.
ms=method_source(text,'MainWindow','_diagnostic_start')
anchor='        self._diagnostic_current_unread_names=set()\n'
if anchor not in ms:
    anchor='        self._diagnostic_unread_registry={}\n'
if anchor not in ms: raise SystemExit('AI diagnostic start anchor not found')
insert=(
'        self._ai_observer_busy=False\n'
'        self._ai_net=None\n'
'        self._ai_observer_reply=None\n'
'        self._ai_observer_text_widget=None\n'
'        self._ai_observer_status_widget=None\n'
'        self._ai_last_analyzed_event_ts=0.0\n'
'        self._ai_request_meta={}\n'
'        try:\n'
'            _last=self._ai_history_latest()\n'
'            self._ai_last_analyzed_event_ts=float((_last or {}).get("last_event_ts") or 0)\n'
'        except Exception:pass\n'
'        self._ai_observer_timer=QTimer(self)\n'
'        self._ai_observer_reschedule()\n'
)
ms=ms.replace(anchor,anchor+insert,1)
text=replace_method(text,'MainWindow','_diagnostic_start',ms)

# Camada integrada de IA. A chave e protegida pelo DPAPI do Windows e nunca vai para o repositorio.
anchor='    def _diagnostic_show_dialog(self):\n'
if anchor not in text: raise SystemExit('diagnostic dialog anchor not found')
ai_methods=r'''    def _ai_config_path(self):
        return USER_DATA_DIR/"ia_observadora_config.json"

    def _ai_history_path(self):
        return USER_DATA_DIR/"ia_observadora_historico.jsonl"

    def _ai_dpapi_encrypt(self,value):
        import base64,ctypes,sys
        if not value:return ""
        if sys.platform!="win32":return ""
        from ctypes import wintypes
        class DATA_BLOB(ctypes.Structure):
            _fields_=[("cbData",wintypes.DWORD),("pbData",ctypes.POINTER(ctypes.c_char))]
        raw=str(value).encode("utf-8")
        buf=ctypes.create_string_buffer(raw)
        inp=DATA_BLOB(len(raw),ctypes.cast(buf,ctypes.POINTER(ctypes.c_char)))
        out=DATA_BLOB()
        ok=ctypes.windll.crypt32.CryptProtectData(ctypes.byref(inp),"ALIYVO IA",None,None,None,0,ctypes.byref(out))
        if not ok:return ""
        try:data=ctypes.string_at(out.pbData,out.cbData)
        finally:ctypes.windll.kernel32.LocalFree(out.pbData)
        return base64.b64encode(data).decode("ascii")

    def _ai_dpapi_decrypt(self,value):
        import base64,ctypes,sys
        if not value or sys.platform!="win32":return ""
        from ctypes import wintypes
        class DATA_BLOB(ctypes.Structure):
            _fields_=[("cbData",wintypes.DWORD),("pbData",ctypes.POINTER(ctypes.c_char))]
        try:raw=base64.b64decode(str(value))
        except Exception:return ""
        buf=ctypes.create_string_buffer(raw)
        inp=DATA_BLOB(len(raw),ctypes.cast(buf,ctypes.POINTER(ctypes.c_char)))
        out=DATA_BLOB()
        ok=ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(inp),None,None,None,None,0,ctypes.byref(out))
        if not ok:return ""
        try:data=ctypes.string_at(out.pbData,out.cbData)
        finally:ctypes.windll.kernel32.LocalFree(out.pbData)
        try:return data.decode("utf-8")
        except Exception:return ""

    def _ai_config_load(self):
        cfg={"enabled":False,"interval_minutes":10,"model":"gpt-5.6-luna","api_key_dpapi":""}
        try:
            p=self._ai_config_path()
            if p.exists():
                d=json.loads(p.read_text(encoding="utf-8"))
                if isinstance(d,dict):cfg.update(d)
        except Exception:pass
        try:cfg["interval_minutes"]=max(5,min(60,int(cfg.get("interval_minutes") or 10)))
        except Exception:cfg["interval_minutes"]=10
        if str(cfg.get("model") or "") not in ("gpt-5.6-luna","gpt-5.6-terra","gpt-5.6-sol"):
            cfg["model"]="gpt-5.6-luna"
        return cfg

    def _ai_config_save(self,cfg):
        try:
            USER_DATA_DIR.mkdir(parents=True,exist_ok=True)
            self._ai_config_path().write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding="utf-8")
            return True
        except Exception:return False

    def _ai_api_key(self):
        cfg=self._ai_config_load()
        try:return self._ai_dpapi_decrypt(cfg.get("api_key_dpapi") or "")
        except Exception:return ""

    def _ai_observer_reschedule(self):
        try:
            timer=getattr(self,"_ai_observer_timer",None)
            if timer is None:return
            try:timer.timeout.disconnect()
            except Exception:pass
            cfg=self._ai_config_load()
            timer.setInterval(max(5,int(cfg.get("interval_minutes") or 10))*60000)
            timer.timeout.connect(self._ai_observer_tick)
            if bool(cfg.get("enabled")) and self._ai_api_key():timer.start()
            else:timer.stop()
        except Exception:pass

    def _ai_history_append(self,row):
        try:
            USER_DATA_DIR.mkdir(parents=True,exist_ok=True)
            with self._ai_history_path().open("a",encoding="utf-8") as f:
                f.write(json.dumps(row,ensure_ascii=False)+"\n")
        except Exception:pass

    def _ai_history_latest(self):
        try:
            p=self._ai_history_path()
            if not p.exists():return None
            lines=p.read_text(encoding="utf-8",errors="ignore").splitlines()
            for line in reversed(lines[-80:]):
                try:
                    d=json.loads(line)
                    if isinstance(d,dict):return d
                except Exception:pass
        except Exception:pass
        return None

    def _ai_compact_event(self,x):
        if not isinstance(x,dict):return None
        keep={}
        for k in ("time","event","client","text","response_seconds","total_wait_seconds","until_open_seconds","after_open_seconds","tool","direction","call_type","duration_seconds","interruptions","max_unread_during_wait","unread_count","content_type","needs_reply","snippet"):
            if k in x and x.get(k) not in (None,""):
                v=x.get(k)
                if isinstance(v,str):v=v[:420]
                keep[k]=v
        return keep or None

    def _ai_build_context(self,mode="observer"):
        import datetime,time
        now=time.time(); today=datetime.date.today().isoformat(); groups=set(self._diagnostic_groups_load())
        rows=[]
        for x in self._diagnostic_read():
            if not isinstance(x,dict):continue
            if not str(x.get("time") or "").startswith(today):continue
            if str(x.get("client") or "").strip() in groups:continue
            rows.append(x)
        active=str(getattr(self,"_diagnostic_active_name","") or "").strip()
        if mode=="conversation" and active:
            selected=[x for x in rows if str(x.get("client") or "").strip()==active][-60:]
        else:
            selected=rows[-140:]
        events=[self._ai_compact_event(x) for x in selected]
        events=[x for x in events if x]
        last_event_ts=max([float(x.get("ts") or 0) for x in rows] or [0])
        overview={}
        try:overview=self._diagnostic_whatsapp_overview_payload()
        except Exception:pass
        waiting=[]
        try:waiting=self._diagnostic_waiting_snapshot()[:25]
        except Exception:pass
        current_context=""
        try:current_context=str((getattr(self,"_diagnostic_last_context_by_contact",{}) or {}).get(active) or "")[-1600:]
        except Exception:pass
        data={
            "generated_at":datetime.datetime.now().isoformat(timespec="seconds"),
            "mode":mode,
            "active_contact":active,
            "active_recent_context":current_context,
            "whatsapp_overview":overview,
            "waiting_now":waiting,
            "recent_events":events,
            "day_event_count":len(rows),
            "last_event_ts":last_event_ts,
            "known_tools":["Somaforce busca de pecas","busca por imagem","consulta placa/chassi","prazo de pagamento","lembretes","diagnostico"],
            "goal":"observar o trabalho comercial, melhorar respostas, detectar esquecimentos, gargalos e oportunidades de ferramenta/automacao sem enviar mensagens automaticamente"
        }
        return data

    def _ai_prompt(self,mode):
        base=("Você é a IA Observadora do ALIYVO, um copiloto comercial para vendas de autopeças pesadas pelo WhatsApp. "
              "Analise somente os dados fornecidos. Não invente fatos, peças, preços ou intenção do cliente. "
              "O vendedor trabalha rápido e usa respostas curtas; não critique abreviações ou informalidade se não prejudicarem a venda. "
              "Mensagens de encerramento como ok, show, obrigado, valeu e equivalentes normalmente não exigem resposta. "
              "Nunca diga que uma automação já existe se os dados não mostrarem isso. Diferencie observação de hipótese. "
              "Seu objetivo é aprender o fluxo real e descobrir o que o ALIYVO pode automatizar no futuro. Não envie nada ao cliente.")
        if mode=="conversation":
            return base+("\nAnalise a conversa atual e responda em português com: "
                         "1) SITUAÇÃO AGORA; 2) O QUE AINDA FALTA RESPONDER/FAZER; 3) RESPOSTA SUGERIDA curta, somente se realmente couber; "
                         "4) PRÓXIMA FERRAMENTA/AÇÃO útil; 5) OPORTUNIDADE DE AUTOMAÇÃO aprendida com este caso. Seja objetivo.")
        return base+("\nFaça uma auditoria do fluxo recente e responda em português com: "
                     "1) ATENÇÃO AGORA (somente problemas concretos); 2) PADRÕES DAS SUAS RESPOSTAS; 3) TAREFAS REPETITIVAS; "
                     "4) FERRAMENTAS/ATALHOS QUE VALE CRIAR; 5) AUTOMAÇÕES FUTURAS; 6) O QUE A IA DEVE CONTINUAR OBSERVANDO. "
                     "Priorize ganhos de tempo reais e evite sugestões genéricas.")

    def _ai_response_text(self,data):
        if not isinstance(data,dict):return ""
        direct=str(data.get("output_text") or "").strip()
        if direct:return direct
        parts=[]
        for item in data.get("output") or []:
            if not isinstance(item,dict):continue
            for c in item.get("content") or []:
                if isinstance(c,dict) and c.get("type") in ("output_text","text"):
                    t=str(c.get("text") or "").strip()
                    if t:parts.append(t)
        return "\n".join(parts).strip()

    def _ai_observer_set_status(self,text):
        w=getattr(self,"_ai_observer_status_widget",None)
        try:
            if w is not None:w.setText(str(text))
        except Exception:pass

    def _ai_observer_set_text(self,text):
        w=getattr(self,"_ai_observer_text_widget",None)
        try:
            if w is not None:w.setPlainText(str(text))
        except Exception:pass

    def _ai_observer_analyze(self,mode="observer",silent=False):
        if bool(getattr(self,"_ai_observer_busy",False)):
            if not silent:self._ai_observer_set_status("A IA já está analisando…")
            return
        key=self._ai_api_key()
        if not key:
            if not silent:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self,"IA Observadora","Configure primeiro sua chave da API.\n\nA assinatura do ChatGPT e a API possuem cobranças separadas.")
                self._ai_settings_dialog(self)
            return
        ctx=self._ai_build_context(mode)
        last_ts=float(ctx.get("last_event_ts") or 0)
        if mode=="auto" and last_ts<=float(getattr(self,"_ai_last_analyzed_event_ts",0) or 0):
            return
        cfg=self._ai_config_load(); model=str(cfg.get("model") or "gpt-5.6-luna")
        body={
            "model":model,
            "store":False,
            "reasoning":{"effort":"low"},
            "instructions":self._ai_prompt("conversation" if mode=="conversation" else "observer"),
            "input":json.dumps(ctx,ensure_ascii=False,separators=(",",":")),
            "max_output_tokens":1800
        }
        try:
            from PyQt6.QtCore import QUrl,QByteArray
            from PyQt6.QtNetwork import QNetworkAccessManager,QNetworkRequest
            if getattr(self,"_ai_net",None) is None:self._ai_net=QNetworkAccessManager(self)
            req=QNetworkRequest(QUrl("https://api.openai.com/v1/responses"))
            req.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader,"application/json")
            req.setRawHeader(b"Authorization",("Bearer "+key).encode("utf-8"))
            req.setRawHeader(b"User-Agent",("ALIYVO/"+str(ALIYVO_VERSION)).encode("ascii","ignore"))
            self._ai_observer_busy=True
            self._ai_request_meta={"mode":mode,"model":model,"last_event_ts":last_ts,"started_at":__import__("time").time()}
            self._ai_observer_set_status(f"Analisando com {model}…")
            if not silent:self._ai_observer_set_text("A IA está lendo o contexto recente do ALIYVO. Nenhuma mensagem será enviada ao WhatsApp.")
            reply=self._ai_net.post(req,QByteArray(json.dumps(body,ensure_ascii=False).encode("utf-8")))
            self._ai_observer_reply=reply
            reply.finished.connect(lambda r=reply:self._ai_request_finished(r))
        except Exception as e:
            self._ai_observer_busy=False
            self._ai_observer_set_status("Falha ao iniciar a análise")
            if not silent:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self,"IA Observadora",f"Não consegui iniciar a análise:\n{e}")

    def _ai_request_finished(self,reply):
        import datetime,time
        meta=dict(getattr(self,"_ai_request_meta",{}) or {})
        self._ai_observer_busy=False
        raw="";status=0
        try:
            from PyQt6.QtNetwork import QNetworkRequest
            try:status=int(reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) or 0)
            except Exception:status=0
            raw=bytes(reply.readAll()).decode("utf-8","replace")
        except Exception as e:raw=str(e)
        finally:
            try:reply.deleteLater()
            except Exception:pass
        try:data=json.loads(raw) if raw.strip().startswith("{") else {}
        except Exception:data={}
        if status<200 or status>=300:
            msg=""
            try:msg=str((data.get("error") or {}).get("message") or "")
            except Exception:pass
            if not msg:msg=raw[:700] or f"HTTP {status}"
            self._ai_observer_set_status("Erro na API")
            self._ai_observer_set_text("Não consegui concluir a análise.\n\n"+msg)
            self._ai_history_append({"time":datetime.datetime.now().isoformat(timespec="seconds"),"mode":meta.get("mode"),"model":meta.get("model"),"ok":False,"error":msg[:1000],"last_event_ts":meta.get("last_event_ts",0)})
            return
        out=self._ai_response_text(data)
        if not out:out="A API respondeu, mas não encontrei texto de análise na resposta."
        usage=data.get("usage") if isinstance(data,dict) else {}; usage=usage if isinstance(usage,dict) else {}
        inp=int(usage.get("input_tokens") or 0);outtok=int(usage.get("output_tokens") or 0)
        elapsed=max(0,time.time()-float(meta.get("started_at") or time.time()))
        header=(f"IA OBSERVADORA — {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                f"Modelo: {meta.get('model') or '-'} • tokens: {inp} entrada / {outtok} saída • {elapsed:.1f}s\n\n")
        full=header+out
        self._ai_observer_set_status("Análise concluída")
        self._ai_observer_set_text(full)
        self._ai_last_analyzed_event_ts=float(meta.get("last_event_ts") or self._ai_last_analyzed_event_ts or 0)
        self._ai_history_append({"time":datetime.datetime.now().isoformat(timespec="seconds"),"mode":meta.get("mode"),"model":meta.get("model"),"ok":True,"input_tokens":inp,"output_tokens":outtok,"analysis":out,"last_event_ts":self._ai_last_analyzed_event_ts})
        try:self._diagnostic_log("ai_analysis",client=str(getattr(self,"_diagnostic_active_name","") or ""),mode=str(meta.get("mode") or ""),model=str(meta.get("model") or ""),input_tokens=inp,output_tokens=outtok)
        except Exception:pass

    def _ai_observer_tick(self):
        cfg=self._ai_config_load()
        if not bool(cfg.get("enabled")) or not self._ai_api_key():return
        self._ai_observer_analyze("auto",True)

    def _ai_settings_dialog(self,parent=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QCheckBox,QSpinBox,QComboBox,QPushButton,QMessageBox
        dlg=QDialog(parent or self);dlg.setWindowTitle("Configurar IA Observadora");dlg.resize(590,390)
        lay=QVBoxLayout(dlg);cfg=self._ai_config_load();has_key=bool(self._ai_api_key())
        info=QLabel("A IA analisa nomes e trechos recentes das conversas para encontrar gargalos, respostas esquecidas e automações.\nNada é enviado aos clientes. Ao ativar, esse contexto é enviado à API OpenAI para análise.")
        info.setWordWrap(True);lay.addWidget(info)
        lay.addWidget(QLabel("Chave da API OpenAI:"))
        key=QLineEdit();key.setEchoMode(QLineEdit.EchoMode.Password);key.setPlaceholderText("Já existe uma chave protegida neste Windows" if has_key else "Cole aqui sua chave sk-…");lay.addWidget(key)
        enabled=QCheckBox("Analisar automaticamente em segundo plano");enabled.setChecked(bool(cfg.get("enabled")));lay.addWidget(enabled)
        row=QHBoxLayout();row.addWidget(QLabel("Intervalo:"));interval=QSpinBox();interval.setRange(5,60);interval.setSuffix(" min");interval.setValue(int(cfg.get("interval_minutes") or 10));row.addWidget(interval);row.addWidget(QLabel("Modelo:"));model=QComboBox();model.addItems(["gpt-5.6-luna","gpt-5.6-terra","gpt-5.6-sol"]);model.setCurrentText(str(cfg.get("model") or "gpt-5.6-luna"));row.addWidget(model);row.addStretch(1);lay.addLayout(row)
        note=QLabel("Recomendado: GPT-5.6 Luna para observação contínua por ter custo bem menor. O uso da API é cobrado separadamente do ChatGPT Plus.");note.setWordWrap(True);lay.addWidget(note)
        lay.addStretch(1);buttons=QHBoxLayout();save=QPushButton("💾 Salvar");remove=QPushButton("Remover chave");cancel=QPushButton("Cancelar");buttons.addWidget(save);buttons.addWidget(remove);buttons.addStretch(1);buttons.addWidget(cancel);lay.addLayout(buttons)
        def do_save():
            d=dict(cfg);typed=key.text().strip()
            if typed:
                enc=self._ai_dpapi_encrypt(typed)
                if not enc:
                    QMessageBox.warning(dlg,"IA Observadora","Não consegui proteger a chave com o Windows DPAPI.");return
                d["api_key_dpapi"]=enc
            d["enabled"]=bool(enabled.isChecked());d["interval_minutes"]=int(interval.value());d["model"]=str(model.currentText())
            if d["enabled"] and not (typed or has_key):
                QMessageBox.information(dlg,"IA Observadora","Cole uma chave da API antes de ativar a análise automática.");return
            if not self._ai_config_save(d):QMessageBox.warning(dlg,"IA Observadora","Não consegui salvar a configuração.");return
            self._ai_observer_reschedule();dlg.accept()
        def do_remove():
            d=dict(cfg);d["api_key_dpapi"]="";d["enabled"]=False
            self._ai_config_save(d);self._ai_observer_reschedule();dlg.accept()
        save.clicked.connect(do_save);remove.clicked.connect(do_remove);cancel.clicked.connect(dlg.reject);dlg.exec()

    def _ai_observer_dialog(self,parent=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPlainTextEdit,QPushButton
        dlg=QDialog(parent or self);dlg.setWindowTitle("🤖 IA Observadora do ALIYVO");dlg.resize(900,690)
        lay=QVBoxLayout(dlg);cfg=self._ai_config_load();key_ok=bool(self._ai_api_key())
        status=QLabel(("✅ IA configurada" if key_ok else "⚠ Configure a chave da API")+(f" • automático a cada {cfg.get('interval_minutes')} min" if key_ok and cfg.get("enabled") else " • automático desligado"))
        lay.addWidget(status);txt=QPlainTextEdit();txt.setReadOnly(True);lay.addWidget(txt,1)
        self._ai_observer_text_widget=txt;self._ai_observer_status_widget=status
        latest=self._ai_history_latest()
        if isinstance(latest,dict) and latest.get("ok"):
            txt.setPlainText(f"Última análise: {latest.get('time','')}\nModelo: {latest.get('model','')}\n\n{latest.get('analysis','')}")
        else:txt.setPlainText("A IA ainda não analisou este trabalho. Configure a chave e use Analisar agora.\n\nEla observa o histórico recente, o panorama do WhatsApp, tempos de resposta, ligações e ferramentas usadas. Não envia mensagens sozinha.")
        bar=QHBoxLayout();settings=QPushButton("⚙ Configurar");now_btn=QPushButton("🧠 Analisar trabalho agora");chat_btn=QPushButton("💬 Analisar conversa atual");close=QPushButton("Fechar")
        for b in (settings,now_btn,chat_btn):bar.addWidget(b)
        bar.addStretch(1);bar.addWidget(close);lay.addLayout(bar)
        settings.clicked.connect(lambda:self._ai_settings_dialog(dlg));now_btn.clicked.connect(lambda:self._ai_observer_analyze("observer",False));chat_btn.clicked.connect(lambda:self._ai_observer_analyze("conversation",False));close.clicked.connect(dlg.accept)
        dlg.finished.connect(lambda _=0:self._ai_observer_dialog_closed(txt,status));dlg.exec()

    def _ai_observer_dialog_closed(self,txt,status):
        if getattr(self,"_ai_observer_text_widget",None) is txt:self._ai_observer_text_widget=None
        if getattr(self,"_ai_observer_status_widget",None) is status:self._ai_observer_status_widget=None

'''
text=text.replace(anchor,ai_methods+anchor,1)

# Botao IA Observadora dentro do Diagnostico, sem criar outra lateral no WhatsApp.
ms=method_source(text,'MainWindow','_diagnostic_show_dialog')
old='bar=QHBoxLayout(); history=QPushButton("👤 Histórico por contato"); daily=QPushButton("📅 Resumo do dia"); folder_btn=QPushButton("📁 Abrir pasta"); refresh_btn=QPushButton("↻ Atualizar"); export=QPushButton("📤 Exportar diagnóstico"); close=QPushButton("Fechar")'
new='bar=QHBoxLayout(); history=QPushButton("👤 Histórico por contato"); daily=QPushButton("📅 Resumo do dia"); ai_btn=QPushButton("🤖 IA Observadora"); folder_btn=QPushButton("📁 Abrir pasta"); refresh_btn=QPushButton("↻ Atualizar"); export=QPushButton("📤 Exportar diagnóstico"); close=QPushButton("Fechar")'
if old not in ms: raise SystemExit('diagnostic AI bar creation anchor not found')
ms=ms.replace(old,new,1)
old='for b in (history,daily,folder_btn,refresh_btn,export):bar.addWidget(b)'
new='for b in (history,daily,ai_btn,folder_btn,refresh_btn,export):bar.addWidget(b)'
if old not in ms: raise SystemExit('diagnostic AI button list anchor not found')
ms=ms.replace(old,new,1)
old='history.clicked.connect(lambda:self._diagnostic_contact_history_dialog(dlg)); daily.clicked.connect(lambda:self._diagnostic_show_daily_summary(dlg)); folder_btn.clicked.connect(lambda:self._diagnostic_open_backup_folder(dlg)); refresh_btn.clicked.connect(refresh)'
new='history.clicked.connect(lambda:self._diagnostic_contact_history_dialog(dlg)); daily.clicked.connect(lambda:self._diagnostic_show_daily_summary(dlg)); ai_btn.clicked.connect(lambda:self._ai_observer_dialog(dlg)); folder_btn.clicked.connect(lambda:self._diagnostic_open_backup_folder(dlg)); refresh_btn.clicked.connect(refresh)'
if old not in ms: raise SystemExit('diagnostic AI connection anchor not found')
ms=ms.replace(old,new,1)
text=replace_method(text,'MainWindow','_diagnostic_show_dialog',ms)

# Backup diario inclui a ultima analise da IA, facilitando revisar os 3 dias depois.
ms=method_source(text,'MainWindow','_diagnostic_daily_backup')
anchor='                "whatsapp_overview":self._diagnostic_whatsapp_overview_payload(),\n'
if anchor not in ms: raise SystemExit('backup AI anchor not found')
ms=ms.replace(anchor,anchor+'                "ai_observer_latest":self._ai_history_latest(),\n',1)
text=replace_method(text,'MainWindow','_diagnostic_daily_backup',ms)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched integrated AI observer',version)
