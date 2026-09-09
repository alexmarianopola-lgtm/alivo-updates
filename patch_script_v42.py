from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v42.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)


def _class_method(src,class_name,method_name):
    tree=ast.parse(src)
    cls=next((n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==class_name),None)
    if cls is None: raise SystemExit(f'class {class_name} not found')
    target=next((n for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==method_name),None)
    if target is None: raise SystemExit(f'method {class_name}.{method_name} not found')
    return target


def method_source(src,class_name,method_name):
    target=_class_method(src,class_name,method_name)
    lines=src.splitlines(keepends=True)
    return ''.join(lines[target.lineno-1:target.end_lineno])


def replace_method(src,class_name,method_name,new_code):
    target=_class_method(src,class_name,method_name)
    lines=src.splitlines(keepends=True)
    start=sum(len(x) for x in lines[:target.lineno-1]); end=sum(len(x) for x in lines[:target.end_lineno])
    if not new_code.endswith('\n'): new_code+='\n'
    return src[:start]+new_code+src[end:]


def prefix_method(src,class_name,method_name,code):
    target=_class_method(src,class_name,method_name)
    if not target.body: raise SystemExit(f'empty method {method_name}')
    lines=src.splitlines(keepends=True)
    pos=sum(len(x) for x in lines[:target.body[0].lineno-1])
    if not code.endswith('\n'):code+='\n'
    return src[:pos]+code+src[pos:]


# Horario real informado pelo usuario: segunda a sexta, 07:50-12:08 e 13:30-18:00.
# O tempo corrido continua preservado nos eventos; KPIs passam a usar somente os segundos uteis.
anchor='    def _diagnostic_is_closing_message(self,text):\n'
if anchor not in text:
    anchor='    def _diagnostic_show_dialog(self):\n'
if anchor not in text: raise SystemExit('worktime helper anchor not found')
helpers=r'''    def _work_schedule_text(self):
        return "Seg–Sex • 07:50–12:08 e 13:30–18:00"

    def _work_is_open(self,when=None):
        import datetime,time
        try:
            if when is None:dt=datetime.datetime.now()
            elif isinstance(when,datetime.datetime):dt=when
            else:dt=datetime.datetime.fromtimestamp(float(when))
        except Exception:return False
        if dt.weekday()>=5:return False
        mins=dt.hour*60+dt.minute+(dt.second/60.0)
        return (470<=mins<728) or (810<=mins<1080)

    def _work_seconds_between(self,start_ts,end_ts):
        import datetime
        try:
            start=float(start_ts or 0); end=float(end_ts or 0)
        except Exception:return 0
        if start<=0 or end<=start:return 0
        try:
            a=datetime.datetime.fromtimestamp(start); b=datetime.datetime.fromtimestamp(end)
        except Exception:return max(0,int(end-start))
        total=0.0
        day=a.date(); last=b.date()
        while day<=last:
            if day.weekday()<5:
                for sh,sm,eh,em in ((7,50,12,8),(13,30,18,0)):
                    ws=datetime.datetime.combine(day,datetime.time(sh,sm))
                    we=datetime.datetime.combine(day,datetime.time(eh,em))
                    lo=max(a,ws); hi=min(b,we)
                    if hi>lo:total+=(hi-lo).total_seconds()
            day+=datetime.timedelta(days=1)
        return max(0,int(total))

    def _work_next_open_text(self,when=None):
        import datetime
        try:
            dt=datetime.datetime.now() if when is None else (when if isinstance(when,datetime.datetime) else datetime.datetime.fromtimestamp(float(when)))
        except Exception:return ""
        if self._work_is_open(dt):return "em expediente"
        for add in range(0,8):
            d=dt.date()+datetime.timedelta(days=add)
            if d.weekday()>=5:continue
            morning=datetime.datetime.combine(d,datetime.time(7,50))
            afternoon=datetime.datetime.combine(d,datetime.time(13,30))
            if morning>dt:return morning.strftime("%d/%m %H:%M")
            if afternoon>dt:return afternoon.strftime("%d/%m %H:%M")
        return "próximo expediente"

    def _diagnostic_rows_worktime(self,rows):
        out=[]
        for original in (rows or []):
            if not isinstance(original,dict):
                out.append(original);continue
            x=dict(original)
            if x.get("event")=="response":
                try:recv=float(x.get("received_ts") or 0); resp=float(x.get("response_ts") or x.get("ts") or 0)
                except Exception:recv=resp=0
                if recv>0 and resp>=recv:
                    raw=max(0,int(resp-recv)); useful=self._work_seconds_between(recv,resp)
                    x["raw_total_wait_seconds"]=raw
                    x["work_wait_seconds"]=useful
                    x["response_seconds"]=useful
                    x["total_wait_seconds"]=useful
                    try:opened=float(x.get("opened_ts") or 0)
                    except Exception:opened=0
                    if opened>0:
                        opened=max(recv,min(opened,resp))
                        x["raw_until_open_seconds"]=max(0,int(opened-recv))
                        x["raw_after_open_seconds"]=max(0,int(resp-opened))
                        x["until_open_seconds"]=self._work_seconds_between(recv,opened)
                        x["after_open_seconds"]=self._work_seconds_between(opened,resp)
            out.append(x)
        return out

'''
text=text.replace(anchor,helpers+anchor,1)

