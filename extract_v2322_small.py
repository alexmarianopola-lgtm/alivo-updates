from pathlib import Path
import ast,sys
src=Path(sys.argv[1]).read_text(encoding='utf-8',errors='replace')
lines=src.splitlines(); tree=ast.parse(src)
sets={
 'inspect_v2322_calls.txt':{'_diagnostic_live_call_update','_diagnostic_finish_live_call','_diagnostic_log','_diagnostic_scan_done'},
 'inspect_v2322_crm_methods.txt':{'_crm_client_profile','_crm_save_profile','_crm_schedule_followup','_crm_register_contact_dialog','_crm_clients_dialog','_reminder_save','_attendance_open_chat'},
 'inspect_v2322_maininit.txt':{'_attendance_bootstrap','_diagnostic_start'}
}
for fn,names in sets.items():
 out=[]
 for node in ast.walk(tree):
  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in names:
   a=max(1,node.lineno-8);b=min(len(lines),getattr(node,'end_lineno',node.lineno)+8)
   out.append(f'===== {node.name} =====')
   out.extend(lines[a-1:b])
 Path(fn).write_text('\n'.join(out),encoding='utf-8')
 print(fn,len(out))
