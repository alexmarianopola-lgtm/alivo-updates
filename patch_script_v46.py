from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v46.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

def replace_method(src,class_name,method_name,new_code):
    tree=ast.parse(src)
    cls=next((n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==class_name),None)
    if cls is None: raise SystemExit(f'class {class_name} not found')
    target=next((n for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==method_name),None)
    if target is None: raise SystemExit(f'method {class_name}.{method_name} not found')
    lines=src.splitlines(keepends=True)
    start=sum(len(x) for x in lines[:target.lineno-1]); end=sum(len(x) for x in lines[:target.end_lineno])
    if not new_code.endswith('\n'):new_code+='\n'
    return src[:start]+new_code+src[end:]

# 1) Permissoes de chamadas: cobre os tipos atuais do WebView2 usados por WebRTC.
new_perm=r'''    def _on_webview2_permission_requested(self,sender,args):
        try:
            uri=str(getattr(args,"Uri","") or "").lower()
            if "whatsapp.com" not in uri:
                return
            kind=str(getattr(args,"PermissionKind","") or "").lower()
            allow_kinds=(
                "microphone","camera","autoplay",
                "windowmanagement","window management",
                "notifications","persistentstorage","persistent storage",
                "clipboard","other sensors",
            )
            allowed=any(x in kind for x in allow_kinds)
            # Log tecnico sem dados da conversa, apenas permissao/origem.
            try:
                log_dir=ALIYVO_USER_DIR/"logs"; log_dir.mkdir(parents=True,exist_ok=True)
                import time as _time
                with (log_dir/"WEBVIEW2_MEDIA.log").open("a",encoding="utf-8") as f:
                    f.write("["+_time.strftime("%Y-%m-%d %H:%M:%S")+"] "+kind+" | "+uri[:180]+" | allow="+str(allowed)+"\n")
            except Exception:pass
            if not allowed:
                return
            current=getattr(args,"State",None)
            enum_type=type(current)
            allow=getattr(enum_type,"Allow",None)
            if allow is None and current is not None:
                allow=getattr(current,"Allow",None)
            if allow is not None:
                args.State=allow
                try:args.SavesInProfile=True
                except Exception:pass
                try:args.Handled=True
                except Exception:pass
        except Exception:
            pass
'''
text=replace_method(text,'WhatsAppView','_on_webview2_permission_requested',new_perm)

# 2) Volta ao comportamento estavel da 0.22.57: falha e informada, mas o
# componente nao dispara uma cadeia de destruicao/recriacao durante a sessao.
new_init=r'''    def _on_wv2_initialized(self,*args):
        try:
            if args and args[0] is False:
                self.loadFinished.emit(False)
        except Exception:
            pass
'''
text=replace_method(text,'WhatsAppView','_on_wv2_initialized',new_init)

# 3) Desativa recuperacao agressiva. O problema de reabertura passa a ser
# resolvido pelo encerramento real do processo, nao por trocar o navegador vivo.
new_schedule=r'''    def _schedule_whatsapp_recovery(self,reason="falha"):
        try:self._aliyvo_log_webview_startup("falha detectada sem recriacao automatica: "+str(reason))
        except Exception:pass
        self._wa_recovery_scheduled=False
'''
text=replace_method(text,'MainWindow','_schedule_whatsapp_recovery',new_schedule)

new_recreate=r'''    def _recreate_whatsapp_webview(self):
        # Chamadas/WebRTC dependem de uma sessao WebView2 estavel. Nao trocamos
        # o navegador enquanto o ALIYVO esta aberto.
        self._wa_recovery_scheduled=False
        return
'''
text=replace_method(text,'MainWindow','_recreate_whatsapp_webview',new_recreate)

new_watchdog=r'''    def _whatsapp_startup_watchdog(self,generation=None):
        # Watchdog somente informativo. Nunca destroi/recria o WebView2 ativo.
        if bool(getattr(self,"_aliyvo_shutting_down",False)):
            return
        if bool(getattr(self,"_wa_ready_seen",False)):
            return
        try:self._aliyvo_log_webview_startup("watchdog: WhatsApp ainda nao sinalizou DOM carregado")
        except Exception:pass
'''
text=replace_method(text,'MainWindow','_whatsapp_startup_watchdog',new_watchdog)

# 4) O handler de carga nao agenda recriacao. Em sucesso, mantem o mesmo
# WebView2 vivo para chamadas, audio, login e diagnosticos.
new_loaded=r'''    def _on_whatsapp_loaded(self,ok):
        if not ok:
            try:self._aliyvo_log_webview_startup("WebView2 informou falha de inicializacao")
            except Exception:pass
            return
        self._wa_recovery_attempts=0
        self._wa_recovery_scheduled=False
        self._wa_ready_seen=True
        try:self._aliyvo_log_webview_startup("WhatsApp WebView2 carregado e mantido estavel")
        except Exception:pass
        QTimer.singleShot(450,self.apply_aliyvo_whatsapp_theme)
        QTimer.singleShot(2600,self.apply_aliyvo_whatsapp_theme)
'''
text=replace_method(text,'MainWindow','_on_whatsapp_loaded',new_loaded)

# 5) Encerramento conservador: pede ao Qt para sair e fecha a janela tecnica,
# mas nao chama Dispose() no WebView2 manualmente. Isso evita corromper o estado
# de midia e ainda impede que uma janela escondida mantenha o app aberto.
new_shutdown=r'''    def _aliyvo_shutdown_webviews(self):
        if bool(getattr(self,"_aliyvo_webviews_shutdown",False)):
            return
        self._aliyvo_webviews_shutdown=True
        self._aliyvo_shutting_down=True
        self._wa_recovery_scheduled=False
        try:self._aliyvo_log_webview_startup("encerramento conservador iniciado")
        except Exception:pass
        try:
            cat=getattr(self,"_catalog_window",None)
            if cat is not None:
                try:setattr(cat,"_background_mode",False)
                except Exception:pass
                try:cat.hide()
                except Exception:pass
                try:cat.deleteLater()
                except Exception:pass
                self._catalog_window=None
        except Exception:pass
        try:self._aliyvo_log_webview_startup("encerramento conservador concluido")
        except Exception:pass
'''
text=replace_method(text,'MainWindow','_aliyvo_shutdown_webviews',new_shutdown)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched call-safe WebView2 lifecycle and media permissions',version)
