from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v45.json').read_text(encoding='utf-8'))
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
    if not new_code.endswith('\n'): new_code+='\n'
    return src[:start]+new_code+src[end:]


# 1) Nao cria HWND nativo para o campo de valor. O winId() usado na versao
# anterior podia transformar o editor em janela nativa e quebrar o reparenting
# do PrazoPanel quando ele era colocado dentro do QScrollArea lateral.
new_claim=r'''    def _claim_editor_focus(self,editor=None):
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
        try:target.setFocus(Qt.FocusReason.OtherFocusReason)
        except Exception:pass
        # Reafirma apenas pelo Qt; nao chama winId()/SetFocus do Windows.
        for delay in (0,60,160):
            try:
                QTimer.singleShot(delay,lambda t=target:t.setFocus(Qt.FocusReason.OtherFocusReason) if t is not None and t.isVisible() else None)
            except Exception:pass
'''
text=replace_method(text,'PrazoPanel','_claim_editor_focus',new_claim)

# 2) O Prazos deixa de ter rota de overlay. Se algum codigo antigo tentar
# posiciona-lo sobre o WhatsApp, apenas mantemos a largura da ferramenta lateral.
new_position=r'''    def position_prazo_overlay(self):
        if getattr(self,"_quick_mode_tool",None)=="prazo":
            self._position_quick_tool("prazo")
            return
        # Nunca mais exibe o Prazos solto sobre o WhatsApp.
        try:
            if hasattr(self,"prazo_panel") and self.prazo_panel.isVisible():
                self.prazo_panel.hide()
        except Exception:pass
'''
text=replace_method(text,'MainWindow','position_prazo_overlay',new_position)

# 3) Qualquer chamada antiga de toggle_prazo_panel e redirecionada para o
# mecanismo unico das Acoes rapidas, que hospeda o painel no lado direito.
new_toggle=r'''    def toggle_prazo_panel(self):
        if getattr(self,"_quick_mode_tool",None)=="prazo":
            self._restore_quick_actions()
            return
        self._open_quick_tool("prazo")
'''
text=replace_method(text,'MainWindow','toggle_prazo_panel',new_toggle)

# 4) Expandir/recolher so altera a largura do host lateral. Nao chama show()
# diretamente e nao calcula geometria sobre o WhatsApp.
new_expand=r'''    def toggle_prazo_expand(self):
        if getattr(self,"_quick_mode_tool",None)!="prazo":
            self._open_quick_tool("prazo")
            return
        panel=self.prazo_panel
        panel.expanded=not bool(getattr(panel,"expanded",False))
        if panel.expanded:
            panel.expand_btn.setText("↩")
            panel.expand_btn.setToolTip("Voltar ao tamanho compacto")
        else:
            panel.expand_btn.setText("⛶")
            panel.expand_btn.setToolTip("Expandir painel de prazos")
        self._position_quick_tool("prazo")
        try:self._set_prazo_focus_guard(True,panel.valor)
        except Exception:pass
'''
text=replace_method(text,'MainWindow','toggle_prazo_expand',new_expand)

# 5) Fechar Prazos nunca percorre a rota antiga. Ou recolhe o host lateral,
# ou simplesmente esconde um painel legado que tenha sobrado visivel.
new_close=r'''    def _close_tool_panel(self, tool):
        if tool=="prazo":
            try:self._set_prazo_focus_guard(False)
            except Exception:pass
            if getattr(self,"_quick_mode_tool",None)=="prazo":
                self._restore_quick_actions()
            else:
                try:self.prazo_panel.hide()
                except Exception:pass
            return
        if getattr(self,"_quick_mode_tool",None)==tool:
            self._restore_quick_actions()
            return

        if tool in ("technical","diagnostic","update","plate"):
            panel=self._tool_panel(tool)
            if panel is not None:
                panel.hide()
            self._restore_quick_actions()
            return

        {
            "lens": self.toggle_lens_panel,
            "chat": self.toggle_chat_panel,
            "audio": self.toggle_audio_panel,
            "campaign": self.toggle_campaign_panel,
        }[tool]()
'''
text=replace_method(text,'MainWindow','_close_tool_panel',new_close)

# 6) Na abertura da ferramenta, depois de setWidget, reafirma que o Prazos
# pertence ao viewport do QScrollArea. Isto protege contra codigo legado e
# contra handles nativos antigos ainda existentes na sessao atual.
old='''        self.quick_scroll.setWidget(panel)\n        self.quick_scroll.show()\n        self._quick_mode_tool=tool\n'''
new='''        self.quick_scroll.setWidget(panel)\n        self.quick_scroll.show()\n        self._quick_mode_tool=tool\n        if tool=="prazo":\n            try:\n                viewport=self.quick_scroll.viewport()\n                if panel.parentWidget() is not viewport:\n                    panel.setParent(viewport)\n                panel.move(0,0)\n            except Exception:pass\n'''
if old not in text:raise SystemExit('_open_quick_tool setWidget anchor not found')
text=text.replace(old,new,1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched Prazos single right-side host',version)
