from pathlib import Path
import ast,sys
src=Path(sys.argv[1]).read_text(encoding='utf-8',errors='replace')
lines=src.splitlines()
tree=ast.parse(src)
wanted={
 '_diagnostic_live_call_update','_diagnostic_finish_live_call','_diagnostic_log',
 '_crm_client_profile','_crm_save_profile','_crm_schedule_followup','_crm_current_contact_name',
 '_crm_clients_dialog','_attendance_open_chat','_diagnostic_show_dialog',
 '__init__'
}
out=[]
for node in ast.walk(tree):
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in wanted:
        a=max(1,node.lineno-20); b=min(len(lines),getattr(node,'end_lineno',node.lineno)+20)
        out.append(f'===== {node.name} {node.lineno}-{getattr(node,"end_lineno",node.lineno)} =====')
        out.extend(f'{i:06d}: {lines[i-1]}' for i in range(a,b+1))
for term in ['self.attendance_toggle=','self.reminder_toggle=','self.audio_toggle=','QTimer.singleShot(650,self._attendance_bootstrap)','ALIYVO_VERSION =']:
    for i,l in enumerate(lines,1):
        if term in l:
            a=max(1,i-30);b=min(len(lines),i+60)
            out.append(f'===== TERM {term} @ {i} =====')
            out.extend(f'{j:06d}: {lines[j-1]}' for j in range(a,b+1))
Path(sys.argv[2]).write_text('\n'.join(out),encoding='utf-8')
print(len(out))
