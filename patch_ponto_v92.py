from pathlib import Path
import shutil
import sys

root = Path(sys.argv[1])
main = root / "_app" / "main.py"
source_module = Path(__file__).resolve().parent / "ponto_module_v92.py"
target_module = root / "_app" / "aliyvo_ponto.py"

text = main.read_text(encoding="utf-8")

def one(old, new, label):
    global text
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"{label}: esperado 1, encontrado {n}")
    text = text.replace(old, new, 1)

one('ALIYVO_VERSION = "0.22.91"', 'ALIYVO_VERSION = "0.22.92"', "version")

# Import isolado do módulo. Mantém WhatsApp, Assistente e updater intactos.
anchor = 'ALIYVO_VERSION = "0.22.92"\n'
one(anchor, anchor + 'from aliyvo_ponto import AliyvoPontoController\n', "point import")

one(
'''        self.attendance_toggle=QPushButton("📊  Diagnóstico")
        self.reminder_toggle=QPushButton("⏰  Lembretes")
''',
'''        self.attendance_toggle=QPushButton("📊  Diagnóstico")
        self.reminder_toggle=QPushButton("⏰  Lembretes")
        self.ponto_toggle=QPushButton("🕒  Ponto")
        self.ponto_toggle.setToolTip("Controle de ponto • 07:50 • 12:08 • 13:30 • 18:00")
''',
"point navbar button",
)

one(
'''        nav_lay.addWidget(self.attendance_toggle)
        nav_lay.addWidget(self.reminder_toggle)
        nav_lay.addStretch(1)
''',
'''        nav_lay.addWidget(self.attendance_toggle)
        nav_lay.addWidget(self.reminder_toggle)
        nav_lay.addWidget(self.ponto_toggle)
        nav_lay.addStretch(1)
''',
"point navbar placement",
)

one(
'''        self.attendance_toggle.clicked.connect(self._diagnostic_show_dialog)
        self.reminder_toggle.clicked.connect(self._reminder_show_dialog)
''',
'''        self.attendance_toggle.clicked.connect(self._diagnostic_show_dialog)
        self.reminder_toggle.clicked.connect(self._reminder_show_dialog)
        self.ponto_toggle.clicked.connect(
            lambda: self._ponto_controller.show_dialog(manual=True)
            if hasattr(self,"_ponto_controller") else None
        )
''',
"point signal",
)

one(
'''        self.setCentralWidget(self.splitter)
        QTimer.singleShot(650,self._attendance_bootstrap)
''',
'''        self.setCentralWidget(self.splitter)

        # Controle de ponto 0.22.92: módulo independente, sem consultar DOM do WhatsApp.
        # Usa somente um QTimer single-shot até a próxima batida e um bridge localhost
        # para a extensão do Chrome que protege o acesso ao Sankhya.
        self._ponto_controller=AliyvoPontoController(self,self.ponto_toggle)
        QTimer.singleShot(900,self._ponto_controller.start)

        QTimer.singleShot(650,self._attendance_bootstrap)
''',
"point controller startup",
)

main.write_text(text, encoding="utf-8")
shutil.copy2(source_module, target_module)

# Copia a extensão para dentro do pacote final, sem instalar nada automaticamente.
ext_source = Path(__file__).resolve().parent / "extension_ponto_v92"
ext_target = root / "EXTENSAO_PONTO_SANKHYA"
if ext_target.exists():
    shutil.rmtree(ext_target)
shutil.copytree(ext_source, ext_target)

(root / "LEIA-ME-PONTO-02292.txt").write_text(
    """ALIYVO 0.22.92 RC - CONTROLE DE PONTO

Horários configurados:
07:50 - Entrada
12:08 - Saída para almoço
13:30 - Volta do almoço
18:00 - Saída final
Segunda a sexta-feira.

O módulo NÃO bate ponto automaticamente.
O módulo NÃO guarda matrícula nem senha.
Você continua fazendo a batida oficial no Ahgora Ponto Online.

A pasta EXTENSAO_PONTO_SANKHYA contém a extensão auxiliar do Chrome.
Ela bloqueia o Sankhya quando o ALIYVO informa que existe uma batida pendente.
Se o ALIYVO estiver fechado, a extensão usa os mesmos horários como contingência.

Instalação da extensão:
1. Abra chrome://extensions
2. Ative Modo do desenvolvedor
3. Clique em Carregar sem compactação
4. Selecione a pasta EXTENSAO_PONTO_SANKHYA
5. Deixe Ahgora Ponto Online e ALIYVO Ponto Guard fixados no Chrome.

Esta é uma versão RC: o build e os testes automatizados podem passar, mas o
funcionamento real com seu Chrome/Ahgora/Sankhya precisa ser confirmado no seu PC.
""",
    encoding="utf-8",
)

print("PATCH_PONTO_V92=OK")
