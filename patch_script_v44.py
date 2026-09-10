from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v44.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)


def method_source(src,class_name,method_name):
    tree=ast.parse(src)
    cls=next((n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==class_name),None)
    if cls is None: raise SystemExit(f'class {class_name} not found')
    target=next((n for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==method_name),None)
    if target is None: raise SystemExit(f'method {class_name}.{method_name} not found')
    lines=src.splitlines(keepends=True)
    return ''.join(lines[target.lineno-1:target.end_lineno])


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

# 1) Registra falhas reais de inicializacao. Nao apaga nem altera o perfil.
new_init=r'''    def _on_wv2_initialized(self,*args):
        try:
            failed=bool(args and args[0] is False)
            if not failed:
                return
            detail=""
            try:
                if len(args)>1:detail=str(args[1] or "")
            except Exception:pass
            try:
                log_dir=ALIYVO_USER_DIR/"logs"
                log_dir.mkdir(parents=True,exist_ok=True)
                import time as _time
                with (log_dir/"WEBVIEW2_STARTUP.log").open("a",encoding="utf-8") as _f:
                    _f.write("["+_time.strftime("%Y-%m-%d %H:%M:%S")+"] falha: "+detail[:1200]+"\n")
            except Exception:pass
            # O qtwebview2 0.5.0 remove o widget quando a inicializacao falha.
            # Avisamos o MainWindow antes para ele recriar um navegador novo
            # apontando para o MESMO perfil persistente do WhatsApp.
            self.loadFinished.emit(False)
        except Exception:
            pass
'''
text=replace_method(text,'WhatsAppView','_on_wv2_initialized',new_init)

# 2) Inicializa estado de recuperacao logo apos criar o WhatsApp.
old='''        self.web=WhatsAppView()\n\n        self.web_host=QWidget()\n'''
new='''        self._aliyvo_shutting_down=False\n        self._aliyvo_webviews_shutdown=False\n        self._wa_recovery_attempts=0\n        self._wa_recovery_scheduled=False\n        self._wa_recovery_generation=0\n        self.web=WhatsAppView()\n\n        self.web_host=QWidget()\n'''
if old not in text:raise SystemExit('MainWindow self.web anchor not found')
text=text.replace(old,new,1)

# O bloco antigo reinicializava apenas attempts/ready mais abaixo. Mantemos ready,
# mas nao sobrescrevemos o estado de recuperacao criado antes do WebView.
old='''        self._wa_recovery_attempts=0\n        self._wa_ready_seen=False\n'''
new='''        self._wa_ready_seen=False\n'''
if old not in text:raise SystemExit('old wa recovery init anchor not found')
text=text.replace(old,new,1)

