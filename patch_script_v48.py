from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v48.json').read_text(encoding='utf-8'))
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

# Aprendizado v2: reconstroi automaticamente o arquivo v1 para eliminar
# contagens infladas por snapshots/varreduras repetidas do diagnostico.
text=replace_method(text,'MainWindow','_ai_learning_empty',r'''    def _ai_learning_empty(self):
        return {"version":2,"last_processed_ts":0.0,"patterns":{},"seller_phrases":{},"seen_cases":{},"seen_phrase_cases":{},"updated_at":""}
''')

text=replace_method(text,'MainWindow','_ai_learning_load',r'''    def _ai_learning_load(self):
        data=self._ai_learning_empty()
        try:
            p=self._ai_learning_path()
            if p.exists():
                d=json.loads(p.read_text(encoding="utf-8"))
                # Mudanca de metodologia: v1 tinha contagem por linha tecnica.
                # Nao reaproveitamos os totais antigos; o refresh reprocessa o diagnostico.
                if isinstance(d,dict) and int(d.get("version") or 0)==2:
                    data.update(d)
        except Exception:pass
        if not isinstance(data.get("patterns"),dict):data["patterns"]={}
        if not isinstance(data.get("seller_phrases"),dict):data["seller_phrases"]={}
        if not isinstance(data.get("seen_cases"),dict):data["seen_cases"]={}
        if not isinstance(data.get("seen_phrase_cases"),dict):data["seen_phrase_cases"]={}
        return data
''')

text=replace_method(text,'MainWindow','_ai_learning_categories',r'''    def _ai_learning_categories(self,row):
        if not isinstance(row,dict):return []
        raw=" ".join(str(row.get(k) or "") for k in ("text","snippet","row_text","tool","event","content_type"))
        s=self._ai_learning_norm(raw)
        event=self._ai_learning_norm(row.get("event"))
        tool=self._ai_learning_norm(row.get("tool"))
        found=[]
        def add(key,label,weight):
            if not any(x[0]==key for x in found):found.append((key,label,float(weight)))
        if any(x in s for x in ("preco","valor","quanto","cotacao","orcamento","oferecendo")):
            add("consulta_preco","Consulta de preço/orçamento",4.0)
        if any(x in s for x in ("pre-venda","pre venda","prevenda","separar","separa pra","reservar","reserva","deixa uma","deixe uma")):
            add("pre_venda","Separação / pré-venda / reserva",3.6)
        if any(x in s for x in ("desconto","melhor preco","consegue fazer","consigo fazer","oferecendo","fechar por","chegar em","negocia")):
            add("negociacao","Negociação de preço",2.8)
        if tool=="prazo" or any(x in s for x in ("prazo","parcela","boleto","30/60","20/40","28/56","dias para pagar")):
            add("prazo_pagamento","Consulta de prazo/condição",3.5)
        if any(x in s for x in ("tem em estoque","tem dispon","disponivel","disponibilidade","tem essa","tem esse","consegue uma","consegue duas")):
            add("estoque","Disponibilidade / estoque",3.1)
        if any(x in s for x in ("codigo","cod ","referencia","original","aplica","aplicacao")):
            add("codigo_aplicacao","Código / referência / aplicação",3.4)
        if tool in ("plate","placa","chassi") or any(x in s for x in ("placa","chassi")):
            add("placa_chassi","Consulta por placa/chassi",3.0)
        if tool in ("lens","image","imagem") or "busca por imagem" in s:
            add("busca_imagem","Busca por imagem",3.2)
        # Ligações: conta somente o evento final da chamada, não o overlay vivo/inicio.
        if event=="call":
            add("ligacoes","Ligações com clientes",1.0)
        # Espera: só quando existe uma resposta efetivamente medida.
        try:
            measured=(row.get("response_seconds") not in (None,"") or row.get("response_ts") not in (None,""))
            wait=float(row.get("response_seconds") or row.get("total_wait_seconds") or 0)
            if measured and 300<=wait<=172800:add("espera_5min","Atendimento com espera acima de 5 min úteis",0.8)
        except Exception:pass
        # Interrupção: prioriza atendimentos que chegaram a uma resposta ou evento explícito.
        try:
            measured=(row.get("response_seconds") not in (None,"") or row.get("response_ts") not in (None,""))
            explicit=(event in ("attendance_interrupted","interrupted_attendance","attendance_resumed"))
            if (measured and int(row.get("interruptions") or 0)>0) or explicit:
                add("interrupcoes","Atendimentos interrompidos",0.7)
        except Exception:pass
        ctype=self._ai_learning_norm(row.get("content_type"))
        if ctype in ("audio","voice","ptt"):
            add("audio_recebido","Áudios recebidos no WhatsApp",1.6)
        return found
''')

