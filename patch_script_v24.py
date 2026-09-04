from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v24.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.38 - remove da interface toda a tela antiga Scherer/Fraga de busca por placa.
# Mantem apenas o dialogo simples da v0.22.37 + automacao Android/BlueStacks.

main_block=re.search(r'(?m)^if\s+__name__\s*==\s*["\']__main__["\']\s*:',text)
if not main_block:
    raise SystemExit('main block not found')

code=r'''

# -----------------------------------------------------------------------------
# ALIYVO - UI definitiva da busca por placa: somente dialogo Android
# -----------------------------------------------------------------------------
_aliyvo_plate_v24_timer=None
_aliyvo_plate_v24_replacement=None


def _aliyvo_plate_norm_label(value):
    try:
        import unicodedata
        s=unicodedata.normalize("NFKD",str(value or "")).encode("ascii","ignore").decode("ascii").lower()
        return re.sub(r"[^a-z]","",s)
    except Exception:
        return re.sub(r"[^a-z]","",str(value or "").lower())


def _aliyvo_hide_legacy_plate_panel():
    """Esconde o painel antigo Scherer/Fraga caso ainda exista no binario."""
    try:
        app=QApplication.instance()
        if not app: return
        for top in app.topLevelWidgets():
            try:
                panel=getattr(top,"plate_panel",None)
                if panel is not None:
                    panel.hide()
                    panel.setEnabled(False)
            except Exception:
                pass
        # Fallback: procura qualquer objeto dono de plate_panel.
        for w in app.allWidgets():
            try:
                panel=getattr(w,"plate_panel",None)
                if panel is not None:
                    panel.hide()
                    panel.setEnabled(False)
            except Exception:
                pass
    except Exception:
        pass


def _aliyvo_make_clean_plate_button(old):
    global _aliyvo_plate_v24_replacement
    try:
        if _aliyvo_plate_v24_replacement is not None:
            return _aliyvo_plate_v24_replacement
        parent=old.parentWidget()
        if parent is None: return None
        layout=parent.layout()
        if layout is None: return None
        btn=QPushButton("🚚 Busca placa",parent)
        btn.setObjectName("aliyvoPlateCleanButton")
        btn.setToolTip("Digite a placa e consulte o chassi pelo app Android")
        try: btn.setStyleSheet(old.styleSheet())
        except Exception: pass
        try: btn.setMinimumHeight(old.minimumHeight())
        except Exception: pass
        try: btn.setMaximumHeight(old.maximumHeight())
        except Exception: pass
        try: btn.setMinimumWidth(old.minimumWidth())
        except Exception: pass
        btn.clicked.connect(lambda checked=False,b=btn:_aliyvo_show_plate_dialog(b.window()))

        inserted=False
        if hasattr(layout,"insertWidget"):
            for i in range(layout.count()):
                item=layout.itemAt(i)
                if item is not None and item.widget() is old:
                    layout.insertWidget(i,btn)
                    inserted=True
                    break
        if not inserted:
            try:
                layout.addWidget(btn)
                inserted=True
            except Exception:
                pass
        if inserted:
            _aliyvo_plate_v24_replacement=btn
            return btn
    except Exception:
        pass
    return None


def _aliyvo_clean_plate_ui():
    """Substitui o launcher antigo e elimina qualquer entrada para a tela Scherer/Fraga."""
    global _aliyvo_plate_v24_timer
    _aliyvo_hide_legacy_plate_panel()
    try:
        app=QApplication.instance()
        if not app: return
        old_top=None
        for w in app.allWidgets():
            try:
                if not hasattr(w,"text"):
                    continue
                label=str(w.text() or "").strip()
                norm=_aliyvo_plate_norm_label(label)
                obj=str(w.objectName() or "") if hasattr(w,"objectName") else ""

                # Entradas antigas/laterais deixam de existir visualmente.
                if obj=="aliyvoPlateLookupButton" or norm in ("buscarporplaca","buscaporplaca"):
                    try: w.hide(); w.setEnabled(False)
                    except Exception: pass
                    continue

                # Nosso botao limpo permanece.
                if obj=="aliyvoPlateCleanButton":
                    continue

                # O botao antigo do topo era "Busca placa". Escondemos e colocamos outro
                # no mesmo lugar, sem qualquer conexao com o painel Scherer/Fraga.
                if norm=="buscaplaca" and old_top is None:
                    try:
                        if w.isVisible(): old_top=w
                    except Exception:
                        old_top=w
            except Exception:
                pass

        if old_top is not None:
            newbtn=_aliyvo_make_clean_plate_button(old_top)
            if newbtn is not None:
                try: old_top.hide(); old_top.setEnabled(False)
                except Exception: pass
    except Exception:
        pass

    try:
        if _aliyvo_plate_v24_timer is None:
            _aliyvo_plate_v24_timer=QTimer()
            _aliyvo_plate_v24_timer.setInterval(1400)
            _aliyvo_plate_v24_timer.timeout.connect(_aliyvo_clean_plate_ui)
            _aliyvo_plate_v24_timer.start()
    except Exception:
        pass

'''

# Coloca a nova definicao depois das anteriores, para sobrescrever o cleaner da v23.
text=text[:main_block.start()]+code+text[main_block.start():]

# A chamada QTimer.singleShot já existente da v23 passa a resolver esta nova função.
ast.parse(text)
p.write_text(text,encoding='utf-8')
print('removed legacy plate UI; Android dialog only',version)
