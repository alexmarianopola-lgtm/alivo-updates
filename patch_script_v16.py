from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v16.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.30 - experimento reversivel: troca visualmente o Assistente Tecnico
# pelo buscador oficial de produtos Somaforce, mantendo toda a logica antiga no codigo.
if 'class SomaforceCatalogPanel(QWidget):' not in text:
    marker='class TechnicalAssistPanel(QWidget):\n'
    if marker not in text:
        raise SystemExit('TechnicalAssistPanel marker not found')
    panel=r'''
class SomaforceCatalogPanel(QWidget):
    URL = "https://somaforce.com.br/buscapecas/index.php"

    def __init__(self,parent=None):
        super().__init__(parent)
        self.expanded=False
        self.on_analyze=None
        self.setObjectName("somaforceCatalogPanel")
        self.setStyleSheet("""
            QWidget#somaforceCatalogPanel{background:#F8FAFC;color:#0F172A;}
            QWidget#somaforceCatalogPanel QLabel{color:#0F172A;background:transparent;}
            QWidget#somaforceCatalogPanel QPushButton{
                background:#0A2236;color:#F4FAF8;border:1px solid #173B52;
                border-radius:6px;padding:7px;font-weight:700;
            }
            QWidget#somaforceCatalogPanel QPushButton:hover{border-color:#20E983;background:#0D303B;}
        """)
        lay=QVBoxLayout(self)
        lay.setContentsMargins(5,5,5,5)
        lay.setSpacing(5)

        head=QHBoxLayout()
        title=QLabel("🔎 Busca de Produtos Somaforce")
        title.setStyleSheet("font-size:14px;font-weight:800;color:#073B4C;")
        head.addWidget(title)
        head.addStretch(1)
        self.refresh_btn=QPushButton("↻")
        self.refresh_btn.setToolTip("Recarregar buscador")
        self.refresh_btn.setFixedWidth(34)
        self.external_btn=QPushButton("↗")
        self.external_btn.setToolTip("Abrir no navegador")
        self.external_btn.setFixedWidth(34)
        self.expand_btn=QPushButton("⛶")
        self.expand_btn.setFixedWidth(34)
        self.close_btn=QPushButton("◀")
        self.close_btn.setFixedWidth(34)
        head.addWidget(self.refresh_btn)
        head.addWidget(self.external_btn)
        head.addWidget(self.expand_btn)
        head.addWidget(self.close_btn)
        lay.addLayout(head)

        info=QLabel("Buscador oficial Somaforce. A análise antiga continua preservada no ALIYVO para podermos voltar se necessário.")
        info.setWordWrap(True)
        info.setStyleSheet("color:#64748B;font-size:9px;")
        lay.addWidget(info)

        self.browser=QWebEngineView(self)
        self.browser.setUrl(QUrl(self.URL))
        lay.addWidget(self.browser,1)

        self.refresh_btn.clicked.connect(self.browser.reload)
        self.external_btn.clicked.connect(self._open_external)

    def _open_external(self):
        try:
            QDesktopServices.openUrl(QUrl(self.URL))
        except Exception:
            pass

    # Compatibilidade: se algum trecho antigo ainda chamar estes metodos,
    # o painel permanece estável e não dispara leitura do WhatsApp.
    def set_loading(self):
        pass
    def render_error(self,message):
        pass
    def render_payload(self,data):
        pass

'''
    text=text.replace(marker,panel+marker,1)

# Troca somente a instancia visual. O TechnicalAssistPanel antigo permanece no arquivo.
old='self.technical_panel=TechnicalAssistPanel(self.web_host)'
if old not in text:
    raise SystemExit('technical panel instantiation not found')
text=text.replace(old,'self.technical_panel=SomaforceCatalogPanel(self.web_host)',1)

# O clique agora abre o buscador, sem rodar análise/leitura DOM do WhatsApp.
old_method='''    def _technical_open_and_analyze(self):\n        self._open_quick_tool("technical")\n        QTimer.singleShot(0,self._technical_analyze_current)'''
if old_method not in text:
    raise SystemExit('technical open method not found')
new_method='''    def _technical_open_and_analyze(self):\n        self._open_quick_tool("technical")\n        try:\n            if hasattr(self.technical_panel,"browser") and not self.technical_panel.browser.url().isValid():\n                self.technical_panel.browser.setUrl(QUrl(self.technical_panel.URL))\n        except Exception:\n            pass'''
text=text.replace(old_method,new_method,1)

# Textos do botão principal e restauração de rótulo.
text=text.replace('⚡  Analisar pedido atual','🔎  Busca Somaforce')
text=text.replace('⚡ Analisar pedido atual','🔎 Busca Somaforce')

# Um pouco mais de espaço para o site dentro da lateral.
text=text.replace('"technical": 520','"technical": 720')
text=text.replace('"technical": 760','"technical": 980')

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched Somaforce catalog panel',version)