# Insere gerador de chave de caso antes do refresh.
anchor='    def _ai_learning_refresh(self):\n'
if anchor not in text: raise SystemExit('_ai_learning_refresh anchor missing')
helper=r'''    def _ai_learning_case_key(self,row,key):
        import datetime,hashlib
        client=self._ai_learning_norm(row.get("client") or "sem_cliente")
        stamp=str(row.get("time") or "")
        day=stamp[:10] if len(stamp)>=10 else ""
        event=self._ai_learning_norm(row.get("event"))
        example=self._ai_learning_norm(row.get("text") or row.get("snippet") or row.get("row_text") or "")[:120]
        # Casos de espera/interrupção possuem timestamps próprios do atendimento.
        if key in ("espera_5min","interrupcoes"):
            a=str(row.get("received_ts") or row.get("opened_ts") or "")
            b=str(row.get("response_ts") or "")
            if a or b:subject=a+"|"+b
            else:
                try:subject="bucket:"+str(int(float(row.get("ts") or 0)//600))
                except Exception:subject=stamp[:16]
        elif key=="ligacoes":
            subject="|".join((stamp[:16],str(row.get("duration_seconds") or ""),self._ai_learning_norm(row.get("direction"))))
        elif example:
            # Mesmo texto/caso repetido pelo scanner para o mesmo cliente no mesmo dia = 1 caso.
            subject=day+"|"+example
        else:
            try:subject="bucket:"+str(int(float(row.get("ts") or 0)//600))+"|"+event
            except Exception:subject=stamp[:16]+"|"+event
        raw="|".join((key,client,subject))
        return hashlib.sha1(raw.encode("utf-8","ignore")).hexdigest()

    def _ai_learning_phrase_case_key(self,row,norm):
        import hashlib
        client=self._ai_learning_norm(row.get("client") or "sem_cliente")
        stamp=str(row.get("time") or "")
        day=stamp[:10] if len(stamp)>=10 else ""
        raw="|".join((client,day,norm))
        return hashlib.sha1(raw.encode("utf-8","ignore")).hexdigest()

'''
text=text.replace(anchor,helper+anchor,1)

text=replace_method(text,'MainWindow','_ai_learning_refresh',r'''    def _ai_learning_refresh(self):
        data=self._ai_learning_load();last=float(data.get("last_processed_ts") or 0);rows=[]
        try:rows=list(self._diagnostic_read() or [])
        except Exception:rows=[]
        fresh=[]
        for row in rows:
            if not isinstance(row,dict):continue
            try:ts=float(row.get("ts") or 0)
            except Exception:ts=0
            if ts>last:fresh.append((ts,row))
        if not fresh:return data
        fresh.sort(key=lambda x:x[0]);max_ts=last
        seen=dict(data.get("seen_cases") or {});seen_phrases=dict(data.get("seen_phrase_cases") or {})
        for ts,row in fresh:
            max_ts=max(max_ts,ts)
            client=str(row.get("client") or "").strip()
            stamp=str(row.get("time") or "")[:19]
            example=str(row.get("text") or row.get("snippet") or row.get("row_text") or "").strip()[:180]
            for key,label,weight in self._ai_learning_categories(row):
                case=self._ai_learning_case_key(row,key)
                if case in seen:continue
                seen[case]=ts
                rec=data["patterns"].get(key)
                if not isinstance(rec,dict):
                    rec={"label":label,"count":0,"weight":weight,"first_seen":stamp,"last_seen":stamp,"clients":[],"examples":[]}
                rec["label"]=label;rec["weight"]=weight;rec["count"]=int(rec.get("count") or 0)+1
                if not rec.get("first_seen"):rec["first_seen"]=stamp
                rec["last_seen"]=stamp
                clients=list(rec.get("clients") or [])
                if client and client not in clients:clients.append(client)
                rec["clients"]=clients[-80:]
                examples=list(rec.get("examples") or [])
                if example and example not in examples:examples.append(example)
                rec["examples"]=examples[-5:]
                data["patterns"][key]=rec
            # Frases: mesma frase para o mesmo cliente no mesmo dia conta uma vez,
            # evitando que varreduras técnicas inflem o total.
            ev=self._ai_learning_norm(row.get("event"));direction=self._ai_learning_norm(row.get("direction"))
            msg=str(row.get("text") or "").strip()
            seller=("seller" in ev or direction in ("out","outgoing","seller","me","mine"))
            if seller and 1<=len(msg)<=90:
                norm=self._ai_learning_norm(msg)
                if norm:
                    pk=self._ai_learning_phrase_case_key(row,norm)
                    if pk not in seen_phrases:
                        seen_phrases[pk]=ts
                        rec=data["seller_phrases"].get(norm) or {"text":msg,"count":0,"last_seen":stamp}
                        rec["text"]=msg;rec["count"]=int(rec.get("count") or 0)+1;rec["last_seen"]=stamp
                        data["seller_phrases"][norm]=rec
        phrases=sorted(data["seller_phrases"].items(),key=lambda kv:(int((kv[1] or {}).get("count") or 0),str((kv[1] or {}).get("last_seen") or "")),reverse=True)[:100]
        data["seller_phrases"]={k:v for k,v in phrases}
        # Mantém as chaves recentes para deduplicação sem crescimento ilimitado.
        data["seen_cases"]={k:v for k,v in sorted(seen.items(),key=lambda kv:float(kv[1] or 0),reverse=True)[:12000]}
        data["seen_phrase_cases"]={k:v for k,v in sorted(seen_phrases.items(),key=lambda kv:float(kv[1] or 0),reverse=True)[:8000]}
        data["last_processed_ts"]=max_ts
        self._ai_learning_save(data)
        return data
''')

