from pathlib import Path
import sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
text=main.read_text(encoding='utf-8')

if 'ALIYVO_VERSION = "0.23.04"' not in text:
    raise SystemExit('base esperada 0.23.04 nao encontrada')

text=text.replace('ALIYVO_VERSION = "0.23.04"','ALIYVO_VERSION = "0.23.05"',1)

old='''        nav_lay.addWidget(self.campaign_toggle)
        nav_lay.addWidget(self.prazo_toggle)
        nav_lay.addWidget(self.chat_toggle)
        nav_lay.addWidget(self.nav_lens_toggle)
        nav_lay.addWidget(self.plate_toggle)
'''
new='''        nav_lay.addWidget(self.campaign_toggle)
        # 0.23.05: Prazos, Assistente e Busca por imagem já existem na lateral.
        # Mantemos os objetos vivos para preservar integrações/atalhos existentes,
        # mas não duplicamos os botões na barra superior.
        self.prazo_toggle.hide()
        self.chat_toggle.hide()
        self.nav_lens_toggle.hide()
        nav_lay.addWidget(self.plate_toggle)
'''
if text.count(old)!=1:
    raise SystemExit(f'bloco de navegacao esperado 1x, encontrado {text.count(old)}')
text=text.replace(old,new,1)

text=text.replace('aliyvo_version="0.23.04"','aliyvo_version="0.23.05"')
main.write_text(text,encoding='utf-8')
print('PATCH_NAV_CLEAN_V2305=OK')
