from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v22.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.36 - automacao experimental da consulta de placa via app Android/BlueStacks.
# Usa ADB + uiautomator para localizar campo/botao e extrair VIN/chassi do resultado.
# Se ADB estiver desativado ou a UI mudar, mantem o fallback: abre o app e deixa a placa copiada.

if '_aliyvo_android_plate_automation_worker' not in text:
    main_block=re.search(r'(?m)^if\s+__name__\s*==\s*["\']__main__["\']\s*:',text)
    if not main_block:
        raise SystemExit('main block not found')

    code=r'''

# -----------------------------------------------------------------------------
# ALIYVO - Automacao da busca de placa no BlueStacks via ADB
# -----------------------------------------------------------------------------
class _AliyvoAndroidPlateBridge(QObject):
    ready=pyqtSignal(object)

_aliyvo_android_plate_bridge=None


def _aliyvo_bluestacks_conf_path():
    try:
        import os
        candidates=[
            Path(os.environ.get("ProgramData") or r"C:\\ProgramData")/"BlueStacks_nxt"/"bluestacks.conf",
            Path(r"C:\\ProgramData\BlueStacks_nxt\bluestacks.conf"),
        ]
        for p in candidates:
            if p.exists(): return p
    except Exception:
        pass
    return None


def _aliyvo_bluestacks_adb_paths():
    try:
        import os
        candidates=[]
        for base in [os.environ.get("ProgramFiles"),os.environ.get("ProgramFiles(x86)"),r"C:\\Program Files"]:
            if base:
                candidates.extend([
                    Path(base)/"BlueStacks_nxt"/"HD-Adb.exe",
                    Path(base)/"BlueStacks_nxt"/"adb.exe",
                ])
        out=[]
        for p in candidates:
            try:
                if p.exists() and str(p) not in out: out.append(str(p))
            except Exception:
                pass
        return out
    except Exception:
        return []


def _aliyvo_bluestacks_adb_ports():
    result=[]
    try:
        conf=_aliyvo_bluestacks_conf_path()
        if conf:
            raw=conf.read_text(encoding="utf-8",errors="ignore")
            # Formato comum: bst.instance.Pie64.adb_port="5555"
            for name,port in re.findall(r'bst\.instance\.([^.="\\s]+)\.adb_port\s*=\s*"?(\d+)"?',raw):
                item=(name,"127.0.0.1:"+port)
                if item not in result: result.append(item)
    except Exception:
        pass
    return result


def _aliyvo_adb_run(adb,serial,args,timeout=8):
    import subprocess
    cmd=[adb]
    if serial:
        cmd += ["-s",serial]
    cmd += list(args)
    cp=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors="ignore",timeout=timeout,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    return str(cp.stdout or "")


def _aliyvo_find_android_target(wait_seconds=18):
    import time,subprocess
    adbs=_aliyvo_bluestacks_adb_paths()
    ports=_aliyvo_bluestacks_adb_ports()
    if not adbs:
        return {"ok":False,"reason":"adb_missing","error":"Nao encontrei o ADB do BlueStacks."}
    deadline=time.time()+max(2,wait_seconds)
    last=""
    while time.time()<deadline:
        for adb in adbs:
            # Se a configuracao nao trouxe portas, HD-Adb pode ja enxergar a instancia ativa.
            candidates=[x[1] for x in ports] or [""]
            for serial in candidates:
                try:
                    if serial:
                        last=_aliyvo_adb_run(adb,"",["connect",serial],5)
                    probe=_aliyvo_adb_run(adb,serial,["shell","pm","path",ALIYVO_PLATE_APP_PACKAGE],5)
                    if "package:" in probe:
                        return {"ok":True,"adb":adb,"serial":serial}
                    last=probe or last
                except Exception as e:
                    last=str(e)
        time.sleep(1.5)
    return {"ok":False,"reason":"adb_disabled","error":last[:300] or "BlueStacks nao respondeu ao ADB."}


def _aliyvo_ui_dump(adb,serial):
    try:
        _aliyvo_adb_run(adb,serial,["shell","uiautomator","dump","/sdcard/aliyvo_ui.xml"],7)
        xml=_aliyvo_adb_run(adb,serial,["shell","cat","/sdcard/aliyvo_ui.xml"],7)
        return xml if "<hierarchy" in xml else ""
    except Exception:
        return ""


def _aliyvo_bounds_center(value):
    try:
        m=re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",str(value or ""))
        if not m: return None
        x1,y1,x2,y2=map(int,m.groups())
        if x2<=x1 or y2<=y1: return None
        return ((x1+x2)//2,(y1+y2)//2)
    except Exception:
        return None


def _aliyvo_android_nodes(xml):
    try:
        import xml.etree.ElementTree as ET
        root=ET.fromstring(xml)
        return list(root.iter("node"))
    except Exception:
        return []


def _aliyvo_extract_chassi_from_xml(xml):
    nodes=_aliyvo_android_nodes(xml)
    values=[]
    for n in nodes:
        for key in ("text","content-desc"):
            v=str(n.attrib.get(key) or "").strip()
            if v: values.append(v)
    # Primeiro tenta o valor proximo do rotulo Chassi.
    for i,v in enumerate(values):
        if "chassi" in v.lower():
            for cand in values[i+1:i+7]:
                compact=re.sub(r"[^A-Za-z0-9]","",cand).upper()
                if re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}",compact):
                    return compact
    # Fallback: qualquer VIN de 17 caracteres visivel.
    for v in values:
        for cand in re.findall(r"[A-Za-z0-9]{17}",v):
            cand=cand.upper()
            if re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}",cand):
                return cand
    return ""


def _aliyvo_find_edit_center(xml):
    nodes=_aliyvo_android_nodes(xml)
    for n in nodes:
        cls=str(n.attrib.get("class") or "")
        txt=(str(n.attrib.get("text") or "")+" "+str(n.attrib.get("content-desc") or "")+" "+str(n.attrib.get("resource-id") or "")).lower()
        if "edittext" in cls.lower() or ("placa" in txt and str(n.attrib.get("focusable") or "").lower()=="true"):
            c=_aliyvo_bounds_center(n.attrib.get("bounds"))
            if c: return c
    return None


def _aliyvo_find_search_center(xml):
    nodes=_aliyvo_android_nodes(xml)
    words=("buscar","consultar","pesquisar","consulta")
    for n in nodes:
        txt=(str(n.attrib.get("text") or "")+" "+str(n.attrib.get("content-desc") or "")).strip().lower()
        if any(w in txt for w in words):
            c=_aliyvo_bounds_center(n.attrib.get("bounds"))
            if c: return c
    return None


def _aliyvo_android_plate_automation_worker(plate):
    import time
    target=_aliyvo_find_android_target(22)
    if not target.get("ok"):
        target.update({"plate":plate})
        return target
    adb=target["adb"]; serial=target.get("serial") or ""
    try:
        # Reinicia o app para voltar a uma tela previsivel.
        _aliyvo_adb_run(adb,serial,["shell","am","force-stop",ALIYVO_PLATE_APP_PACKAGE],5)
        _aliyvo_adb_run(adb,serial,["shell","monkey","-p",ALIYVO_PLATE_APP_PACKAGE,"-c","android.intent.category.LAUNCHER","1"],8)
        time.sleep(2.5)

        edit=None; xml=""
        for _ in range(4):
            xml=_aliyvo_ui_dump(adb,serial)
            # Se abriu no resultado anterior, volta ate encontrar o campo de placa.
            edit=_aliyvo_find_edit_center(xml)
            if edit: break
            _aliyvo_adb_run(adb,serial,["shell","input","keyevent","4"],4)
            time.sleep(1)
        if not edit:
            return {"ok":False,"reason":"field_not_found","plate":plate,"error":"Nao localizei o campo da placa no app. A placa continua copiada para colar manualmente."}

        x,y=edit
        _aliyvo_adb_run(adb,serial,["shell","input","tap",str(x),str(y)],4)
        time.sleep(.3)
        # Limpa eventual conteudo do campo.
        _aliyvo_adb_run(adb,serial,["shell","input","keyevent","123"],4)
        for _ in range(12):
            _aliyvo_adb_run(adb,serial,["shell","input","keyevent","67"],3)
        _aliyvo_adb_run(adb,serial,["shell","input","text",plate],5)
        time.sleep(.4)

        xml=_aliyvo_ui_dump(adb,serial)
        search=_aliyvo_find_search_center(xml)
        if search:
            sx,sy=search
            _aliyvo_adb_run(adb,serial,["shell","input","tap",str(sx),str(sy)],4)
        else:
            _aliyvo_adb_run(adb,serial,["shell","input","keyevent","66"],4)

        # Aguarda resposta e extrai o VIN/chassi visivel.
        for _ in range(10):
            time.sleep(1.5)
            xml=_aliyvo_ui_dump(adb,serial)
            chassi=_aliyvo_extract_chassi_from_xml(xml)
            if chassi:
                return {"ok":True,"plate":plate,"chassi":chassi}
        return {"ok":False,"reason":"chassi_not_found","plate":plate,"error":"A consulta abriu, mas nao consegui ler o chassi automaticamente. Veja o resultado no app."}
    except Exception as e:
        return {"ok":False,"reason":"automation_error","plate":plate,"error":str(e)[:300]}


def _aliyvo_android_plate_result(data):
    try:
        if not isinstance(data,dict): return
        plate=str(data.get("plate") or "")
        if data.get("ok") and data.get("chassi"):
            chassi=str(data.get("chassi") or "").upper()
            try: QApplication.clipboard().setText(chassi)
            except Exception: pass
            QMessageBox.information(None,"Busca por placa",f"✅ Placa: {plate}\n\nCHASSI: {chassi}\n\nO chassi ja foi copiado.")
            return
        reason=str(data.get("reason") or "")
        if reason in ("adb_disabled","adb_missing"):
            QMessageBox.information(None,"Ativar automacao da placa",
                "O app Android ja esta funcionando. Para o ALIYVO preencher a placa e ler o chassi sozinho, falta ativar uma vez no BlueStacks:\n\n"
                "⚙ Configuracoes → Avancado → Android Debug Bridge → Ativar → Salvar alteracoes.\n\n"
                "Depois clique novamente em Buscar placa. A placa ficou copiada para uso manual enquanto isso.")
        else:
            QMessageBox.information(None,"Busca por placa",str(data.get("error") or "Nao consegui automatizar esta consulta.")+"\n\nA placa ficou copiada e o app continua disponivel para consulta manual.")
    except Exception:
        pass


def _aliyvo_start_android_plate_automation(plate,parent=None):
    global _aliyvo_android_plate_bridge
    try:
        if _aliyvo_android_plate_bridge is None:
            _aliyvo_android_plate_bridge=_AliyvoAndroidPlateBridge()
            _aliyvo_android_plate_bridge.ready.connect(_aliyvo_android_plate_result)
        bridge=_aliyvo_android_plate_bridge
    except Exception:
        bridge=None

    def worker():
        data=_aliyvo_android_plate_automation_worker(plate)
        try:
            if bridge is not None: bridge.ready.emit(data)
        except Exception:
            pass
    try:
        import threading
        threading.Thread(target=worker,name="AliyvoPlateADB",daemon=True).start()
    except Exception:
        pass


# Redefine a acao da v0.22.35: agora tenta automacao completa apos abrir/copiar.
def _aliyvo_plate_from_ui_and_open(parent=None):
    plate=""
    try:
        app=QApplication.instance()
        if app:
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
            if candidates: plate=candidates[-1]
        if plate:
            QApplication.clipboard().setText(plate)
    except Exception:
        pass
    if not plate:
        try: QMessageBox.information(parent,"Busca por placa","Digite uma placa valida antes de buscar.")
        except Exception: pass
        return
    try:
        _aliyvo_open_plate_lookup_app(parent)
    except Exception:
        pass
    _aliyvo_start_android_plate_automation(plate,parent)

'''
    text=text[:main_block.start()]+code+text[main_block.start():]

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched Android plate automation',version)
