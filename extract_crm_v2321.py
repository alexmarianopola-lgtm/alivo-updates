from pathlib import Path
import ast,sys
src=Path(sys.argv[1]).read_text(encoding='utf-8',errors='replace')
tree=ast.parse(src)
lines=src.splitlines()
names=[]
for node in ast.walk(tree):
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
        n=node.name
        if n.startswith('_attendance_') or n.startswith('_crm_') or n in {
            '_diagnostic_show_dialog','_diagnostic_apply_home','_contact_category',
            '_contact_classify_current'
        }:
            names.append((node.lineno,getattr(node,'end_lineno',node.lineno),n))
names=sorted(set(names))
out=[]
for a,b,n in names:
    lo=max(1,a-3); hi=min(len(lines),b+3)
    out.append(f"===== {n} L{a}-{b} =====")
    for i in range(lo,hi+1):
        out.append(f"{i:06d}: {lines[i-1]}")
# Add targeted literal neighborhoods
for term in ['Hoje','Próximo contato','proximo contato','retorno','comprador','atendimento','CRM']:
    for i,l in enumerate(lines,1):
        if term.lower() in l.lower():
            lo=max(1,i-8); hi=min(len(lines),i+20)
            out.append(f"===== TERM {term!r} @ L{i} =====")
            for j in range(lo,hi+1):
                out.append(f"{j:06d}: {lines[j-1]}")
Path(sys.argv[2]).write_text('\n'.join(out),encoding='utf-8')
print('methods',len(names),'chars',sum(map(len,out)))
