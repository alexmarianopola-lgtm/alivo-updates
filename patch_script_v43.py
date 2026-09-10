from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v43.json').read_text(encoding='utf-8'))
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

# 1) WebView2 nao pode reassumir foco por chamadas programaticas enquanto
# o usuario esta editando o painel de Prazos.
new_wpp_focus='''    def setFocus(self,*args,**kwargs):
        if bool(getattr(self,"_aliyvo_focus_blocked",False)):
            try:super().clearFocus()
            except Exception:pass
            return
        try:
            super().setFocus(*args,**kwargs)
        except Exception:
            pass
        try:
            if getattr(self,"_webview",None):
                self._webview.Focus()
        except Exception:
            pass
'''
text=replace_method(text,'WhatsAppView','setFocus',new_wpp_focus)

# 2) O proprio PrazoPanel reafirma o foco no editor clicado. No Windows,
# SetFocus no HWND do editor vence a janela nativa do Edge/WebView2.
anchor='    def parse_valor(self):\n'
if anchor not in text:raise SystemExit('PrazoPanel parse_valor anchor not found')
helpers=r'''    def _claim_editor_focus(self,editor=None):
        target=editor or getattr(self,"valor",None)
        try:
            win=self.window()
            web=getattr(win,"web",None)
            if web is not None:setattr(web,"_aliyvo_focus_blocked",True)
            release=getattr(win,"_release_whatsapp_focus",None)
            if callable(release):release()
            try:win.activateWindow()
            except Exception:pass
        except Exception:pass
        if target is None:return
        try:target.setFocus(Qt.FocusReason.MouseFocusReason)
        except Exception:pass
        try:
            import sys as _sys,ctypes as _ctypes
            if _sys.platform=="win32":
                hwnd=int(target.winId())
                if hwnd:_ctypes.windll.user32.SetFocus(hwnd)
        except Exception:pass
        try:
            QTimer.singleShot(0,lambda t=target:t.setFocus(Qt.FocusReason.OtherFocusReason) if t is not None and t.isVisible() else None)
            QTimer.singleShot(60,lambda t=target:t.setFocus(Qt.FocusReason.OtherFocusReason) if t is not None and t.isVisible() else None)
        except Exception:pass

    def eventFilter(self,obj,event):
        try:
            if obj in (getattr(self,"valor",None),getattr(self,"msg",None)):
                if event.type() in (QEvent.Type.MouseButtonPress,QEvent.Type.FocusIn):
                    # Libera o WebView2 imediatamente; o clique continua normalmente.
                    try:
                        win=self.window();web=getattr(win,"web",None)
                        if web is not None:setattr(web,"_aliyvo_focus_blocked",True)
                        release=getattr(win,"_release_whatsapp_focus",None)
                        if callable(release):release()
                    except Exception:pass
                    QTimer.singleShot(0,lambda t=obj:self._claim_editor_focus(t))
        except Exception:pass
        return super().eventFilter(obj,event)

    def mousePressEvent(self,event):
        try:
            win=self.window();web=getattr(win,"web",None)
            if web is not None:setattr(web,"_aliyvo_focus_blocked",True)
            release=getattr(win,"_release_whatsapp_focus",None)
            if callable(release):release()
        except Exception:pass
        super().mousePressEvent(event)

'''
text=text.replace(anchor,helpers+anchor,1)

# Instala o filtro nos dois editores do painel.
old='''        self.valor=QLineEdit()\n        self.valor.setFocusPolicy(Qt.FocusPolicy.StrongFocus)\n        self.valor.setPlaceholderText("Ex.: 1850,00")\n'''
new='''        self.valor=QLineEdit()\n        self.valor.setFocusPolicy(Qt.FocusPolicy.StrongFocus)\n        self.valor.installEventFilter(self)\n        self.valor.setPlaceholderText("Ex.: 1850,00")\n'''
if old not in text:raise SystemExit('Prazo valor anchor not found')
text=text.replace(old,new,1)
old='''        self.msg=QTextEdit()\n        self.msg.setMaximumHeight(130)\n'''
new='''        self.msg=QTextEdit()\n        self.msg.setFocusPolicy(Qt.FocusPolicy.StrongFocus)\n        self.msg.installEventFilter(self)\n        self.msg.setMaximumHeight(130)\n'''
if old not in text:raise SystemExit('Prazo msg anchor not found')
text=text.replace(old,new,1)

