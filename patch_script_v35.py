from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v35.json').read_text(encoding='utf-8'))
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
    if not new_code.endswith('\n'): new_code+='\n'
    return src[:start]+new_code+src[end:]

# 1) Quando muda de conversa, registra se deixou um atendimento pendente e
# quantas outras conversas foram abertas enquanto cada contato aguardava.
old='''        if changed_chat:\n            previous=getattr(self,"_diagnostic_last_active","") or ""; self._diagnostic_log("chat_opened",client=name,previous=previous); self._diagnostic_last_active=name\n            p=self._diagnostic_pending.get(name)\n'''
new='''        if changed_chat:\n            previous=getattr(self,"_diagnostic_last_active","") or ""\n            self._diagnostic_log("chat_opened",client=name,previous=previous)\n            self._diagnostic_last_active=name\n\n            # Toda nova conversa aberta durante uma espera ajuda a explicar a demora.\n            for _pn,_pd in list(self._diagnostic_pending.items()):\n                if not isinstance(_pd,dict) or _pn==name or _pn in groups: continue\n                if _pd.get("opened_ts"):\n                    _pd["other_chat_opens"]=int(_pd.get("other_chat_opens") or 0)+1\n                    _ch=list(_pd.get("other_chats") or [])\n                    if name and name not in _ch:\n                        _ch.append(name)\n                        _pd["other_chats"]=_ch[-20:]\n\n            # Se saiu de um contato já aberto sem responder, isso é atendimento interrompido.\n            _prev_pending=self._diagnostic_pending.get(previous)\n            if previous and previous!=name and previous not in groups and isinstance(_prev_pending,dict) and _prev_pending.get("opened_ts"):\n                _prev_pending["interruptions"]=int(_prev_pending.get("interruptions") or 0)+1\n                _prev_pending["last_interruption_ts"]=now\n                self._diagnostic_log("attendance_interrupted",client=previous,switched_to=name,interruptions=int(_prev_pending.get("interruptions") or 0),wait_so_far_seconds=max(0,int(now-float(_prev_pending.get("received_ts") or now))))\n\n            p=self._diagnostic_pending.get(name)\n'''
if old not in text: raise SystemExit('changed_chat block not found')
text=text.replace(old,new,1)

# 2) Ligações com timestamp real podem explicar parte do tempo de espera.
old_call='''                self._diagnostic_log("call",client=name,direction=direction,call_type=str(x.get("call_type") or "voice"),missed=bool(x.get("missed")),duration_seconds=int(x.get("duration_seconds") or 0),text=raw[:500],call_key=call_key)\n'''
new_call='''                _call_msg_ts=float(x.get("message_ts") or 0)\n                _call_duration=int(x.get("duration_seconds") or 0)\n                self._diagnostic_log("call",client=name,direction=direction,call_type=str(x.get("call_type") or "voice"),missed=bool(x.get("missed")),duration_seconds=_call_duration,text=raw[:500],call_key=call_key,message_ts=_call_msg_ts or None)\n                # Só atribui a ligação à espera quando o WhatsApp forneceu o horário da chamada.\n                if _call_msg_ts>0:\n                    for _pn,_pd in list(self._diagnostic_pending.items()):\n                        if not isinstance(_pd,dict): continue\n                        _recv=float(_pd.get("received_ts") or now)\n                        if _recv<=_call_msg_ts<=now:\n                            _pd["calls_during_wait"]=int(_pd.get("calls_during_wait") or 0)+1\n                            _pd["call_seconds_during_wait"]=int(_pd.get("call_seconds_during_wait") or 0)+max(0,_call_duration)\n'''
if old_call not in text: raise SystemExit('call log line not found')
text=text.replace(old_call,new_call,1)

# 3) Mantém o maior volume de não lidos observado durante cada espera.
old_unread='''        unread_now=set(unread_rows); old=set(getattr(self,"_diagnostic_unread",set()) or set()); new_names=unread_now-old; cleared=old-unread_now\n'''
new_unread='''        unread_now=set(unread_rows); old=set(getattr(self,"_diagnostic_unread",set()) or set()); new_names=unread_now-old; cleared=old-unread_now\n        _unread_count=len(unread_now)\n        for _pn,_pd in list(self._diagnostic_pending.items()):\n            if isinstance(_pd,dict):\n                _pd["max_unread_during_wait"]=max(int(_pd.get("max_unread_during_wait") or 0),_unread_count)\n'''
if old_unread not in text: raise SystemExit('unread state line not found')
text=text.replace(old_unread,new_unread,1)