# Toda estatistica baseada em respostas passa a receber uma copia normalizada em tempo util.
for method in ('_diagnostic_summary_text','_diagnostic_enhanced_text','_diagnostic_daily_summary_text','_diagnostic_contact_history_text'):
    try:
        text=prefix_method(text,'MainWindow',method,'        rows=self._diagnostic_rows_worktime(rows)')
    except SystemExit:
        raise

# A lista de quem aguarda agora usa tempo util e preserva tambem o tempo corrido.
new_waiting=r'''    def _diagnostic_waiting_snapshot(self):
        import time
        now=time.time(); groups=set(self._diagnostic_groups_load()); out=[]
        for name,p in list(getattr(self,"_diagnostic_pending",{}).items()):
            if name in groups or not isinstance(p,dict):continue
            try:received=float(p.get("received_ts") or now)
            except Exception:received=now
            raw=max(0,int(now-received)); useful=self._work_seconds_between(received,now)
            row={"client":str(name),"waiting_seconds":useful,"work_waiting_seconds":useful,"raw_waiting_seconds":raw,"received_ts":p.get("received_ts"),"opened_ts":p.get("opened_ts"),"source":p.get("source"),"interruptions":int(p.get("interruptions") or 0),"other_chat_opens":int(p.get("other_chat_opens") or 0),"max_unread_during_wait":int(p.get("max_unread_during_wait") or 0),"work_clock_running":bool(self._work_is_open(now)),"next_work_open":self._work_next_open_text(now)}
            out.append(row)
        return sorted(out,key=lambda x:-int(x.get("waiting_seconds") or 0))
'''
text=replace_method(text,'MainWindow','_diagnostic_waiting_snapshot',new_waiting)

# Ajusta a exibicao em tempo real do Diagnostico: espera e abertura em tempo util.
ms=method_source(text,'MainWindow','_diagnostic_enhanced_text')
ms=ms.replace('wait=max(0,int(now-recv))','wait=self._work_seconds_between(recv,now)')
ms=ms.replace("stage=f\"abriu após {fmt(max(0,opened-float(p.get('received_ts') or opened)))}\"","stage=f\"abriu após {fmt(self._work_seconds_between(float(p.get('received_ts') or opened),opened))} úteis\"")
ms=ms.replace('stage="ainda não abriu"','stage="ainda não abriu"')
ms=ms.replace('lines.append(f"{i}. {name} — {fmt(wait)} • {stage}")','''
                _paused="" if self._work_is_open(now) else f" • relógio pausado até {self._work_next_open_text(now)}"
                lines.append(f"{i}. {name} — {fmt(wait)} úteis • {stage}{_paused}")''')
# Acrescenta a regra de horario ao topo interpretado.
old='return (base + "\\n\\n"'
if old in ms:
    ms=ms.replace(old,'return (base + "\\n\\nTEMPO ÚTIL DO RELATÓRIO\\n" + self._work_schedule_text() + " • almoço/noite/fim de semana não contam\\n\\n"',1)
text=replace_method(text,'MainWindow','_diagnostic_enhanced_text',ms)

# Panorama estruturado preserva tempo corrido, mas expõe tempo útil como principal.
ms=method_source(text,'MainWindow','_diagnostic_whatsapp_overview_payload')
ms=ms.replace('"waiting_visible_seconds":max(0,int(now-float(d.get("first_seen_ts") or now)))','"waiting_visible_seconds":self._work_seconds_between(float(d.get("first_seen_ts") or now),now),"raw_waiting_visible_seconds":max(0,int(now-float(d.get("first_seen_ts") or now))),"work_clock_running":bool(self._work_is_open(now))')
text=replace_method(text,'MainWindow','_diagnostic_whatsapp_overview_payload',ms)

