from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v15.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

if 'class _AliyvoUpdateNoticeBridge(QObject):' not in text:
    imports='\nfrom PyQt6.QtCore import QObject, pyqtSignal\n'
    pos=0
    for mm in re.finditer(r'(?m)^(?:from\s+\S+\s+import\s+.+|import\s+.+)$',text):
        pos=mm.end()
        if pos>3500: break
    text=text[:pos]+imports+text[pos:]

    marker='def _aliyvo_open_feedback(parent=None,preset_category=None,preset_text=""):\n'
    if marker not in text:
        raise SystemExit('feedback marker not found')

    code=r'''

class _AliyvoUpdateNoticeBridge(QObject):
    ready=pyqtSignal(object)

_aliyvo_update_notice_bridge=None


def _aliyvo_version_tuple(value):
    try:
        return tuple(int(x) for x in re.findall(r"\d+",str(value))[:4])
    except Exception:
        return (0,)


def _aliyvo_update_notice_folder():
    try:
        base=globals().get("USER_DATA_DIR")
        folder=Path(base) if base else Path.home()/"ALIYVO"/"dados"
        folder.mkdir(parents=True,exist_ok=True)
        return folder
    except Exception:
        return Path.home()


def _aliyvo_open_updates_from_notice():
    try:
        app=QApplication.instance()
        if not app: return
        candidates=[]
        for w in app.allWidgets():
            try:
                if isinstance(w,QPushButton) and w.isVisible():
                    t=str(w.text() or "").lower()
                    if "atualiza" in t and "observ" not in t:
                        candidates.append(w)
            except Exception:
                pass
        if candidates:
            candidates[0].click()
            return
        QMessageBox.information(None,"Atualizações","Abra o menu Atualizações do ALIYVO e clique em Verificar atualização.")
    except Exception:
        pass


def _aliyvo_show_update_notice(info):
    try:
        if not isinstance(info,dict): return
        latest=str(info.get("version") or "").strip().lstrip("vV")
        current=str(globals().get("ALIYVO_VERSION","")).strip().lstrip("vV")
        if not latest or _aliyvo_version_tuple(latest)<=_aliyvo_version_tuple(current):
            return
        folder=_aliyvo_update_notice_folder()
        marker=folder/"update_notice_seen.txt"
        if marker.exists() and marker.read_text(encoding="utf-8",errors="ignore").strip()==latest:
            return
        notes=str(info.get("body") or "Nova atualização disponível.").strip()
        if len(notes)>1000: notes=notes[:1000]+"..."

        dlg=QMessageBox()
        dlg.setWindowTitle("Nova atualização do ALIYVO")
        dlg.setIcon(QMessageBox.Icon.Information)
        dlg.setText(f"🚀 <b>Nova versão disponível: {latest}</b>")
        dlg.setInformativeText("<b>O que mudou:</b><br>"+notes.replace("\n","<br>")+"<br><br>Você está usando a versão "+current+".")
        go=dlg.addButton("Abrir Atualizações",QMessageBox.ButtonRole.AcceptRole)
        dlg.addButton("Depois",QMessageBox.ButtonRole.RejectRole)
        dlg.exec()
        try: marker.write_text(latest,encoding="utf-8")
        except Exception: pass
        if dlg.clickedButton() is go:
            QTimer.singleShot(120,_aliyvo_open_updates_from_notice)
    except Exception:
        pass


def _aliyvo_check_update_notice():
    global _aliyvo_update_notice_bridge
    try:
        if _aliyvo_update_notice_bridge is None:
            _aliyvo_update_notice_bridge=_AliyvoUpdateNoticeBridge()
            _aliyvo_update_notice_bridge.ready.connect(_aliyvo_show_update_notice)
        bridge=_aliyvo_update_notice_bridge
    except Exception:
        return

    def worker():
        try:
            import urllib.request as _ur
            import json as _json
            req=_ur.Request(
                "https://api.github.com/repos/alexmarianopola-lgtm/alivo-updates/releases/latest",
                headers={"User-Agent":"ALIYVO-Update-Notice/"+str(globals().get("ALIYVO_VERSION",""))}
            )
            with _ur.urlopen(req,timeout=5) as resp:
                d=_json.loads(resp.read(65536).decode("utf-8","replace"))
            bridge.ready.emit({
                "version":str(d.get("tag_name") or "").lstrip("vV"),
                "body":str(d.get("body") or ""),
            })
        except Exception:
            pass
    try:
        import threading as _threading
        _threading.Thread(target=worker,name="AliyvoUpdateNotice",daemon=True).start()
    except Exception:
        pass

'''
    text=text.replace(marker,code+marker,1)

    pat=r'(?m)^(?P<indent>[ \t]*)QTimer\.singleShot\(3500, _aliyvo_register_unique_install\)[ \t]*$'
    m=re.search(pat,text)
    if not m:
        raise SystemExit('startup anchor not found')
    indent=m.group('indent')
    repl=indent+'QTimer.singleShot(3500, _aliyvo_register_unique_install)\n'+indent+'QTimer.singleShot(6500, _aliyvo_check_update_notice)'
    text=text[:m.start()]+repl+text[m.end():]

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched update notice',version)
