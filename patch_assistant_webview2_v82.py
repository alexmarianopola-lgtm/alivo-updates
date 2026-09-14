from pathlib import Path
import re, sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
text=main.read_text(encoding='utf-8')

# 1) Bump estritamente da base confirmada.
text2,n=re.subn(r'ALIYVO_VERSION\s*=\s*["\']0\.22\.81["\']','ALIYVO_VERSION = "0.22.82"',text,count=1)
if n!=1:
    raise SystemExit(f'Versao 0.22.81 nao encontrada exatamente; ocorrencias={n}')
text=text2

# 2) Adiciona um navegador Edge WebView2 exclusivo para o Assistente.
marker='class ChatGPTPanel(QWidget):\n'
if marker not in text:
    raise SystemExit('ChatGPTPanel nao encontrado')

wv2_class=r'''class ChatGPTWebView(QtWebView2Widget):
    """ChatGPT via Microsoft Edge WebView2: codecs, videos e downloads do Edge."""
    loadFinished=pyqtSignal(bool)
    loadStarted=pyqtSignal()

    def __init__(self):
        self._current_url="https://chatgpt.com/share/6a91b46d-d2f4-83e9-a758-e901e31bcba2"
        self._core_webview2=None
        profile_dir=USER_CACHE_DIR/"webview2_chatgpt_profile"
        try:
            profile_dir.mkdir(parents=True,exist_ok=True)
        except Exception:
            profile_dir=USER_CACHE_DIR

        super().__init__(
            url=self._current_url,
            user_agent=None,
            debug=False,
            context_menus=True,
            transparent=False,
            background_color="#FFFFFF",
            handle_new_window=True,
            lazyload=False,
            user_data_folder=str(profile_dir),
            no_local_storage=False,
            fullscreen_support=True,
            init_settings_hook=self._configure_webview2_core,
            parent=None,
        )

        try:
            self.bridge.domContentLoaded.connect(self._on_dom_loaded)
        except Exception:
            pass
        try:
            self.bridge.initialization_done.connect(self._on_initialized)
        except Exception:
            pass

    def _configure_webview2_core(self,core):
        self._core_webview2=core
        try:
            core.DownloadStarting += self._on_download_starting
        except Exception:
            pass
        try:
            core.PermissionRequested += self._on_permission_requested
        except Exception:
            pass
        try:
            settings=core.Settings
            settings.IsScriptEnabled=True
            try: settings.AreDefaultContextMenusEnabled=True
            except Exception: pass
        except Exception:
            pass

    def _on_permission_requested(self,sender,args):
        try:
            uri=str(getattr(args,"Uri","") or "").lower()
            if not any(host in uri for host in ("chatgpt.com","openai.com")):
                return
            kind=str(getattr(args,"PermissionKind","") or "").lower()
            allow_kinds=(
                "microphone","camera","autoplay","clipboard",
                "notifications","persistentstorage","persistent storage",
                "windowmanagement","window management",
            )
            if not any(x in kind for x in allow_kinds):
                return
            current=getattr(args,"State",None)
            enum_type=type(current)
            allow=getattr(enum_type,"Allow",None)
            if allow is None and current is not None:
                allow=getattr(current,"Allow",None)
            if allow is not None:
                args.State=allow
                try: args.SavesInProfile=True
                except Exception: pass
                try: args.Handled=True
                except Exception: pass
        except Exception:
            pass

    def _download_folder(self):
        home=Path.home()
        for folder in (home/"Downloads",home/"OneDrive"/"Downloads",USER_CACHE_DIR/"downloads"):
            try:
                folder.mkdir(parents=True,exist_ok=True)
                return folder
            except Exception:
                pass
        return APP_DIR

    def _unique_download_name(self,folder,name):
        name=(name or "arquivo_chatgpt").strip()
        target=folder/name
        if not target.exists():
            return name
        stem=Path(name).stem
        suffix=Path(name).suffix
        i=1
        while True:
            candidate=f"{stem} ({i}){suffix}"
            if not (folder/candidate).exists():
                return candidate
            i+=1

    def _on_download_starting(self,sender,args):
        try:
            original=str(getattr(args,"ResultFilePath","") or "")
            suggested=Path(original).name if original else "arquivo_chatgpt"
            folder=self._download_folder()
            target=(folder/self._unique_download_name(folder,suggested)).resolve()
            args.ResultFilePath=str(target)
            try: args.Handled=True
            except Exception: pass
            try: args.Cancel=False
            except Exception: pass
        except Exception:
            pass

    def setUrl(self,url):
        try:
            value=url.toString() if hasattr(url,"toString") else str(url)
            self._current_url=value
            self.loadStarted.emit()
            self.load_url(value)
        except Exception:
            pass

    def reload(self):
        self.loadStarted.emit()
        try:
            super().reload()
        except Exception:
            try: self.load_url(self._current_url)
            except Exception: pass

    def go_back(self):
        try:
            core=self._core_webview2
            if core is not None and bool(core.CanGoBack):
                self.loadStarted.emit()
                core.GoBack()
                return True
        except Exception:
            pass
        return False

    def _on_initialized(self,*args):
        try:
            if args and args[0] is False:
                self.loadFinished.emit(False)
        except Exception:
            pass

    def _on_dom_loaded(self):
        self.loadFinished.emit(True)


'''
text=text.replace(marker,wv2_class+marker,1)

# 3) Troca somente a criação do browser do Assistente.
old='''        self.web=QWebEngineView(self)\n\n        try:\n            self.web.page().profile().downloadRequested.connect(self._handle_download)\n        except Exception:\n            pass\n'''
new='''        self.web=ChatGPTWebView()\n'''
if old not in text:
    raise SystemExit('Bloco QWebEngineView do Assistente nao encontrado')
text=text.replace(old,new,1)

# 4) Voltar passa a usar o historico nativo do Edge.
old_back='''        try:\n            if web.history().canGoBack():\n                web.back()\n                self.status.setText("Voltando...")\n            else:\n                self._go_home()\n        except Exception:\n            self._go_home()\n'''
new_back='''        try:\n            if hasattr(web,"go_back") and web.go_back():\n                self.status.setText("Voltando...")\n            else:\n                self._go_home()\n        except Exception:\n            self._go_home()\n'''
if old_back not in text:
    raise SystemExit('Bloco de voltar do Assistente nao encontrado')
text=text.replace(old_back,new_back,1)

main.write_text(text,encoding='utf-8')
print('patched Assistant WebView2 0.22.82')