# Labels dos relatorios deixam explicito que as medias/rankings sao em tempo util.
for method in ('_diagnostic_summary_text','_diagnostic_daily_summary_text','_diagnostic_contact_history_text'):
    ms=method_source(text,'MainWindow',method)
    ms=ms.replace('Tempo médio de resposta medido:', 'Tempo médio de resposta medido (útil):')
    ms=ms.replace('Tempo médio de resposta:', 'Tempo médio de resposta (útil):')
    ms=ms.replace('Acima de 5 min:', 'Acima de 5 min úteis:')
    ms=ms.replace(' • acima de 15 min:', ' • acima de 15 min úteis:')
    ms=ms.replace('Respostas medidas:', 'Respostas medidas (tempo útil):')
    text=replace_method(text,'MainWindow',method,ms)

# Contexto enviado para a IA usa os mesmos tempos uteis do Diagnostico.
ms=method_source(text,'MainWindow','_ai_build_context')
anchor_rows='        active=str(getattr(self,"_diagnostic_active_name","") or "").strip()\n'
if anchor_rows not in ms: raise SystemExit('AI context active anchor not found')
ms=ms.replace(anchor_rows,'        rows=self._diagnostic_rows_worktime(rows)\n'+anchor_rows,1)
anchor_goal='            "generated_at":datetime.datetime.now().isoformat(timespec="seconds"),\n'
if anchor_goal in ms:
    ms=ms.replace(anchor_goal,anchor_goal+'            "work_schedule":{"days":"segunda a sexta","morning":"07:50-12:08","afternoon":"13:30-18:00","kpi_rule":"usar tempo útil; almoço, noite e fim de semana não contam"},\n',1)
text=replace_method(text,'MainWindow','_ai_build_context',ms)

# A IA recebe uma instrucao explicita para nao chamar almoço/noite de atraso comercial.
ms=method_source(text,'MainWindow','_ai_prompt')
marker='        if mode=="conversation":\n'
if marker not in ms: raise SystemExit('AI prompt mode anchor not found')
ms=ms.replace(marker,'        base += " O expediente é segunda a sexta, 07:50–12:08 e 13:30–18:00. Avalie atrasos e esperas pelo tempo útil; almoço, noite e fim de semana não contam como demora de atendimento."\n'+marker,1)
text=replace_method(text,'MainWindow','_ai_prompt',ms)

# Analise automatica nao consome API fora do expediente. Analise manual continua liberada a qualquer hora.
new_tick=r'''    def _ai_observer_tick(self):
        cfg=self._ai_config_load()
        if not bool(cfg.get("enabled")) or not self._ai_api_key():return
        if not self._work_is_open():return
        self._ai_observer_analyze("auto",True)
'''
text=replace_method(text,'MainWindow','_ai_observer_tick',new_tick)

# Mostra a regra na configuracao da IA para o usuario saber exatamente quando ela roda.
ms=method_source(text,'MainWindow','_ai_settings_dialog')
old='note=QLabel("Recomendado: GPT-5.6 Luna para observação contínua por ter custo bem menor. O uso da API é cobrado separadamente do ChatGPT Plus.")'
new='note=QLabel("Recomendado: GPT-5.6 Luna para observação contínua por ter custo bem menor. Automático somente no expediente: Seg–Sex 07:50–12:08 e 13:30–18:00. O uso da API é cobrado separadamente do ChatGPT Plus.")'
if old in ms:ms=ms.replace(old,new,1)
text=replace_method(text,'MainWindow','_ai_settings_dialog',ms)

# Backup diario informa a regra aplicada, facilitando auditoria posterior dos 3 dias.
ms=method_source(text,'MainWindow','_diagnostic_daily_backup')
needle='                "automatic_backup":True,\n'
if needle in ms:
    ms=ms.replace(needle,needle+'                "work_schedule":{"days":"segunda a sexta","morning":"07:50-12:08","afternoon":"13:30-18:00","metric":"business_seconds"},\n',1)
text=replace_method(text,'MainWindow','_diagnostic_daily_backup',ms)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched business-hours diagnostics and AI schedule',version)