# 3) Metodos robustos de descarte, recriacao e watchdog.
anchor='    def _on_whatsapp_loaded(self,ok):\n'
if anchor not in text:raise SystemExit('_on_whatsapp_loaded anchor not found')
helpers=r'''    def _aliyvo_log_webview_startup(self,message):
        try:
            log_dir=ALIYVO_USER_DIR/"logs"
            log_dir.mkdir(parents=True,exist_ok=True)
            import time as _time
            with (log_dir/"WEBVIEW2_STARTUP.log").open("a",encoding="utf-8") as f:
                f.write("["+_time.strftime("%Y-%m-%d %H:%M:%S")+"] "+str(message)[:1500]+"\n")
        except Exception:
            pass

    def _aliyvo_dispose_webview_widget(self,widget):
        if widget is None:return
        try:
            native=getattr(widget,"_webview",None)
            if native is not None:
                try:native.Visible=False
                except Exception:pass
                try:
                    if not bool(getattr(native,"IsDisposed",False)):
                        native.Dispose()
                except Exception:
                    try:native.Dispose()
                    except Exception:pass
        except Exception:pass
        try:setattr(widget,"is_ready",False)
        except Exception:pass
        try:
            executor=getattr(widget,"_wsgi_executor",None)
            if executor is not None:
                try:executor.shutdown(wait=False,cancel_futures=True)
                except TypeError:executor.shutdown(wait=False)
                except Exception:pass
        except Exception:pass

    def _schedule_whatsapp_recovery(self,reason="falha"):
        if bool(getattr(self,"_aliyvo_shutting_down",False)):
            return
        if bool(getattr(self,"_wa_recovery_scheduled",False)):
            return
        attempts=int(getattr(self,"_wa_recovery_attempts",0) or 0)
        if attempts>=5:
            self._aliyvo_log_webview_startup("recuperacao pausada apos 5 tentativas: "+str(reason))
            return
        self._wa_recovery_scheduled=True
        delay=(700,1300,2200,3500,5000)[attempts]
        self._aliyvo_log_webview_startup(
            "agendando recriacao WhatsApp tentativa "+str(attempts+1)+" em "+str(delay)+"ms: "+str(reason)
        )
        QTimer.singleShot(delay,self._recreate_whatsapp_webview)

    def _recreate_whatsapp_webview(self):
        if bool(getattr(self,"_aliyvo_shutting_down",False)):
            return
        self._wa_recovery_scheduled=False
        self._wa_recovery_attempts=int(getattr(self,"_wa_recovery_attempts",0) or 0)+1
        self._wa_recovery_generation=int(getattr(self,"_wa_recovery_generation",0) or 0)+1
        generation=self._wa_recovery_generation
        old=getattr(self,"web",None)
        self._aliyvo_log_webview_startup("recriando WhatsApp tentativa "+str(self._wa_recovery_attempts))
        try:
            self.web_host_layout.removeWidget(old)
        except Exception:pass
        self._aliyvo_dispose_webview_widget(old)
        try:
            if old is not None:
                old.hide()
                old.setParent(None)
                old.deleteLater()
        except Exception:pass
        try:
            new_web=WhatsAppView()
            new_web.setMinimumHeight(0)
            new_web.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
            new_web.media_download_callback=self._handle_whatsapp_media_download
            try:new_web.audio_download_callback=self._audio_native_download_ready
            except Exception:pass
            new_web.loadFinished.connect(self._on_whatsapp_loaded)
            self.web=new_web
            self.web_host_layout.addWidget(new_web)
            new_web.show()
            new_web.raise_()
            # Se nem sucesso nem falha chegarem, considera inicializacao presa.
            QTimer.singleShot(12000,lambda g=generation:self._whatsapp_startup_watchdog(g))
        except Exception as e:
            self._aliyvo_log_webview_startup("erro ao recriar widget: "+repr(e))
            self._schedule_whatsapp_recovery("excecao ao recriar")

    def _whatsapp_startup_watchdog(self,generation=None):
        if bool(getattr(self,"_aliyvo_shutting_down",False)):
            return
        if generation is not None and generation!=getattr(self,"_wa_recovery_generation",None):
            return
        web=getattr(self,"web",None)
        try:
            native=getattr(web,"_webview",None)
            ready=bool(getattr(web,"is_ready",False)) and native is not None and not bool(getattr(native,"IsDisposed",False))
        except Exception:
            ready=False
        if ready:
            return
        self._schedule_whatsapp_recovery("watchdog: WebView2 nao ficou pronto")

    def _aliyvo_shutdown_webviews(self):
        if bool(getattr(self,"_aliyvo_webviews_shutdown",False)):
            return
        self._aliyvo_webviews_shutdown=True
        self._aliyvo_shutting_down=True
        self._wa_recovery_scheduled=False
        self._aliyvo_log_webview_startup("encerramento limpo iniciado")
        # Fecha qualquer WebView2 pertencente ao ALIYVO, inclusive janelas
        # tecnicas antigas que possam estar escondidas em segundo plano.
        seen=set()
        app=QApplication.instance()
        widgets=[]
        try:
            if app is not None:widgets=list(app.allWidgets())
        except Exception:pass
        try:widgets.append(getattr(self,"web",None))
        except Exception:pass
        try:
            cat=getattr(self,"_catalog_window",None)
            if cat is not None:widgets.append(getattr(cat,"web",None))
        except Exception:pass
        for widget in widgets:
            if widget is None:continue
            try:
                is_wv=isinstance(widget,QtWebView2Widget)
            except Exception:
                is_wv=hasattr(widget,"_webview") and hasattr(widget,"_wsgi_executor")
            if not is_wv:continue
            ident=id(widget)
            if ident in seen:continue
            seen.add(ident)
            self._aliyvo_dispose_webview_widget(widget)
        try:
            cat=getattr(self,"_catalog_window",None)
            if cat is not None:
                cat.hide()
                cat.deleteLater()
                self._catalog_window=None
        except Exception:pass
        self._aliyvo_log_webview_startup("encerramento limpo concluido")

    def closeEvent(self,event):
        try:self._aliyvo_shutdown_webviews()
        except Exception:pass
        try:event.accept()
        except Exception:pass
        try:
            app=QApplication.instance()
            if app is not None:QTimer.singleShot(0,app.quit)
        except Exception:pass

'''
text=text.replace(anchor,helpers+anchor,1)

# 4) Falha de inicializacao agora aciona recuperacao; sucesso zera tentativas.
old_method=method_source(text,'MainWindow','_on_whatsapp_loaded')
new_method=r'''    def _on_whatsapp_loaded(self,ok):
        if not ok:
            self._schedule_whatsapp_recovery("sinal de falha da inicializacao WebView2")
            return
        self._wa_recovery_attempts=0
        self._wa_recovery_scheduled=False
        self._wa_ready_seen=True
        self._aliyvo_log_webview_startup("WhatsApp WebView2 carregado")
        # WhatsApp primeiro: apenas duas aplicacoes de tema na abertura.
        QTimer.singleShot(450,self.apply_aliyvo_whatsapp_theme)
        QTimer.singleShot(2600,self.apply_aliyvo_whatsapp_theme)
'''
text=replace_method(text,'MainWindow','_on_whatsapp_loaded',new_method)

# 5) Watchdog tambem protege a primeira abertura, caso a biblioteca fique presa
# sem emitir sucesso nem falha.
old='''        self.web.loadFinished.connect(self._on_whatsapp_loaded)\n\n        # Compatibilidade com métodos antigos\n'''
new='''        self.web.loadFinished.connect(self._on_whatsapp_loaded)\n        QTimer.singleShot(12000,lambda:self._whatsapp_startup_watchdog(0))\n\n        # Compatibilidade com métodos antigos\n'''
if old not in text:raise SystemExit('loadFinished connect anchor not found')
text=text.replace(old,new,1)

# 6) Garante a mesma limpeza quando o app sair por atualizacao ou outro caminho,
# nao apenas pelo X da janela.
old='''    win=MainWindow()\n    win.show()\n    sys.exit(app.exec())\n'''
new='''    win=MainWindow()\n    try:app.aboutToQuit.connect(win._aliyvo_shutdown_webviews)\n    except Exception:pass\n    win.show()\n    sys.exit(app.exec())\n'''
if old not in text:raise SystemExit('__main__ win anchor not found')
text=text.replace(old,new,1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched WhatsApp reopen recovery and clean shutdown',version)
