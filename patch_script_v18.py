from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v18.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.32 - atalho simples para consulta de placa/chassi usando o app Android
# Consulta Placa Preco e Multas (package br.com.consultaplacasfipe) via BlueStacks.
# Sem API paga e sem alterar a busca Somaforce que ja esta funcionando.

if '_aliyvo_open_plate_lookup_app' not in text:
    code=r'''

ALIYVO_PLATE_APP_PACKAGE = "br.com.consultaplacasfipe"
ALIYVO_PLATE_PLAY_URL = "https://play.google.com/store/apps/details?id=br.com.consultaplacasfipe"
ALIYVO_BLUESTACKS_URL = "https://www.bluestacks.com/pt-br/index.html"


def _aliyvo_find_bluestacks_player():
    try:
        import os
        candidates=[]
        for base in [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), r"C:\\Program Files"]:
            if base:
                candidates.extend([
                    Path(base)/"BlueStacks_nxt"/"HD-Player.exe",
                    Path(base)/"BlueStacks"/"HD-Player.exe",
                ])
        for c in candidates:
            try:
                if c.exists(): return str(c)
            except Exception:
                pass
    except Exception:
        pass
    return ""


def _aliyvo_open_url(url):
    try:
        import webbrowser
        webbrowser.open(url)
        return True
    except Exception:
        try:
            QDesktopServices.openUrl(QUrl(url))
            return True
        except Exception:
            return False


def _aliyvo_open_plate_lookup_app(parent=None):
    player=_aliyvo_find_bluestacks_player()
    if not player:
        try:
            box=QMessageBox(parent)
            box.setWindowTitle("Busca de placa")
            box.setIcon(QMessageBox.Icon.Information)
            box.setText("Para usar o app de consulta de placa no computador, instale o BlueStacks 5 uma unica vez.")
            box.setInformativeText("Depois instale nele o app 'Consulta Placa Preco e Multas'. Nas proximas vezes o ALIYVO tentara abrir o app direto.")
            install_btn=box.addButton("1. Baixar BlueStacks",QMessageBox.ButtonRole.AcceptRole)
            app_btn=box.addButton("2. Abrir app no Google Play",QMessageBox.ButtonRole.ActionRole)
            box.addButton("Fechar",QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is install_btn:
                _aliyvo_open_url(ALIYVO_BLUESTACKS_URL)
            elif box.clickedButton() is app_btn:
                _aliyvo_open_url(ALIYVO_PLATE_PLAY_URL)
        except Exception:
            _aliyvo_open_url(ALIYVO_BLUESTACKS_URL)
        return

    # O BlueStacks pode usar nomes diferentes de instancia. Tentamos os mais comuns.
    # O comando launchApp e o mesmo usado pelos atalhos de desktop do BlueStacks.
    try:
        import subprocess
        instances=["Rvc64","Pie64","Tiramisu64","Nougat64","Nougat32"]
        started=False
        for inst in instances:
            try:
                subprocess.Popen(
                    [player,"--instance",inst,"--cmd","launchApp","--package",ALIYVO_PLATE_APP_PACKAGE,"--source","desktop_shortcut"],
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL
                )
                started=True
                break
            except Exception:
                pass
        if not started:
            subprocess.Popen([player],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except Exception:
        try:
            import subprocess
            subprocess.Popen([player])
        except Exception:
            _aliyvo_open_url(ALIYVO_PLATE_PLAY_URL)


_aliyvo_plate_button_attempts=0

def _aliyvo_install_plate_lookup_button():
    global _aliyvo_plate_button_attempts
    _aliyvo_plate_button_attempts+=1
    try:
        app=QApplication.instance()
        if not app: return
        for w in app.allWidgets():
            try:
                if isinstance(w,QPushButton) and w.objectName()=="aliyvoPlateLookupButton":
                    return
            except Exception:
                pass

        target=None
        # Preferimos colocar logo depois da Busca Somaforce.
        for w in app.allWidgets():
            try:
                if isinstance(w,QPushButton) and "busca somaforce" in str(w.text() or "").lower():
                    target=w; break
            except Exception:
                pass
        # Fallback: coloca perto de Atualizacoes.
        if target is None:
            for w in app.allWidgets():
                try:
                    if isinstance(w,QPushButton) and "atualiza" in str(w.text() or "").lower():
                        target=w; break
                except Exception:
                    pass

        if target is not None and target.parentWidget() is not None:
            parent=target.parentWidget(); layout=parent.layout()
            if layout is not None:
                btn=QPushButton("🚘 Buscar placa",parent)
                btn.setObjectName("aliyvoPlateLookupButton")
                btn.setToolTip("Abrir consulta de placa/chassi no app Android")
                try: btn.setStyleSheet(target.styleSheet())
                except Exception: pass
                try: btn.setMinimumHeight(target.minimumHeight())
                except Exception: pass
                btn.clicked.connect(lambda checked=False,p=parent:_aliyvo_open_plate_lookup_app(p))
                inserted=False
                if hasattr(layout,"insertWidget"):
                    for i in range(layout.count()):
                        item=layout.itemAt(i)
                        if item and item.widget() is target:
                            layout.insertWidget(i+1,btn); inserted=True; break
                if not inserted:
                    try: layout.addWidget(btn); inserted=True
                    except Exception: pass
                if inserted: return
    except Exception:
        pass
    if _aliyvo_plate_button_attempts<10:
        QTimer.singleShot(1000,_aliyvo_install_plate_lookup_button)

'''
    main_block=re.search(r'(?m)^if\s+__name__\s*==\s*["\']__main__["\']\s*:',text)
    if not main_block:
        raise SystemExit('main block not found for plate lookup code')
    text=text[:main_block.start()]+code+text[main_block.start():]

    # Agenda a instalacao do botao logo apos a criacao do QApplication.
    m=re.search(r'(?m)^(?P<indent>\s*)(?P<var>[A-Za-z_]\w*)\s*=\s*QApplication\s*\([^\n]*\)\s*$',text)
    if not m:
        raise SystemExit('QApplication creation not found for plate lookup button')
    pos=m.end(); indent=m.group('indent')
    text=text[:pos]+'\n'+indent+'QTimer.singleShot(1800, _aliyvo_install_plate_lookup_button)'+text[pos:]

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched plate lookup Android launcher',version)
