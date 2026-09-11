from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v50.json').read_text(encoding='utf-8'))
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

# ---------------------------------------------------------------------
# IA Observadora 3.1 - desempenho dos perfis comerciais
# - tela abre usando cache local
# - reconstrução roda em thread e não bloqueia a interface
# - cálculo de todos os perfis/desfechos é feito em uma única passada
# - cache tem validade curta e pode ser atualizado manualmente
# ---------------------------------------------------------------------
anchor='    def _ai_client_profiles_payload(self):\n'
if anchor not in text: raise SystemExit('_ai_client_profiles_payload anchor missing')
helpers=r'''    def _ai_profiles_cache_path(self):
        return USER_DATA_DIR/"ia_perfis_clientes_cache.json"

    def _ai_profiles_cache_load(self):
        try:
            p=self._ai_profiles_cache_path()
            if not p.exists():return {"version":1,"built_at_ts":0.0,"profiles":{}}
            d=json.loads(p.read_text(encoding="utf-8"))
            if isinstance(d,dict) and isinstance(d.get("profiles"),dict):return d
        except Exception:pass
        return {"version":1,"built_at_ts":0.0,"profiles":{}}

    def _ai_profiles_cache_save(self,profiles):
        import time
        try:
            USER_DATA_DIR.mkdir(parents=True,exist_ok=True)
            payload={"version":1,"built_at_ts":time.time(),"profiles":profiles or {}}
            tmp=self._ai_profiles_cache_path().with_suffix(".tmp")
            tmp.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
            tmp.replace(self._ai_profiles_cache_path())
            self._ai_profiles_cache_generation=int(getattr(self,"_ai_profiles_cache_generation",0) or 0)+1
            return True
        except Exception:return False

    def _ai_client_profiles_rebuild_fast(self):
        import time
        rows=self._ai_unique_rows()
        data={};seen=set();pending={};outcome_seen=set()
        explicit_terms=("pode mandar","manda vir","pode enviar","pode faturar","pode separar","separa pra mim","separa para mim","fecha","fechado","vou ficar","manda pra mim","manda para mim","pode fechar")
        def profile(client,row):
            rec=data.get(client)
            if rec is None:
                rec={"client":client,"first_seen":str(row.get("time") or "")[:19],"last_seen":str(row.get("time") or "")[:19],"patterns":{},"interaction_cases":0,"calls":0,"audio":0,"wait_over_5m":0,"interruptions":0,"outcomes":{}}
                data[client]=rec
            rec["last_seen"]=str(row.get("time") or "")[:19]
            return rec
        def add_outcome(rec,key,label,client,ts,evidence):
            bucket=int(float(ts or 0)//900)
            ok=(self._ai_learning_norm(client),key,bucket,self._ai_learning_norm(evidence)[:80])
            if ok in outcome_seen:return
            outcome_seen.add(ok)
            o=rec["outcomes"].get(key) or {"key":key,"label":label,"count":0,"examples":[]}
            o["count"]+=1
            ex=str(evidence or "").strip()[:150]
            if ex and ex not in o["examples"]:o["examples"].append(ex)
            o["examples"]=o["examples"][-4:]
            rec["outcomes"][key]=o
        for ts,row in rows:
            client=str(row.get("client") or "").strip()
            if not client:continue
            rec=profile(client,row)
            # volume aproximado: um bloco de interação por cliente a cada 15 min
            ik=(self._ai_learning_norm(client),"interaction",int(ts//900))
            if ik not in seen:
                seen.add(ik);rec["interaction_cases"]+=1
            for key,label,weight in self._ai_learning_categories(row):
                ck=(self._ai_learning_norm(client),key,self._ai_learning_case_key(row,key))
                if ck in seen:continue
                seen.add(ck)
                if key=="espera_5min":rec["wait_over_5m"]+=1;continue
                if key=="interrupcoes":rec["interruptions"]+=1;continue
                if key=="ligacoes":rec["calls"]+=1;continue
                if key=="audio_recebido":rec["audio"]+=1;continue
                pr=rec["patterns"].get(key) or {"key":key,"label":label,"count":0,"weight":weight}
                pr["count"]+=1;rec["patterns"][key]=pr
            side=self._ai_row_side(row)
            msg=str(row.get("text") or row.get("snippet") or row.get("row_text") or "").strip()
            norm=self._ai_learning_norm(msg)
            if side=="customer":
                if msg and any(term in norm for term in explicit_terms):
                    add_outcome(rec,"sinal_fechamento","Sinal explícito de fechamento/pedido no texto do cliente",client,ts,msg)
                # Resolve oportunidades pendentes criadas por uma mensagem do vendedor.
                pend=list(pending.get(client) or [])
                keep=[]
                for pts,pairs in pend:
                    age=ts-pts
                    if age<0:continue
                    if age>4*3600:continue
                    for key,label in pairs:add_outcome(rec,key,label,client,pts,msg or "cliente respondeu")
                pending[client]=keep
            elif side=="seller":
                cats={x[0] for x in self._ai_learning_categories(row)}
                pairs=[]
                if "consulta_preco" in cats:pairs.append(("resposta_apos_preco","Cliente respondeu após preço/orçamento"))
                if "prazo_pagamento" in cats:pairs.append(("resposta_apos_prazo","Cliente respondeu após condição/prazo"))
                if "codigo_aplicacao" in cats:pairs.append(("resposta_apos_codigo","Cliente respondeu após código/aplicação"))
                if pairs:
                    pend=[x for x in (pending.get(client) or []) if ts-x[0]<=4*3600]
                    pend.append((ts,pairs));pending[client]=pend[-12:]
        # Finaliza estrutura compacta e ranking por cliente.
        for client,rec in data.items():
            pats=list(rec.get("patterns",{}).values())
            pats.sort(key=lambda x:(int(x.get("count") or 0)*float(x.get("weight") or 1),int(x.get("count") or 0)),reverse=True)
            rec["patterns"]=pats[:10]
            outs=list(rec.get("outcomes",{}).values())
            outs.sort(key=lambda x:int(x.get("count") or 0),reverse=True)
            rec["outcomes"]=outs[:6]
            rec["evidence_count"]=sum(int(x.get("count") or 0) for x in pats)+int(rec.get("calls") or 0)+int(rec.get("audio") or 0)
            rec["confidence"]="alta" if rec["evidence_count"]>=12 and rec["interaction_cases"]>=4 else ("média" if rec["evidence_count"]>=5 else "observando")
        return data

    def _ai_profiles_cache_refresh_sync(self,force=False):
        import time
        cache=self._ai_profiles_cache_load()
        age=time.time()-float(cache.get("built_at_ts") or 0)
        if not force and cache.get("profiles") and age<300:return cache.get("profiles") or {}
        profiles=self._ai_client_profiles_rebuild_fast()
        self._ai_profiles_cache_save(profiles)
        return profiles

    def _ai_profiles_cache_refresh_async(self,force=False):
        import threading,time
        if bool(getattr(self,"_ai_profiles_refresh_busy",False)):return
        cache=self._ai_profiles_cache_load();age=time.time()-float(cache.get("built_at_ts") or 0)
        if not force and cache.get("profiles") and age<300:return
        self._ai_profiles_refresh_busy=True
        def worker():
            try:self._ai_profiles_cache_refresh_sync(True)
            finally:self._ai_profiles_refresh_busy=False
        threading.Thread(target=worker,name="ALIYVO-PerfisIA",daemon=True).start()

'''
text=text.replace(anchor,helpers+anchor,1)