text=replace_method(text,'MainWindow','_ai_learning_summary_payload',r'''    def _ai_learning_summary_payload(self,refresh=True):
        data=self._ai_learning_refresh() if refresh else self._ai_learning_load()
        out=[]
        for key,rec in (data.get("patterns") or {}).items():
            if not isinstance(rec,dict):continue
            count=int(rec.get("count") or 0);weight=float(rec.get("weight") or 1);clients=len(rec.get("clients") or [])
            conf="alta" if count>=10 and clients>=3 else ("média" if count>=4 and clients>=2 else "observando")
            # O ranking mede repetição + alcance entre clientes, sem deixar um contador enorme dominar sozinho.
            score=round(weight*((max(count,0)**0.5)*3.0 + clients*2.0),1)
            out.append({"key":key,"label":rec.get("label") or key,"count":count,"clients_count":clients,"confidence":conf,"automation_score":score,"last_seen":rec.get("last_seen") or "","examples":list(rec.get("examples") or [])[-2:]})
        out.sort(key=lambda x:(x["automation_score"],x["clients_count"],x["count"]),reverse=True)
        phrases=[]
        for rec in (data.get("seller_phrases") or {}).values():
            if isinstance(rec,dict) and int(rec.get("count") or 0)>=2:
                phrases.append({"text":str(rec.get("text") or "")[:90],"count":int(rec.get("count") or 0)})
        phrases.sort(key=lambda x:x["count"],reverse=True)
        return {"methodology":"unique_cases_v2","updated_at":data.get("updated_at") or "","patterns":out[:15],"top_seller_phrases":phrases[:10]}
''')

text=replace_method(text,'MainWindow','_ai_learning_text',r'''    def _ai_learning_text(self):
        learn=self._ai_learning_summary_payload(True);patterns=learn.get("patterns") or []
        if not patterns:return "A IA ainda está juntando evidências. Use o ALIYVO normalmente e ela começará a confirmar padrões."
        confirmed=[x for x in patterns if x.get("confidence") in ("alta","média")]
        observing=[x for x in patterns if x.get("confidence")=="observando"]
        lines=["APRENDIZADO ACUMULADO DA IA","Casos repetidos pelo scanner do diagnóstico são agrupados automaticamente.","", "PADRÕES CONFIRMADOS"]
        if confirmed:
            for x in confirmed[:10]:lines.append(f"• {x['label']}: {x['count']} caso(s) único(s) • {x['clients_count']} cliente(s) • confiança {x['confidence']}")
        else:lines.append("• Ainda não há padrão com evidência suficiente.")
        lines += ["", "RANKING PARA FUTURA AUTOMAÇÃO"]
        for i,x in enumerate(patterns[:8],1):lines.append(f"{i}. {x['label']} — {x['count']} caso(s) • {x['clients_count']} cliente(s) • índice {x['automation_score']}")
        if observing:
            lines += ["", "AINDA OBSERVANDO"]
            for x in observing[:6]:lines.append(f"• {x['label']}: {x['count']} caso(s) em {x['clients_count']} cliente(s)")
        phrases=learn.get("top_seller_phrases") or []
        if phrases:
            lines += ["", "FRASES CURTAS QUE VOCÊ REPETE"]
            for x in phrases[:7]:lines.append(f"• {x['text']} — {x['count']} cliente-dia(s)")
        lines += ["", "Importante: contagem = casos únicos inferidos do diagnóstico, não linhas técnicas. Prioridade de automação = sugestão calculada; não significa que a automação já existe."]
        return "\n".join(lines)
''')

# Backup passa a registrar a metodologia de casos únicos via payload já existente.
# Nenhuma mudança em WebView2, WhatsApp, Prazos, chamadas ou dados de usuário.
ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched AI learning unique-case dedup v2',version)
