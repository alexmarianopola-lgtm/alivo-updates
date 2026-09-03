from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v12.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

if '_aliyvo_register_unique_install' not in text:
    marker='''def _aliyvo_open_feedback(parent=None,preset_category=None,preset_text=""):\n'''
    if marker not in text:
        raise SystemExit('feedback marker not found')

    telemetry=r'''

def _aliyvo_register_unique_install():
    """Registra uma unica vez esta instalacao Beta, sem dados pessoais.
    Envia somente ID anonimo, versao/plano e Windows. Nao le WhatsApp.
    """
    def worker():
        try:
            import os as _os
            import platform as _platform
            import urllib.request as _ur
            from datetime import datetime as _datetime
            base=globals().get("USER_DATA_DIR")
            if base:
                folder=Path(base)
            else:
                folder=Path(_os.environ.get("LOCALAPPDATA") or Path.home())/"ALIYVO"/"dados"
            folder.mkdir(parents=True,exist_ok=True)
            marker_file=folder/"install_registered.txt"
            if marker_file.exists():
                return
            install_id=_aliyvo_feedback_install_id()
            payload="\n".join([
                "ALIYVO BETA - INSTALACAO UNICA",
                "Instalacao: "+str(install_id),
                "Versao: "+str(globals().get("ALIYVO_VERSION","")),
                "Plano: "+str(globals().get("ALIYVO_PLAN","BETA_FREE")),
                "Windows: "+str(_platform.system())+" "+str(_platform.release()),
                "Data: "+_datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ]).encode("utf-8")
            req=_ur.Request(
                "https://ntfy.sh/"+ALIYVO_FEEDBACK_TOPIC,
                data=payload,
                method="POST",
                headers={
                    "Content-Type":"text/plain; charset=utf-8",
                    "Title":"ALIYVO Beta - Nova instalacao",
                    "Tags":"computer",
                    "User-Agent":"ALIYVO-Beta/"+str(globals().get("ALIYVO_VERSION","")),
                },
            )
            with _ur.urlopen(req,timeout=7) as resp:
                _=resp.read(256)
            marker_file.write_text(str(install_id),encoding="utf-8")
        except Exception:
            # Se estiver offline, tenta novamente na proxima abertura. Nunca bloqueia o app.
            pass
    try:
        import threading as _threading
        _threading.Thread(target=worker,name="AliyvoInstallRegister",daemon=True).start()
    except Exception:
        pass

'''
    text=text.replace(marker,telemetry+marker,1)

    # Uma unica tentativa por abertura, alguns segundos depois da interface iniciar.
    anchor='QTimer.singleShot(1200, _aliyvo_install_feedback_button)'
    if anchor not in text:
        raise SystemExit('feedback startup anchor not found')
    text=text.replace(anchor,anchor+'\n'+re.match(r'\s*',anchor).group(0)+'QTimer.singleShot(3500, _aliyvo_register_unique_install)',1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched anonymous unique install registration',version)