text=replace_method(text,'MainWindow','_ai_client_profiles_payload',r'''    def _ai_client_profiles_payload(self):
        # Leitura normal é instantânea: usa somente o cache.
        cache=self._ai_profiles_cache_load()
        profiles=cache.get("profiles") or {}
        # Mantém o cache fresco em segundo plano sem travar a interface.
        self._ai_profiles_cache_refresh_async(False)
        return profiles
''')

text=replace_method(text,'MainWindow','_ai_client_profile_payload',r'''    def _ai_client_profile_payload(self,client_name):
        name=str(client_name or "").strip()
        profiles=self._ai_client_profiles_payload() or {}
        return profiles.get(name) or {"client":name,"patterns":[],"outcomes":[],"confidence":"observando","interaction_cases":0,"calls":0,"audio":0,"wait_over_5m":0,"interruptions":0}
''')

text=replace_method(text,'MainWindow','_ai_client_profiles_dialog',r'''    def _ai_client_profiles_dialog(self,parent=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPlainTextEdit,QPushButton
        from PyQt6.QtCore import QTimer
        dlg=QDialog(parent or self);dlg.setWindowTitle("👤 Perfis comerciais por cliente");dlg.resize(900,720)
        lay=QVBoxLayout(dlg);row=QHBoxLayout();row.addWidget(QLabel("Cliente:"));combo=QComboBox();combo.setEditable(True);row.addWidget(combo,1);ai_btn=QPushButton("🤖 Estratégia IA");row.addWidget(ai_btn);lay.addLayout(row)
        txt=QPlainTextEdit();txt.setReadOnly(True);lay.addWidget(txt,1)
        status=QLabel("Carregando cache dos perfis…");lay.addWidget(status)
        bottom=QHBoxLayout();refresh=QPushButton("↻ Atualizar perfis");close=QPushButton("Fechar");bottom.addWidget(refresh);bottom.addStretch(1);bottom.addWidget(close);lay.addLayout(bottom)
        state={"generation":int(getattr(self,"_ai_profiles_cache_generation",0) or 0),"loaded":False,"selected":""}
        def load_cache(preserve=True):
            profiles=(self._ai_profiles_cache_load().get("profiles") or {})
            previous=str(combo.currentText() or "").strip() if preserve else ""
            names=sorted(profiles.keys(),key=lambda n:(int((profiles[n] or {}).get("evidence_count") or 0),int((profiles[n] or {}).get("interaction_cases") or 0)),reverse=True)
            combo.blockSignals(True);combo.clear();combo.addItems(names)
            if previous and previous in profiles:combo.setCurrentText(previous)
            combo.blockSignals(False)
            state["loaded"]=bool(names)
            if names:
                status.setText(f"{len(names)} perfil(is) em cache • atualização pesada roda em segundo plano.")
                render()
            else:
                txt.setPlainText("Montando os perfis pela primeira vez…\n\nA janela continua utilizável enquanto o ALIYVO processa o diagnóstico em segundo plano.")
                status.setText("Montando cache em segundo plano…")
        def render():
            name=str(combo.currentText() or "").strip()
            if not name:return
            profiles=(self._ai_profiles_cache_load().get("profiles") or {})
            p=profiles.get(name)
            if not p:
                txt.setPlainText("Perfil ainda não está no cache. Clique em Atualizar perfis.");return
            # Renderiza sem recalcular nenhum outro cliente.
            lines=[f"PERFIL COMERCIAL OBSERVADO — {p.get('client') or '-'}",f"Confiança: {p.get('confidence')} • interações aproximadas: {p.get('interaction_cases',0)}",""]
            lines.append("FATOS OBSERVADOS")
            pats=p.get("patterns") or []
            if pats:
                for x in pats[:8]:lines.append(f"• {x.get('label')}: {x.get('count',0)} caso(s)")
            else:lines.append("• Ainda há pouca evidência comercial.")
            lines.append(f"• Áudios recebidos: {p.get('audio',0)} • ligações: {p.get('calls',0)}")
            lines += ["","DESFECHOS OBSERVÁVEIS"]
            outs=p.get("outcomes") or []
            if outs:
                for x in outs[:6]:lines.append(f"• {x.get('label')}: {x.get('count',0)} caso(s)")
            else:lines.append("• Ainda não há desfecho com evidência suficiente.")
            lines += ["","GARGALOS DE ATENDIMENTO",f"• Espera acima de 5 min úteis: {p.get('wait_over_5m',0)} caso(s)",f"• Atendimento interrompido: {p.get('interruptions',0)} caso(s)","","SUGESTÕES BASEADAS NOS PADRÕES (não são fatos)"]
            keys={x.get("key"):int(x.get("count") or 0) for x in pats}
            sug=[]
            if keys.get("consulta_preco",0)>=2 and keys.get("prazo_pagamento",0)>=2:sug.append("Quando fizer sentido, pode valer responder preço + condição juntos para reduzir ida e volta.")
            if keys.get("codigo_aplicacao",0)>=2:sug.append("Deixar busca por código/original/aplicação pronta tende a economizar tempo com este cliente.")
            if keys.get("pre_venda",0)>=2:sug.append("Pré-venda/separação aparece repetidamente; um atalho específico pode ser útil.")
            if keys.get("negociacao",0)>=2:sug.append("Negociação aparece com frequência; pode valer chegar à conversa já com limite/margem disponível.")
            if int(p.get("audio") or 0)>=3:sug.append("Este cliente usa áudio com frequência; futura transcrição automática pode ajudar a IA a entender melhor os pedidos.")
            if not sug:sug.append("Continuar observando antes de criar uma estratégia específica.")
            for s in sug[:5]:lines.append("• "+s)
            lines += ["","Importante: o perfil usa somente evidências encontradas no diagnóstico local. 'Sinal de fechamento' não significa venda/faturamento confirmado."]
            txt.setPlainText("\n".join(lines))
        def ai_strategy():
            name=str(combo.currentText() or "").strip()
            if not name:return
            self._ai_profile_target=name;self._ai_observer_text_widget=txt;self._ai_observer_status_widget=status;self._ai_observer_analyze("client_profile",False)
        def force_refresh():
            status.setText("Atualizando perfis em segundo plano…");refresh.setEnabled(False);self._ai_profiles_cache_refresh_async(True)
        def poll():
            gen=int(getattr(self,"_ai_profiles_cache_generation",0) or 0)
            if gen!=state["generation"]:
                state["generation"]=gen;refresh.setEnabled(True);load_cache(True)
            elif not bool(getattr(self,"_ai_profiles_refresh_busy",False)):
                refresh.setEnabled(True)
        combo.currentTextChanged.connect(lambda _=None:render());refresh.clicked.connect(force_refresh);ai_btn.clicked.connect(ai_strategy);close.clicked.connect(dlg.accept)
        dlg.finished.connect(lambda _=0:self._ai_observer_dialog_closed(txt,status))
        timer=QTimer(dlg);timer.setInterval(600);timer.timeout.connect(poll);timer.start()
        load_cache(False);self._ai_profiles_cache_refresh_async(False);dlg.exec()
''')

# Ao atualizar o aprendizado, também agenda atualização dos perfis sem bloquear.
ms=None
try:
    tree=ast.parse(text);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='MainWindow')
    target=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_ai_learning_refresh')
    lines=text.splitlines(keepends=True);start=sum(len(x) for x in lines[:target.lineno-1]);end=sum(len(x) for x in lines[:target.end_lineno]);ms=text[start:end]
except Exception:ms=None
if ms and 'self._ai_profiles_cache_refresh_async' not in ms:
    old='        self._ai_learning_save(data)\n        return data\n'
    if old in ms:
        ms=ms.replace(old,'        self._ai_learning_save(data)\n        try:self._ai_profiles_cache_refresh_async(False)\n        except Exception:pass\n        return data\n',1)
        text=text[:start]+ms+text[end:]

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched async cached AI client profiles',version)
