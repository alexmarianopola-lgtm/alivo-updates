from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v19.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.33 - melhora o launcher da busca de placa para detectar a instancia real do BlueStacks.

if '_aliyvo_bluestacks_instances' not in text:
    marker='def _aliyvo_open_plate_lookup_app(parent=None):\n'
    if marker not in text:
        raise SystemExit('plate lookup launcher marker not found')

    helper=r'''
def _aliyvo_bluestacks_instances():
    """Retorna os nomes reais das instancias instaladas no BlueStacks 5."""
    found=[]
    try:
        import os,re as _re
        conf_candidates=[
            Path(os.environ.get("ProgramData") or r"C:\\ProgramData")/"BlueStacks_nxt"/"bluestacks.conf",
            Path(r"C:\\ProgramData\BlueStacks_nxt\bluestacks.conf"),
        ]
        for conf in conf_candidates:
            try:
                if not conf.exists(): continue
                raw=conf.read_text(encoding="utf-8",errors="ignore")
                for name in _re.findall(r'bst\.instance\.([^.="\\s]+)\.',raw):
                    if name and name not in found:
                        found.append(name)
            except Exception:
                pass
    except Exception:
        pass
    # Fallbacks apenas se nao conseguimos ler a configuracao.
    if not found:
        found=["Rvc64","Pie64","Tiramisu64","Nougat64","Nougat32"]
    return found


'''
    text=text.replace(marker,helper+marker,1)

# Troca o bloco que usava uma lista fixa e parava na primeira tentativa.
old=r'''        instances=["Rvc64","Pie64","Tiramisu64","Nougat64","Nougat32"]
        started=False
        for inst in instances:
            try:
                subprocess.Popen(
                    [player,"--instance",inst,"--cmd","launchApp","--package",ALIYVO_PLATE_APP_PACKAGE,"--source","desktop_shortcut"],
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL
                )
                started=True
                break
            except Exception:
                pass
        if not started:
            subprocess.Popen([player],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)'''
new=r'''        instances=_aliyvo_bluestacks_instances()
        inst=instances[0] if instances else ""
        if inst:
            subprocess.Popen(
                [player,"--instance",inst,"--cmd","launchApp","--package",ALIYVO_PLATE_APP_PACKAGE,"--source","desktop_shortcut"],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL
            )
        else:
            subprocess.Popen([player],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)'''
if old not in text:
    raise SystemExit('fixed instance launcher block not found')
text=text.replace(old,new,1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched BlueStacks instance detection',version)
