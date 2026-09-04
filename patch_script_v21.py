from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v21.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.35 - a Busca por placa deixa de usar Scherer/Fraga.
# O botao existente passa a copiar a placa digitada e abrir somente o app Android.
# Mantemos o codigo antigo no arquivo por reversibilidade, mas ele nao e mais disparado pela UI.

if '_aliyvo_override_old_plate_search' not in text:
    main_block=re.search(r'(?m)^if\s+__name__\s*==\s*["\']__main__["\']\s*:',text)
    if not main_block:
        raise SystemExit('main block not found')

    code=r'''

# -----------------------------------------------------------------------------
# ALIYVO - Busca por placa via app Android (sem Scherer/Fraga)
# -----------------------------------------------------------------------------
_aliyvo_plate_override_timer=None


def _aliyvo_plate_from_ui_and_open(parent=None):
    plate=""
    try:
        app=QApplication.instance()
        if app:
            # Prioriza campos visiveis com formato de placa brasileira (antiga ou Mercosul).
            candidates=[]
            for w in app.allWidgets():
                try:
                    if isinstance(w,QLineEdit) and w.isVisible():
                        raw=str(w.text() or "").strip().upper()
                        compact=re.sub(r"[^A-Z0-9]","",raw)
                        if re.fullmatch(r"[A-Z]{3}[0-9][A-Z0-9][0-9]{2}",compact):
                            candidates.append(compact)
                except Exception:
                    pass
            if candidates:
                plate=candidates[-1]
                try:
                    QApplication.clipboard().setText(plate)
                except Exception:
                    pass
    except Exception:
        pass

    try:
        _aliyvo_open_plate_lookup_app(parent)
    except Exception as e:
        try:
            QMessageBox.warning(parent,"Busca por placa","Nao consegui abrir o app de consulta: "+str(e)[:180])
        except Exception:
            pass


def _aliyvo_override_old_plate_search():
    """Redireciona a UI antiga da Scherer/Fraga para o app Android."""
    global _aliyvo_plate_override_timer
    try:
        app=QApplication.instance()
        if not app:
            return

        for w in app.allWidgets():
            try:
                if isinstance(w,QPushButton):
                    label=str(w.text() or "").strip().lower()
                    # O botao principal da tela antiga e qualquer launcher novo usam a mesma acao.
                    if "buscar placa" in label:
                        if not bool(w.property("ALIYVO_ANDROID_PLATE_OVERRIDE")):
                            try:
                                w.clicked.disconnect()
                            except Exception:
                                pass
                            w.clicked.connect(lambda checked=False,b=w:_aliyvo_plate_from_ui_and_open(b.window()))
                            w.setProperty("ALIYVO_ANDROID_PLATE_OVERRIDE",True)
                            try:
                                w.setToolTip("Copiar a placa digitada e abrir o app Android de consulta")
                            except Exception:
                                pass
                    # Controles exclusivos do diagnostico Scherer deixam de aparecer.
                    elif label in ("diagnóstico","diagnostico","reconectar"):
                        try:
                            parent=w.parentWidget()
                            # Esconde apenas quando estiver dentro da tela de placa.
                            txt=""
                            if parent:
                                for c in parent.findChildren(QLabel):
                                    txt += " "+str(c.text() or "")
                            if "placa" in txt.lower() or "captura" in txt.lower():
                                w.hide()
                        except Exception:
                            pass
                elif isinstance(w,QLabel):
                    t=str(w.text() or "")
                    low=t.lower()
                    if "digite a placa e receba os dados do veículo diretamente no aliyvo" in low or "digite a placa e receba os dados do veiculo diretamente no aliyvo" in low:
                        w.setText("Digite a placa. O ALIYVO copia e abre o app Android de consulta de chassi.")
                    elif "captura ativa" in low and "caminho completo" in low:
                        # Mensagem pertencente ao fluxo antigo da Scherer.
                        w.hide()
            except Exception:
                pass
    except Exception:
        pass

    # A tela de placa e criada/mostrada sob demanda; checagem leve apenas da UI Qt.
    try:
        if _aliyvo_plate_override_timer is None:
            _aliyvo_plate_override_timer=QTimer()
            _aliyvo_plate_override_timer.setInterval(1200)
            _aliyvo_plate_override_timer.timeout.connect(_aliyvo_override_old_plate_search)
            _aliyvo_plate_override_timer.start()
    except Exception:
        pass

'''
    text=text[:main_block.start()]+code+text[main_block.start():]

    # Agenda a primeira instalacao logo depois que o QApplication for criado.
    m=re.search(r'(?m)^(?P<indent>[ \t]*)(?P<var>[A-Za-z_]\w*)\s*=\s*QApplication\s*\([^\n]*\)\s*$',text)
    if not m:
        raise SystemExit('QApplication creation not found')
    indent=m.group('indent')
    insert=m.end()
    text=text[:insert]+'\n'+indent+'QTimer.singleShot(900, _aliyvo_override_old_plate_search)'+text[insert:]

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched plate search to Android app only',version)