# 4) Ao responder, grava junto os dados que explicam a demora.
old_response='''                            self._diagnostic_log("response",client=name,response_seconds=total,total_wait_seconds=total,until_open_seconds=until_open,after_open_seconds=after_open,received_ts=received,opened_ts=opened,response_ts=now,source=str(p.get("source") or ""))\n'''
new_response='''                            self._diagnostic_log("response",client=name,response_seconds=total,total_wait_seconds=total,until_open_seconds=until_open,after_open_seconds=after_open,received_ts=received,opened_ts=opened,response_ts=now,source=str(p.get("source") or ""),interruptions=int(p.get("interruptions") or 0),other_chat_opens=int(p.get("other_chat_opens") or 0),other_chats=list(p.get("other_chats") or [])[-20:],max_unread_during_wait=int(p.get("max_unread_during_wait") or 0),calls_during_wait=int(p.get("calls_during_wait") or 0),call_seconds_during_wait=int(p.get("call_seconds_during_wait") or 0))\n'''
if old_response not in text: raise SystemExit('response log line not found')
text=text.replace(old_response,new_response,1)

# 5) Se um nome for aprendido como grupo, remove qualquer pendência corrente dele.
old_learn='''        if learned:\n            self._diagnostic_groups=groups; self._diagnostic_groups_save(groups)\n\n        changed_chat='''
new_learn='''        if learned:\n            self._diagnostic_groups=groups; self._diagnostic_groups_save(groups)\n            for _g in list(groups):\n                self._diagnostic_pending.pop(_g,None)\n\n        changed_chat='''
if old_learn not in text: raise SystemExit('group learned block not found')
text=text.replace(old_learn,new_learn,1)

# 6) Acrescenta uma camada de interpretação sem substituir o resumo já existente.
anchor='    def _diagnostic_show_dialog(self):\n'
if anchor not in text: raise SystemExit('diagnostic dialog anchor not found')
helper=r'''    def _diagnostic_enhanced_text(self,rows):
        import datetime,time
        base=self._diagnostic_summary_text(rows)
        today=datetime.date.today().isoformat()
        day=[x for x in rows if isinstance(x,dict) and str(x.get("time") or "").startswith(today)]
        groups=set(self._diagnostic_groups_load())
        now=time.time()

        def fmt(sec):
            try: sec=max(0,int(sec or 0))
            except Exception: sec=0
            h=sec//3600; m=(sec%3600)//60; s=sec%60
            if h:return f"{h}h {m:02d}m"
            if m:return f"{m}m {s:02d}s"
            return f"{s}s"

        # Quem está esperando neste exato momento.
        waiting=[]
        for name,p in list(getattr(self,"_diagnostic_pending",{}).items()):
            if name in groups or not isinstance(p,dict): continue
            recv=float(p.get("received_ts") or now)
            opened=float(p.get("opened_ts") or 0)
            wait=max(0,int(now-recv))
            waiting.append((wait,str(name),p,opened))
        waiting.sort(reverse=True,key=lambda z:z[0])
        if waiting:
            lines=[]
            for i,(wait,name,p,opened) in enumerate(waiting[:10],1):
                if opened:
                    stage=f"abriu após {fmt(max(0,opened-float(p.get('received_ts') or opened)))}"
                    intr=int(p.get("interruptions") or 0)
                    if intr: stage+=f" • interrompido {intr}x"
                else:
                    stage="ainda não abriu"
                peak=int(p.get("max_unread_during_wait") or 0)
                if peak: stage+=f" • pico {peak} não lidos"
                lines.append(f"{i}. {name} — {fmt(wait)} • {stage}")
            if len(waiting)>10: lines.append(f"... e mais {len(waiting)-10} contato(s) aguardando")
            waiting_text="\n".join(lines)
        else:
            waiting_text="Nenhum contato pendente detectado neste momento."

        # Interrupções do dia.
        interrupted=[x for x in day if x.get("event")=="attendance_interrupted"]
        interrupted_clients=sorted(set(str(x.get("client") or "") for x in interrupted if x.get("client")))
        interruption_text=(f"{len(interrupted)} interrupção(ões) em {len(interrupted_clients)} contato(s)." if interrupted else "Nenhuma interrupção registrada nesta versão ainda.")
        if interrupted_clients:
            interruption_text += "\nMais interrompidos: "
            counts={}
            for x in interrupted:
                n=str(x.get("client") or ""); counts[n]=counts.get(n,0)+1
            top=sorted(counts.items(),key=lambda kv:(-kv[1],kv[0].lower()))[:5]
            interruption_text += " • ".join(f"{n} ({c}x)" for n,c in top)

        # Explica as maiores esperas concluídas do dia.
        responses=[x for x in day if x.get("event")=="response"]
        responses.sort(key=lambda x:int(x.get("total_wait_seconds") or x.get("response_seconds") or 0),reverse=True)
        why=[]
        for i,x in enumerate(responses[:5],1):
            total=int(x.get("total_wait_seconds") or x.get("response_seconds") or 0)
            if total<=0: continue
            name=str(x.get("client") or "Contato")
            until=int(x.get("until_open_seconds") or 0); after=int(x.get("after_open_seconds") or 0)
            intr=int(x.get("interruptions") or 0); opens=int(x.get("other_chat_opens") or 0); peak=int(x.get("max_unread_during_wait") or 0)
            calls=int(x.get("calls_during_wait") or 0); callsecs=int(x.get("call_seconds_during_wait") or 0)
            parts=[f"até abrir {fmt(until)}",f"depois de abrir {fmt(after)}"]
            if intr:parts.append(f"interrompido {intr}x")
            if opens:parts.append(f"{opens} outra(s) conversa(s) aberta(s)")
            if peak:parts.append(f"pico {peak} não lidos")
            if calls:parts.append(f"{calls} ligação(ões) / {fmt(callsecs)}")
            why.append(f"{i}. {name} — {fmt(total)}\n   " + " • ".join(parts))
        why_text="\n".join(why) if why else "As novas explicações começam a aparecer conforme você usa esta versão."

        return (base + "\n\n"
                "AGUARDANDO SUA RESPOSTA AGORA\n" + waiting_text + "\n\n"
                "ATENDIMENTOS INTERROMPIDOS\n" + interruption_text + "\n\n"
                "POR QUE OS MAIORES TEMPOS ACONTECERAM\n" + why_text)

    def _diagnostic_waiting_snapshot(self):
        import time
        now=time.time(); groups=set(self._diagnostic_groups_load()); out=[]
        for name,p in list(getattr(self,"_diagnostic_pending",{}).items()):
            if name in groups or not isinstance(p,dict): continue
            row={"client":str(name),"waiting_seconds":max(0,int(now-float(p.get("received_ts") or now))),"received_ts":p.get("received_ts"),"opened_ts":p.get("opened_ts"),"source":p.get("source"),"interruptions":int(p.get("interruptions") or 0),"other_chat_opens":int(p.get("other_chat_opens") or 0),"max_unread_during_wait":int(p.get("max_unread_during_wait") or 0)}
            out.append(row)
        return sorted(out,key=lambda x:-int(x.get("waiting_seconds") or 0))

'''
text=text.replace(anchor,helper+anchor,1)

