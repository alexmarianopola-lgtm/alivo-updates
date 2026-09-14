from pathlib import Path
import re

p=Path(r'C:\temp\build\_app\main.py')
s=p.read_text(encoding='utf-8')
s=s.replace('ALIYVO_VERSION = "0.22.83"','ALIYVO_VERSION = "0.22.84"',1)

start=s.index('    def _smart_reminder_from_diagnostic(self,name,context):')
end=s.index('\n    def ', start+10)
new=r'''    def _smart_reminder_from_diagnostic(self,name,context):
        import hashlib,unicodedata,re
        client=str(name or '').strip()
        if not client or not context:return
        try:
            if client in set(self._diagnostic_groups_load()):return
        except Exception:pass
        last=context[-1] if isinstance(context[-1],dict) else {}
        if not isinstance(last,dict) or last.get('is_call'):return
        msg=str(last.get('text') or '').strip();side=str(last.get('side') or '').strip()
        if not msg or side not in ('customer','seller'):return

        # v0.22.84: entende promessa futura + confirmação curta do cliente.
        # Ex.: vendedor "mando amanhã?" -> cliente "isso".
        source_msg=msg
        source_side=side
        if side=='customer':
            try:
                norm=unicodedata.normalize('NFKD',msg).encode('ascii','ignore').decode('ascii').lower()
            except Exception:
                norm=msg.lower()
            norm=re.sub(r'[^a-z0-9]+',' ',norm).strip()
            confirmations={
                'sim','isso','isso mesmo','pode','pode ser','ok','okay','blz','beleza',
                'fechou','fechado','combinado','certo','perfeito','manda','pode mandar',
                'amanha','isso ai','exato','correto','show','top'
            }
            if norm in confirmations and len(context)>=2:
                for prev in reversed(context[:-1][-5:]):
                    if not isinstance(prev,dict) or prev.get('is_call'):continue
                    prev_side=str(prev.get('side') or '').strip()
                    prev_msg=str(prev.get('text') or '').strip()
                    if prev_side=='seller' and prev_msg:
                        candidate=self._smart_reminder_parse_message(prev_msg,client)
                        if candidate:
                            source_msg=prev_msg
                            source_side='seller_confirmed'
                            parsed=candidate
                            break
                else:
                    parsed=None
            else:
                parsed=None
        else:
            parsed=None

        sig=hashlib.sha1((side+'|'+msg).encode('utf-8','ignore')).hexdigest()
        baseline=getattr(self,'_smart_reminder_diag_baseline',None)
        if not isinstance(baseline,dict):
            baseline={};self._smart_reminder_diag_baseline=baseline
        old=baseline.get(client);baseline[client]=sig
        if old is None or old==sig:return
        if parsed is None:
            parsed=self._smart_reminder_parse_message(source_msg,client)
        if not parsed:return
        seen=getattr(self,'_smart_reminder_diag_seen',None)
        if not isinstance(seen,set):
            seen=set();self._smart_reminder_diag_seen=seen
        key=hashlib.sha1((client+'|'+parsed['title']+'|'+str(int(parsed['due_ts']//300))+'|'+source_msg+'|'+source_side).encode('utf-8','ignore')).hexdigest()
        if key in seen:return
        for r in getattr(self,'_reminders',[]) or []:
            if not isinstance(r,dict) or r.get('done'):continue
            if str(r.get('client') or '').strip()!=client:continue
            try:
                if abs(float(r.get('due_ts') or 0)-float(parsed['due_ts']))<1800 and parsed['title'].lower()[:12] in str(r.get('text') or '').lower():
                    seen.add(key);return
            except Exception:pass
        seen.add(key);self._smart_reminder_offer(client,source_msg,parsed)
'''
s=s[:start]+new+s[end:]
p.write_text(s,encoding='utf-8')
