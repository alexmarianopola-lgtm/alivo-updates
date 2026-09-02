from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v3.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# Preserve capture log across page navigations/reinjections.
text=text.replace('save([]); log("capture_start",{title:document.title||""});','if(!read().length){ save([]); log("capture_start",{title:document.title||""}); }')

# Start a short-lived rearm loop while diagnostic mode is active.
old='''    def _catalog_capture_start(self):\n        browser=self._get_catalog_window(False)'''
new='''    def _catalog_capture_start(self):\n        browser=self._get_catalog_window(False)\n        browser._capture_started=True\n        browser._capture_rounds=0'''
if old in text:
    text=text.replace(old,new,1)

needle='''        browser.start_network_capture(started)'''
replacement='''        browser.start_network_capture(started)\n        QTimer.singleShot(300,lambda b=browser:self._catalog_capture_keepalive(b))'''
if needle in text and '_catalog_capture_keepalive' not in text:
    text=text.replace(needle,replacement,1)

marker='''    def _catalog_capture_read(self,browser):'''
method='''    def _catalog_capture_keepalive(self,browser):\n        try:\n            if not getattr(browser,"_capture_started",False):\n                return\n            browser._capture_rounds=int(getattr(browser,"_capture_rounds",0))+1\n            if browser._capture_rounds>140:\n                browser._capture_started=False\n                return\n            # Reinstala os hooks após qualquer navegação sem apagar o histórico.\n            browser.start_network_capture()\n        except Exception:\n            pass\n        QTimer.singleShot(300,lambda b=browser:self._catalog_capture_keepalive(b))\n\n'''
if marker in text and '_catalog_capture_keepalive' not in text:
    text=text.replace(marker,method+marker,1)

# Enrich diagnostic screen with GraphQL hint if resources mention it.
oldline='''            if useful: self.plate_panel.status.setText(f"✅ Diagnóstico capturou {useful} chamada(s).")'''
newline='''            if any("gateway/graphql" in str(x) for x in lines):\n                lines.insert(4,"PISTA: endpoint GraphQL detectado: https://bff.catalogofraga.com.br/gateway/graphql")\n                self.plate_panel.capture.setPlainText("\\n".join(lines))\n            if useful: self.plate_panel.status.setText(f"✅ Diagnóstico capturou {useful} chamada(s).")'''
if oldline in text:
    text=text.replace(oldline,newline,1)

# Accept file downloads created by ChatGPT/Copiloto inside QWebEngine.
# Qt WebEngine cancels downloads by default unless the application accepts them.
if '_aliyvo_install_download_hooks' not in text:
    hook = r'''
# --- ALIYVO: downloads do Copiloto/ChatGPT ---
def _aliyvo_handle_web_download(download):
    try:
        import os as _os
        from pathlib import Path as _Path
        folder = _Path.home() / "Downloads"
        folder.mkdir(parents=True, exist_ok=True)
        try:
            name = str(download.downloadFileName() or "arquivo")
        except Exception:
            name = "arquivo"
        name = _os.path.basename(name).strip() or "arquivo"
        base, ext = _os.path.splitext(name)
        candidate = folder / name
        n = 2
        while candidate.exists():
            candidate = folder / f"{base} ({n}){ext}"
            n += 1
        download.setDownloadDirectory(str(folder))
        download.setDownloadFileName(candidate.name)
        download.accept()
    except Exception:
        try:
            download.accept()
        except Exception:
            pass

def _aliyvo_install_download_hooks():
    try:
        _app = QApplication.instance()
        if _app is None:
            return
        for _w in _app.allWidgets():
            try:
                _page = _w.page()
                if _page is None:
                    continue
                _profile = _page.profile()
                if _profile is None or bool(_profile.property("ALIYVO_DOWNLOAD_HOOK")):
                    continue
                _profile.downloadRequested.connect(_aliyvo_handle_web_download)
                _profile.setProperty("ALIYVO_DOWNLOAD_HOOK", True)
            except Exception:
                pass
    finally:
        try:
            QTimer.singleShot(2000, _aliyvo_install_download_hooks)
        except Exception:
            pass
# --- fim downloads Copiloto ---

'''
    # Put helper functions BEFORE the top-level __main__ block so indentation remains valid.
    main_block = re.search(r'(?m)^if\s+__name__\s*==\s*[\"\']__main__[\"\']\s*:', text)
    if main_block:
        text = text[:main_block.start()] + hook + text[main_block.start():]
    else:
        m = re.search(r'(?m)^(?P<indent>\s*)(?P<var>[A-Za-z_]\w*)\s*=\s*QApplication\s*\(', text)
        if not m:
            raise SystemExit('QApplication creation not found for download hook')
        text = text[:m.start()] + hook + text[m.start():]

    # Arm the hook immediately after QApplication is instantiated.
    m2 = re.search(r'(?m)^(?P<indent>\s*)(?P<var>[A-Za-z_]\w*)\s*=\s*QApplication\s*\([^\n]*\)\s*$', text)
    if not m2:
        raise SystemExit('QApplication assignment not found after download hook')
    insert_pos = m2.end()
    indent = m2.group('indent')
    text = text[:insert_pos] + '\n' + indent + 'QTimer.singleShot(700, _aliyvo_install_download_hooks)' + text[insert_pos:]

# From 0.22.15 onward, reveal the downloaded file in Windows Explorer when it finishes.
if '_aliyvo_reveal_when_done' not in text:
    old_download = '''        download.setDownloadDirectory(str(folder))\n        download.setDownloadFileName(candidate.name)\n        download.accept()'''
    new_download = '''        download.setDownloadDirectory(str(folder))\n        download.setDownloadFileName(candidate.name)\n\n        def _aliyvo_reveal_when_done(*_args):\n            try:\n                _state = download.state()\n                _state_name = str(getattr(_state, "name", _state))\n                if "DownloadCompleted" not in _state_name:\n                    return\n                try:\n                    download.stateChanged.disconnect(_aliyvo_reveal_when_done)\n                except Exception:\n                    pass\n                import subprocess as _subprocess\n                try:\n                    _subprocess.Popen(["explorer.exe", "/select,", str(candidate)])\n                except Exception:\n                    try:\n                        _os.startfile(str(folder))\n                    except Exception:\n                        pass\n            except Exception:\n                pass\n\n        try:\n            download.stateChanged.connect(_aliyvo_reveal_when_done)\n        except Exception:\n            pass\n        download.accept()'''
    if old_download not in text:
        raise SystemExit('download handler target not found for reveal upgrade')
    text=text.replace(old_download,new_download,1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched',version)