# 7) Diagnóstico visual agora usa a interpretação nova e se atualiza sozinho.
new_diag=r'''    def _diagnostic_show_dialog(self):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QTextEdit,QPushButton,QFileDialog,QMessageBox,QLabel
        import datetime
        dlg=QDialog(self); dlg.setWindowTitle("📊 Diagnóstico do atendimento"); dlg.resize(820,680)
        lay=QVBoxLayout(dlg)
        info=QLabel(""); info.setStyleSheet("font-weight:700;"); lay.addWidget(info)
        txt=QTextEdit(); txt.setReadOnly(True); txt.setStyleSheet("font-size:12px;font-weight:600;"); lay.addWidget(txt,1)

        def filtered_rows():
            groups=set(self._diagnostic_groups_load())
            rows=self._diagnostic_read()
            return [x for x in rows if not (isinstance(x,dict) and str(x.get("client") or "").strip() in groups)]

        def refresh():
            groups=set(self._diagnostic_groups_load())
            pending=len(self._diagnostic_waiting_snapshot())
            info.setText(f"Contatos individuais • {len(groups)} grupo(s) ignorado(s) • {pending} aguardando resposta agora")
            txt.setPlainText(self._diagnostic_enhanced_text(filtered_rows()))

        refresh()
        live=QTimer(dlg); live.setInterval(3000); live.timeout.connect(refresh); live.start()
        bar=QHBoxLayout(); refresh_btn=QPushButton("↻ Atualizar"); export=QPushButton("📤 Exportar diagnóstico"); close=QPushButton("Fechar")
        bar.addWidget(refresh_btn); bar.addWidget(export); bar.addStretch(1); bar.addWidget(close); lay.addLayout(bar)
        refresh_btn.clicked.connect(refresh)

        def do_export():
            fn=f"ALIYVO_diagnostico_{datetime.date.today().isoformat()}.json"
            path,_=QFileDialog.getSaveFileName(dlg,"Exportar diagnóstico",fn,"Arquivo JSON (*.json)")
            if not path:return
            try:
                current=filtered_rows(); ignored=sorted(self._diagnostic_groups_load(),key=str.lower)
                payload={"aliyvo_version":ALIYVO_VERSION,"exported_at":datetime.datetime.now().isoformat(timespec="seconds"),"mode":"contatos_individuais","ignored_groups":ignored,"summary":self._diagnostic_enhanced_text(current),"waiting_now":self._diagnostic_waiting_snapshot(),"events":current,"attendance_snapshot":getattr(self,"_attendance_data",{})}
                Path(path).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
                QMessageBox.information(dlg,"Diagnóstico","Arquivo exportado com esperas, interrupções e contatos ainda aguardando.")
            except Exception as e: QMessageBox.warning(dlg,"Diagnóstico",f"Não consegui exportar: {e}")
        export.clicked.connect(do_export); close.clicked.connect(dlg.accept); dlg.exec()
'''
text=replace_method(text,'MainWindow','_diagnostic_show_dialog',new_diag)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched waiting reasons and interruptions',version)