# 3) Trava/destrava centralizada no MainWindow.
anchor='    def _release_whatsapp_focus(self):\n'
if anchor not in text:raise SystemExit('release focus anchor not found')
main_helper=r'''    def _set_prazo_focus_guard(self,enabled=True,editor=None):
        enabled=bool(enabled)
        try:setattr(self.web,"_aliyvo_focus_blocked",enabled)
        except Exception:pass
        if enabled:
            try:self._release_whatsapp_focus()
            except Exception:pass
            target=editor
            if target is None:
                try:target=self.prazo_panel.valor
                except Exception:target=None
            if target is not None:
                try:QTimer.singleShot(0,lambda t=target:self.prazo_panel._claim_editor_focus(t))
                except Exception:pass

'''
text=text.replace(anchor,main_helper+anchor,1)

# 4) Abrir Prazos liga a trava; abrir outra ferramenta desliga.
ms=method_source(text,'MainWindow','_open_quick_tool')
needle='''        panel=self._tool_panel(tool)\n        if panel is None:\n            return\n'''
if needle not in ms:raise SystemExit('_open_quick_tool anchor not found')
ms=ms.replace(needle,needle+'''\n        try:self._set_prazo_focus_guard(tool=="prazo")\n        except Exception:pass\n''',1)
text=replace_method(text,'MainWindow','_open_quick_tool',ms)

# Voltar para Acoes rapidas sempre libera a trava.
ms=method_source(text,'MainWindow','_restore_quick_actions')
line='''    def _restore_quick_actions(self):\n'''
if not ms.startswith(line):raise SystemExit('_restore_quick_actions header unexpected')
ms=ms.replace(line,line+'''        try:self._set_prazo_focus_guard(False)\n        except Exception:pass\n''',1)
text=replace_method(text,'MainWindow','_restore_quick_actions',ms)

# Fechar o painel tambem libera a trava antes de qualquer outra acao.
ms=method_source(text,'MainWindow','_close_tool_panel')
line='''    def _close_tool_panel(self, tool):\n'''
if not ms.startswith(line):raise SystemExit('_close_tool_panel header unexpected')
ms=ms.replace(line,line+'''        if tool=="prazo":\n            try:self._set_prazo_focus_guard(False)\n            except Exception:pass\n''',1)
text=replace_method(text,'MainWindow','_close_tool_panel',ms)

# A abertura antiga via overlay superior tambem recebe a mesma protecao.
ms=method_source(text,'MainWindow','toggle_prazo_panel')
old='''        if self.prazo_panel.isVisible():\n            self.prazo_panel.hide()\n'''
new='''        if self.prazo_panel.isVisible():\n            try:self._set_prazo_focus_guard(False)\n            except Exception:pass\n            self.prazo_panel.hide()\n'''
if old not in ms:raise SystemExit('toggle prazo hide anchor not found')
ms=ms.replace(old,new,1)
old='''            self.prazo_panel.show()\n            self.prazo_panel.raise_()\n'''
new='''            self.prazo_panel.show()\n            self.prazo_panel.raise_()\n            try:self._set_prazo_focus_guard(True,self.prazo_panel.valor)\n            except Exception:pass\n'''
if old not in ms:raise SystemExit('toggle prazo show anchor not found')
ms=ms.replace(old,new,1)
text=replace_method(text,'MainWindow','toggle_prazo_panel',ms)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched PrazoPanel focus guard',version)
