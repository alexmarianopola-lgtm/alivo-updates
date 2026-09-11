from pathlib import Path
import sys,re,json
p=Path(sys.argv[1] if len(sys.argv)>1 else r'C:\temp\build\_app\main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v60.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# 1) Corrige exibicao do tempo no painel Hoje usando o campo atual waiting_seconds.
old="""        wait_items=[]
        for w in waiting[:8]:
            n=str(w.get('client') or 'Cliente')
            try:sec=float(w.get('business_wait_seconds') or w.get('wait_seconds') or w.get('total_wait_seconds') or 0)
            except Exception:sec=0
            wait_items.append(f'{n}  •  aguardando {int(sec//60)} min úteis')
"""
new="""        wait_items=[]
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
"""
if old not in text: raise SystemExit('bloco wait_items do painel Hoje nao encontrado')
text=text.replace(old,new,1)

# 2) Permite abrir editor de lembrete pre-preenchido, sem criar nada automaticamente.
old_sig='def _reminder_add(self,parent=None,refresh=None,force_client=None,context=None):'
new_sig='def _reminder_add(self,parent=None,refresh=None,force_client=None,context=None,prefill_text=None,prefill_due=None):'
if old_sig not in text: raise SystemExit('assinatura _reminder_add nao encontrada')
text=text.replace(old_sig,new_sig,1)
old_initial='initial=datetime.datetime.now()+datetime.timedelta(hours=1)'
new_initial='initial=datetime.datetime.fromtimestamp(float(prefill_due)) if prefill_due else (datetime.datetime.now()+datetime.timedelta(hours=1))'
if old_initial not in text: raise SystemExit('initial de _reminder_add nao encontrado')
text=text.replace(old_initial,new_initial,1)
old_text='textw=QLineEdit();textw.setPlaceholderText("Ex.: fechar pedido Antiqueira")'
new_text='textw=QLineEdit();textw.setPlaceholderText("Ex.: fechar pedido Antiqueira");\n        if prefill_text:textw.setText(str(prefill_text))'
if old_text not in text: raise SystemExit('campo textw de _reminder_add nao encontrado')
text=text.replace(old_text,new_text,1)

anchor='    def _ai_build_context(self,mode="observer"):\n'
if anchor not in text: raise SystemExit('_ai_build_context anchor missing')
helpers=r'''    def _smart_reminder_parse_message(self,message,client):
        import re,datetime,unicodedata
        raw=str(message or '').strip()
        if not raw:return None
        low=''.join(c for c in unicodedata.normalize('NFD',raw.lower()) if unicodedata.category(c)!='Mn')
        action=bool(re.search(r'\b(me liga|me chama|me avisa|me lembra|te ligo|vou ligar|liga|ligar|chama|chamar|retorna|retornar|retorno|separa|separar|manda|mandar|te mando|vou mandar|envia|enviar|fatura|faturar|cobra|cobrar|confirma|confirmar)\b',low))
        future=bool(re.search(r'\b(amanha|depois|mais tarde|depois do almoco|apos o almoco|segunda|terca|quarta|quinta|sexta|sabado|domingo|daqui a|as\s+\d{1,2}|\d{1,2}:\d{2}|\d{1,2}h)\b',low))
        if not (action and future):return None
        now=datetime.datetime.now();due=None;base=now
        m=re.search(r'daqui a\s+(\d{1,3})\s*(min|minuto|minutos|h|hora|horas)',low)
        if m:
            n=int(m.group(1));due=now+datetime.timedelta(minutes=n if m.group(2).startswith('min') else n*60)
        if 'amanha' in low:base=now+datetime.timedelta(days=1)
        weekdays={'segunda':0,'terca':1,'quarta':2,'quinta':3,'sexta':4,'sabado':5,'domingo':6}
        chosen_weekday=False
        for word,wd in weekdays.items():
            if word in low:
                add=(wd-now.weekday())%7
                if add==0:add=7
                base=now+datetime.timedelta(days=add);chosen_weekday=True;break
        hm=None
        for pat in (r'\b(?:as|pelas?)\s*(\d{1,2})(?::|h)?(\d{2})?\b',r'\b(\d{1,2}):(\d{2})\b',r'\b(\d{1,2})h(\d{2})?\b'):
            m=re.search(pat,low)
            if m:
                try:
                    hh=int(m.group(1));mm=int(m.group(2) or 0)
                    if 0<=hh<=23 and 0<=mm<=59:hm=(hh,mm);break
                except Exception:pass
        if hm:
            due=base.replace(hour=hm[0],minute=hm[1],second=0,microsecond=0)
            if due<=now and 'amanha' not in low and not chosen_weekday:due+=datetime.timedelta(days=1)
        elif due is None:
            if 'depois do almoco' in low or 'apos o almoco' in low:due=base.replace(hour=13,minute=30,second=0,microsecond=0)
            elif 'mais tarde' in low:due=now+datetime.timedelta(hours=2)
            elif 'amanha' in low or chosen_weekday:due=base.replace(hour=9,minute=0,second=0,microsecond=0)
        if due is None:return None
        c=str(client or 'cliente').strip()
        if re.search(r'\b(me liga|te ligo|vou ligar|liga|ligar)\b',low):title=f'Ligar para {c}'
        elif re.search(r'\b(separa|separar)\b',low):title=f'Separar / confirmar para {c}'
        elif re.search(r'\b(fatura|faturar)\b',low):title=f'Faturar pedido de {c}'
        elif re.search(r'\b(manda|mandar|te mando|vou mandar|envia|enviar)\b',low):title=f'Enviar retorno para {c}'
        elif re.search(r'\b(cobra|cobrar)\b',low):title=f'Cobrar retorno de {c}'
        else:title=f'Retornar para {c}'
        return {'title':title,'due_ts':due.timestamp(),'snippet':raw[-450:]}

    def _smart_reminder_from_diagnostic(self,name,context):
        import hashlib
        client=str(name or '').strip()
        if not client or not context:return
        try:
            if client in set(self._diagnostic_groups_load()):return
        except Exception:pass
        last=context[-1] if isinstance(context[-1],dict) else {}
        if not isinstance(last,dict) or last.get('is_call'):return
        msg=str(last.get('text') or '').strip();side=str(last.get('side') or '').strip()
        if not msg or side not in ('customer','seller'):return
        sig=hashlib.sha1((side+'|'+msg).encode('utf-8','ignore')).hexdigest()
        baseline=getattr(self,'_smart_reminder_diag_baseline',None)
        if not isinstance(baseline,dict):
            baseline={};self._smart_reminder_diag_baseline=baseline
        old=baseline.get(client);baseline[client]=sig
        if old is None or old==sig:return
        parsed=self._smart_reminder_parse_message(msg,client)
        if not parsed:return
        seen=getattr(self,'_smart_reminder_diag_seen',None)
        if not isinstance(seen,set):
            seen=set();self._smart_reminder_diag_seen=seen
        key=hashlib.sha1((client+'|'+parsed['title']+'|'+str(int(parsed['due_ts']//300))+'|'+msg).encode('utf-8','ignore')).hexdigest()
        if key in seen:return
        for r in getattr(self,'_reminders',[]) or []:
            if not isinstance(r,dict) or r.get('done'):continue
            if str(r.get('client') or '').strip()!=client:continue
            try:
                if abs(float(r.get('due_ts') or 0)-float(parsed['due_ts']))<1800 and parsed['title'].lower()[:12] in str(r.get('text') or '').lower():
                    seen.add(key);return
            except Exception:pass
        seen.add(key);self._smart_reminder_offer(client,msg,parsed)

    def _smart_reminder_offer(self,client,message,parsed):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QLabel,QHBoxLayout,QPushButton
        from PyQt6.QtCore import Qt
        import datetime
        try:
            pop=getattr(self,'_smart_reminder_popup',None)
            if pop and pop.isVisible():return
        except Exception:pass
        dlg=QDialog(self);self._smart_reminder_popup=dlg;dlg.setWindowTitle('💡 Sugestão de lembrete');dlg.setModal(False);dlg.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint,True);dlg.resize(520,215)
        lay=QVBoxLayout(dlg);head=QLabel('A conversa parece ter uma tarefa futura');head.setStyleSheet('font-size:14px;font-weight:900;color:#0b5d44;');lay.addWidget(head)
        when=datetime.datetime.fromtimestamp(float(parsed['due_ts'])).strftime('%d/%m/%Y às %H:%M')
        task=QLabel(f"<b>{parsed['title']}</b><br>{when}<br><span style='color:#61717f'>Cliente: {client}</span>");task.setWordWrap(True);lay.addWidget(task)
        snippet=QLabel('Trecho: “'+str(message or '')[-240:].replace('\n',' ')+'”');snippet.setWordWrap(True);snippet.setStyleSheet('color:#59636d;font-size:10px;');lay.addWidget(snippet)
        row=QHBoxLayout();create=QPushButton('⏰ Criar lembrete');ignore=QPushButton('Ignorar');row.addWidget(create);row.addStretch(1);row.addWidget(ignore);lay.addLayout(row)
        def do_create():
            dlg.accept();self._reminder_add(self,None,force_client=client,context=str(message or ''),prefill_text=parsed['title'],prefill_due=parsed['due_ts'])
        create.clicked.connect(do_create);ignore.clicked.connect(dlg.reject);dlg.finished.connect(lambda _=0:setattr(self,'_smart_reminder_popup',None));dlg.show();dlg.raise_();dlg.activateWindow()

'''
text=text.replace(anchor,helpers+anchor,1)

# 3) Reaproveita o ciclo existente do diagnostico. Nada novo no __init__ e nenhum QTimer adicional.
old_hook='''            except Exception: pass\n\n        groups=set(getattr(self,"_diagnostic_groups",set()) or set())'''
new_hook='''            except Exception: pass\n            try:self._smart_reminder_from_diagnostic(name,context)\n            except Exception as _smart_err:\n                try:self._diagnostic_log("smart_reminder_error",error=str(_smart_err)[:220])\n                except Exception:pass\n\n        groups=set(getattr(self,"_diagnostic_groups",set()) or set())'''
if old_hook not in text: raise SystemExit('ponto seguro em _diagnostic_scan_done nao encontrado')
text=text.replace(old_hook,new_hook,1)

# Garantia de seguranca: nao inserir timer ou inicializador automatico novo.
if '_smart_crm_timer' in text or '_smart_crm_init' in text: raise SystemExit('timer/init automatico inesperado encontrado')
p.write_text(text,encoding='utf-8')
print('patched wait formatting + diagnostic smart reminder',version)
