from pathlib import Path
import sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'

s=main.read_text(encoding='utf-8')

if 'ALIYVO_VERSION = "0.23.18"' not in s:
    raise SystemExit('base 0.23.18 nao encontrada')
s=s.replace('ALIYVO_VERSION = "0.23.18"','ALIYVO_VERSION = "0.23.19"',1)
s=s.replace('aliyvo_version="0.23.18"','aliyvo_version="0.23.19"')

# Mantem o objeto do botao apenas por compatibilidade com o layout/codigo antigo,
# mas esconde completamente o recurso enquanto a integracao Ahgora e revisada.
needle='''        self.ponto_toggle=QPushButton("🕒  Ponto")
        self.ponto_toggle.setToolTip("Controle de ponto • 07:50 • 12:08 • 13:30 • 18:00")
'''
replacement='''        self.ponto_toggle=QPushButton("🕒  Ponto")
        self.ponto_toggle.setToolTip("Controle de ponto temporariamente desativado")
        self.ponto_toggle.hide()
'''
if needle not in s:
    raise SystemExit('criacao do botao ponto nao encontrada')
s=s.replace(needle,replacement,1)

# Se ele for adicionado ao layout, permanece oculto.
# Desliga a acao manual.
old='''        self.ponto_toggle.clicked.connect(
            lambda: self._ponto_controller.show_dialog(manual=True)
            if hasattr(self,"_ponto_controller") else None
        )
'''
new='''        self.ponto_toggle.clicked.connect(lambda: None)
'''
if old not in s:
    raise SystemExit('conexao do botao ponto nao encontrada')
s=s.replace(old,new,1)

# Principal: nao cria o controller, nao inicia timer, nao abre popup, nao consulta Ahgora.
old='''        # Controle de ponto 0.22.92: módulo independente, sem consultar DOM do WhatsApp.
        # Usa somente um QTimer single-shot até a próxima batida e um bridge localhost
        # para a extensão do Chrome que protege o acesso ao Sankhya.
        self._ponto_controller=AliyvoPontoController(self,self.ponto_toggle)
        QTimer.singleShot(900,self._ponto_controller.start)
'''
new='''        # Controle de ponto temporariamente retirado.
        # Nao instancia controller, nao inicia timers e nao abre avisos automaticos.
        self._ponto_controller=None
'''
if old not in s:
    raise SystemExit('bootstrap do ponto nao encontrado')
s=s.replace(old,new,1)

main.write_text(s,encoding='utf-8')
print('PATCH_REMOVE_PONTO_V2319=OK')
