from pathlib import Path
import sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
module_src=Path(__file__).resolve().parent/'aliyvo_call_ai_v2323.py'
module_dst=root/'_app'/'aliyvo_call_ai.py'

s=main.read_text(encoding='utf-8')
if 'ALIYVO_VERSION = "0.23.22"' not in s:
    raise SystemExit('base 0.23.22 nao encontrada')
s=s.replace('ALIYVO_VERSION = "0.23.22"','ALIYVO_VERSION = "0.23.23"',1)
s=s.replace('aliyvo_version="0.23.22"','aliyvo_version="0.23.23"')

# Importa modulo isolado para nao misturar gravacao/IA no nucleo do WhatsApp.
anchor='''    from aliyvo_ponto import AliyvoPontoController
'''
if anchor not in s:
    raise SystemExit('import aliyvo_ponto nao encontrado')
s=s.replace(anchor,anchor+'from aliyvo_call_ai import AliyvoCallAIManager\n',1)

# Botao no topo.
anchor='''        self.reminder_toggle=QPushButton("👥  CRM")
        self.radar_toggle=QPushButton("🎯  Radar da Carteira")
'''
replacement='''        self.reminder_toggle=QPushButton("👥  CRM")
        self.calls_ai_toggle=QPushButton("📞  Ligações IA")
        self.calls_ai_toggle.setToolTip("Gravação, transcrição, avaliação comercial e CRM")
        self.radar_toggle=QPushButton("🎯  Radar da Carteira")
'''
if anchor not in s:
    raise SystemExit('anchor botoes topo nao encontrado')
s=s.replace(anchor,replacement,1)

anchor='''        nav_lay.addWidget(self.reminder_toggle)
        nav_lay.addWidget(self.radar_toggle)
'''
replacement='''        nav_lay.addWidget(self.reminder_toggle)
        nav_lay.addWidget(self.calls_ai_toggle)
        nav_lay.addWidget(self.radar_toggle)
'''
if anchor not in s:
    raise SystemExit('anchor layout topo nao encontrado')
s=s.replace(anchor,replacement,1)

# Acao do botao.
anchor='''        self.reminder_toggle.clicked.connect(self._reminder_show_dialog)
'''
replacement='''        self.reminder_toggle.clicked.connect(self._reminder_show_dialog)
        self.calls_ai_toggle.clicked.connect(
            lambda: self._call_ai_manager.show_dashboard()
            if getattr(self,"_call_ai_manager",None) is not None
            else QMessageBox.warning(self,"Ligações IA","O módulo de ligações não iniciou.")
        )
'''
if anchor not in s:
    raise SystemExit('anchor click CRM nao encontrado')
s=s.replace(anchor,replacement,1)

# Inicializa antes do diagnostico iniciar os scans.
anchor='''    def _attendance_bootstrap(self):
        self._attendance_load()
'''
replacement='''    def _attendance_bootstrap(self):
        self._attendance_load()
        try:
            self._call_ai_manager=AliyvoCallAIManager(self)
        except Exception as _call_ai_init_error:
            self._call_ai_manager=None
            try:self._diagnostic_log("call_ai_init_error",error=str(_call_ai_init_error)[:500])
            except Exception:pass
'''
if anchor not in s:
    raise SystemExit('bootstrap nao encontrado')
s=s.replace(anchor,replacement,1)

# Hook de INICIO exatamente quando overlay confirma uma chamada nova.
old='''            if not isinstance(cur,dict):
                start=now-duration if duration>0 else now;session=f"live|{client}|{int(start)}";cur={"client":client,"start_ts":start,"duration_seconds":duration,"last_seen_ts":now,"call_type":ctype,"direction":"unknown","session_id":session};self._diagnostic_live_call=cur
                self._diagnostic_log("call_live_started",client=client,call_type=ctype,started_ts=start,visible_duration_seconds=duration,call_key=session)
'''
new='''            if not isinstance(cur,dict):
                start=now-duration if duration>0 else now;session=f"live|{client}|{int(start)}";cur={"client":client,"start_ts":start,"duration_seconds":duration,"last_seen_ts":now,"call_type":ctype,"direction":"unknown","session_id":session};self._diagnostic_live_call=cur
                self._diagnostic_log("call_live_started",client=client,call_type=ctype,started_ts=start,visible_duration_seconds=duration,call_key=session)
                try:
                    if getattr(self,"_call_ai_manager",None) is not None:self._call_ai_manager.on_call_started(cur)
                except Exception as _call_ai_start_error:
                    self._diagnostic_log("call_ai_start_hook_error",client=client,error=str(_call_ai_start_error)[:400])
'''
if old not in s:
    raise SystemExit('hook inicio chamada nao encontrado')
s=s.replace(old,new,1)

# Hook de FIM antes de limpar o objeto da chamada.
old='''        self._diagnostic_log("call",client=client,direction=str(cur.get("direction") or "unknown"),call_type=str(cur.get("call_type") or "voice"),missed=False,duration_seconds=duration,call_key=session,source="live_overlay",started_ts=start,ended_ts=now,end_reason=reason)
        recent=list(getattr(self,"_diagnostic_recent_live_calls",[]) or []);recent.append({"client":client,"ended_ts":now,"duration_seconds":duration,"call_type":str(cur.get("call_type") or "voice")})
'''
new='''        self._diagnostic_log("call",client=client,direction=str(cur.get("direction") or "unknown"),call_type=str(cur.get("call_type") or "voice"),missed=False,duration_seconds=duration,call_key=session,source="live_overlay",started_ts=start,ended_ts=now,end_reason=reason)
        try:
            if getattr(self,"_call_ai_manager",None) is not None:
                _call_ai_meta=dict(cur);_call_ai_meta.update({"client":client,"started_ts":start,"ended_ts":now,"duration_seconds":duration,"session_id":session,"end_reason":reason})
                self._call_ai_manager.on_call_finished(_call_ai_meta)
        except Exception as _call_ai_finish_error:
            self._diagnostic_log("call_ai_finish_hook_error",client=client,error=str(_call_ai_finish_error)[:400])
        recent=list(getattr(self,"_diagnostic_recent_live_calls",[]) or []);recent.append({"client":client,"ended_ts":now,"duration_seconds":duration,"call_type":str(cur.get("call_type") or "voice")})
'''
if old not in s:
    raise SystemExit('hook fim chamada nao encontrado')
s=s.replace(old,new,1)

module_dst.write_text(module_src.read_text(encoding='utf-8'),encoding='utf-8')
main.write_text(s,encoding='utf-8')
print('PATCH_CALL_AI_V2323=OK')
