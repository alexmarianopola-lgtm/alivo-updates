from pathlib import Path
import sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
text=main.read_text(encoding='utf-8')

def one(old,new,label):
    global text
    n=text.count(old)
    if n!=1:
        raise SystemExit(f'{label}: esperado 1, encontrado {n}')
    text=text.replace(old,new,1)

one('ALIYVO_VERSION = "0.22.89"','ALIYVO_VERSION = "0.22.90"','version')

marker='if __name__=="__main__":\n'
if marker not in text:
    marker='if __name__ == "__main__":\n'
if marker not in text:
    raise SystemExit('main marker nao encontrado')

diag_code = """
# --- ALIYVO 0.22.90: diagnostico de renderizacao WebEngine -------------------
# Diagnostico passivo: nao salva conteudo de paginas, mensagens, cookies ou senhas.
# Registra apenas estado tecnico do Chromium/Qt, sinais de carga e metricas visuais.
_aliyvo_webdiag_seen=set()

def _aliyvo_webdiag_file():
    try:
        import os as _os
        from pathlib import Path as _P
        _base=_P(_os.environ.get("LOCALAPPDATA") or str(_P.home()))/"ALIYVO"/"logs"
        _base.mkdir(parents=True,exist_ok=True)
        return _base/"WEB_RENDER_02290.jsonl"
    except Exception:
        return None

def _aliyvo_webdiag_safe_url(_view):
    try:
        from urllib.parse import urlsplit as _split
        _u=_view.url().toString()
        _p=_split(_u)
        return f"{_p.scheme}://{_p.netloc}{_p.path}"
    except Exception:
        return ""

def _aliyvo_webdiag_log(_event,**_data):
    try:
        import json as _json, datetime as _dt
        _row={"ts":_dt.datetime.now().isoformat(timespec="seconds"),"event":str(_event)}
        for _k,_v in _data.items():
            try:
                if isinstance(_v,(str,int,float,bool)) or _v is None:
                    _row[str(_k)]=_v
                elif isinstance(_v,(dict,list,tuple)):
                    _row[str(_k)]=_v
                else:
                    _row[str(_k)]=str(_v)
            except Exception:
                pass
        _f=_aliyvo_webdiag_file()
        if _f is not None:
            with _f.open("a",encoding="utf-8") as _h:
                _h.write(_json.dumps(_row,ensure_ascii=False,default=str)+"\\n")
    except Exception:
        pass

def _aliyvo_webdiag_visual_probe(_view):
    try:
        _pm=_view.grab()
        _img=_pm.toImage()
        _w=int(_img.width()); _h=int(_img.height())
        if _w<=0 or _h<=0:
            _aliyvo_webdiag_log("visual_probe",url=_aliyvo_webdiag_safe_url(_view),width=_w,height=_h,empty=True)
            return
        _sx=max(1,_w//48); _sy=max(1,_h//32)
        _n=0; _dark=0; _sum=0
        for _y in range(_sy//2,_h,_sy):
            for _x in range(_sx//2,_w,_sx):
                _c=_img.pixelColor(_x,_y)
                _r=int(_c.red()); _g=int(_c.green()); _b=int(_c.blue())
                _lum=(_r+_g+_b)/3.0
                _n+=1; _sum+=_lum
                if _r<18 and _g<18 and _b<18:
                    _dark+=1
        _aliyvo_webdiag_log(
            "visual_probe",
            url=_aliyvo_webdiag_safe_url(_view),
            width=_w,height=_h,
            visible=bool(_view.isVisible()),
            dark_ratio=round((_dark/_n) if _n else 0,4),
            mean_brightness=round((_sum/_n) if _n else 0,2),
        )
    except Exception as _e:
        _aliyvo_webdiag_log("visual_probe_error",error=repr(_e))

def _aliyvo_webdiag_js_probe(_view):
    try:
        _page=_view.page()
        _js=(
            "(() => { try { const out={"
            "readyState:document.readyState,"
            "titleLength:(document.title||'').length,"
            "bodyTextLength:document.body?(document.body.innerText||'').length:-1,"
            "bodyHtmlLength:document.body?(document.body.innerHTML||'').length:-1,"
            "visibility:document.visibilityState,"
            "innerWidth:window.innerWidth,innerHeight:window.innerHeight,"
            "dpr:window.devicePixelRatio,ua:navigator.userAgent,"
            "hardwareConcurrency:navigator.hardwareConcurrency||null,"
            "webgl:false,webglVendor:null,webglRenderer:null};"
            "try{const c=document.createElement('canvas');"
            "const gl=c.getContext('webgl2')||c.getContext('webgl');"
            "if(gl){out.webgl=true;const ext=gl.getExtension('WEBGL_debug_renderer_info');"
            "if(ext){out.webglVendor=String(gl.getParameter(ext.UNMASKED_VENDOR_WEBGL)||'');"
            "out.webglRenderer=String(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)||'');}}"
            "}catch(e){out.webglError=String(e);}"
            "try{out.bodyBackground=document.body?getComputedStyle(document.body).backgroundColor:null;}catch(e){}"
            "return out;}catch(e){return {probeError:String(e)};} })()"
        )
        def _done(_result):
            try:
                _aliyvo_webdiag_log(
                    "js_probe",
                    url=_aliyvo_webdiag_safe_url(_view),
                    result=_result if isinstance(_result,dict) else {"value":str(_result)}
                )
            except Exception:
                pass
        _page.runJavaScript(_js,_done)
    except Exception as _e:
        _aliyvo_webdiag_log("js_probe_error",url=_aliyvo_webdiag_safe_url(_view),error=repr(_e))

def _aliyvo_webdiag_probe(_view):
    try:
        _aliyvo_webdiag_log(
            "view_state",
            cls=type(_view).__name__,
            object_name=str(_view.objectName() or ""),
            url=_aliyvo_webdiag_safe_url(_view),
            visible=bool(_view.isVisible()),
            enabled=bool(_view.isEnabled()),
            width=int(_view.width()),
            height=int(_view.height()),
        )
    except Exception:
        pass
    _aliyvo_webdiag_visual_probe(_view)
    _aliyvo_webdiag_js_probe(_view)

def _aliyvo_webdiag_hook_view(_view):
    try:
        _key=id(_view)
        if _key in _aliyvo_webdiag_seen:
            return
        _aliyvo_webdiag_seen.add(_key)
        try:
            _view.setProperty("ALIYVO_WEBDIAG_HOOK",True)
        except Exception:
            pass
        _page=_view.page()
        _aliyvo_webdiag_log(
            "hook_view",
            cls=type(_view).__name__,
            object_name=str(_view.objectName() or ""),
            url=_aliyvo_webdiag_safe_url(_view),
        )
        try:
            _view.loadStarted.connect(lambda v=_view:_aliyvo_webdiag_log("load_started",url=_aliyvo_webdiag_safe_url(v)))
        except Exception as _e:
            _aliyvo_webdiag_log("hook_load_started_error",error=repr(_e))
        try:
            _view.loadProgress.connect(lambda p,v=_view:_aliyvo_webdiag_log("load_progress",url=_aliyvo_webdiag_safe_url(v),progress=int(p)) if int(p) in (0,10,25,50,75,90,100) else None)
        except Exception as _e:
            _aliyvo_webdiag_log("hook_load_progress_error",error=repr(_e))
        try:
            def _finished(_ok,v=_view):
                _aliyvo_webdiag_log("load_finished",url=_aliyvo_webdiag_safe_url(v),ok=bool(_ok))
                QTimer.singleShot(1200,lambda vv=v:_aliyvo_webdiag_probe(vv))
            _view.loadFinished.connect(_finished)
        except Exception as _e:
            _aliyvo_webdiag_log("hook_load_finished_error",error=repr(_e))
        try:
            if hasattr(_page,"renderProcessTerminated"):
                def _terminated(_status,_code,v=_view):
                    _aliyvo_webdiag_log("render_process_terminated",url=_aliyvo_webdiag_safe_url(v),status=str(_status),exit_code=int(_code))
                _page.renderProcessTerminated.connect(_terminated)
        except Exception as _e:
            _aliyvo_webdiag_log("hook_render_terminated_error",error=repr(_e))
        try:
            if hasattr(_page,"loadingChanged"):
                def _loading(_info,v=_view):
                    _d={"url":_aliyvo_webdiag_safe_url(v)}
                    for _name in ("status","errorCode","errorString"):
                        try:
                            _val=getattr(_info,_name)()
                            _d[_name]=str(_val)
                        except Exception:
                            pass
                    _aliyvo_webdiag_log("loading_changed",**_d)
                _page.loadingChanged.connect(_loading)
        except Exception as _e:
            _aliyvo_webdiag_log("hook_loading_changed_error",error=repr(_e))
        for _ms in (1800,5500,12000):
            QTimer.singleShot(_ms,lambda v=_view:_aliyvo_webdiag_probe(v))
    except Exception as _e:
        _aliyvo_webdiag_log("hook_view_error",error=repr(_e))

def _aliyvo_webdiag_scan():
    try:
        _app=QApplication.instance()
        if _app is None:
            return
        _widgets=_app.allWidgets()
        _count=0
        for _w in _widgets:
            try:
                if isinstance(_w,QWebEngineView):
                    _count+=1
                    _aliyvo_webdiag_hook_view(_w)
            except Exception:
                pass
        _aliyvo_webdiag_log("scan",qwebengine_views=_count,total_widgets=len(_widgets))
    except Exception as _e:
        _aliyvo_webdiag_log("scan_error",error=repr(_e))

def _aliyvo_webdiag_system():
    try:
        import os as _os, sys as _sys, platform as _platform
        _pkgs={}
        try:
            import importlib.metadata as _md
            for _p in ("PyQt6","PyQt6-WebEngine","PyQt6-Qt6","PyQt6-WebEngine-Qt6","qtwebview2","pythonnet"):
                try:_pkgs[_p]=_md.version(_p)
                except Exception:_pkgs[_p]=None
        except Exception:
            pass
        _env={}
        for _k in ("QTWEBENGINE_CHROMIUM_FLAGS","QTWEBENGINE_DISABLE_SANDBOX","QT_OPENGL","QT_ANGLE_PLATFORM","QT_SCALE_FACTOR"):
            if _k in _os.environ:
                _env[_k]=_os.environ.get(_k)
        _aliyvo_webdiag_log(
            "system",
            aliyvo_version="0.22.90",
            python=_sys.version.split()[0],
            executable=str(_sys.executable),
            platform=_platform.platform(),
            machine=_platform.machine(),
            packages=_pkgs,
            env=_env,
        )
        try:
            from PyQt6.QtCore import QT_VERSION_STR as _qtv, PYQT_VERSION_STR as _pqv
            _aliyvo_webdiag_log("qt_versions",qt=_qtv,pyqt=_pqv)
        except Exception as _e:
            _aliyvo_webdiag_log("qt_versions_error",error=repr(_e))
        try:
            from PyQt6.QtWebEngineCore import QWebEngineProfile as _Profile
            _prof=_Profile.defaultProfile()
            _aliyvo_webdiag_log(
                "webengine_profile",
                user_agent=str(_prof.httpUserAgent()),
                cache_path=str(_prof.cachePath()),
                storage_path=str(_prof.persistentStoragePath()),
            )
        except Exception as _e:
            _aliyvo_webdiag_log("webengine_profile_error",error=repr(_e))
    except Exception as _e:
        _aliyvo_webdiag_log("system_error",error=repr(_e))

"""

text=text.replace(marker,diag_code+'\n'+marker,1)

startup="    QTimer.singleShot(1000, _aliyvo_clean_plate_ui)\n    QTimer.singleShot(900, _aliyvo_override_old_plate_search)\n"
if startup not in text:
    raise SystemExit('startup anchor nao encontrado')
replacement=startup+(
    "    # Diagnostico WebEngine em passagens finitas; sem timer permanente.\n"
    "    QTimer.singleShot(1200, _aliyvo_webdiag_system)\n"
    "    QTimer.singleShot(2000, _aliyvo_webdiag_scan)\n"
    "    QTimer.singleShot(5000, _aliyvo_webdiag_scan)\n"
    "    QTimer.singleShot(10000, _aliyvo_webdiag_scan)\n"
    "    QTimer.singleShot(20000, _aliyvo_webdiag_scan)\n"
)
text=text.replace(startup,replacement,1)

main.write_text(text,encoding='utf-8')

# Ferramenta de coleta de um clique para o computador onde ocorre a tela preta.
(root/'_app'/'coletar_diagnostico_web.ps1').write_text("$ErrorActionPreference = 'SilentlyContinue'\n$ProgressPreference = 'SilentlyContinue'\n\n$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'\n$tmp = Join-Path $env:TEMP (\"ALIYVO_DIAG_\" + $stamp)\nNew-Item -ItemType Directory -Force -Path $tmp | Out-Null\n\n$logDir = Join-Path $env:LOCALAPPDATA 'ALIYVO\\logs'\nif (Test-Path $logDir) {\n    Get-ChildItem $logDir -File |\n        Where-Object { $_.Name -match 'WEB_RENDER_02290|INSTALACAO|diagn|error|crash|log' } |\n        ForEach-Object { Copy-Item $_.FullName -Destination $tmp -Force }\n}\n\n@(\n    \"ALIYVO diagnostico WebEngine 0.22.90\"\n    \"Gerado em: $(Get-Date -Format o)\"\n    \"Usuario: $env:USERNAME\"\n    \"Computador: $env:COMPUTERNAME\"\n    \"LOCALAPPDATA: $env:LOCALAPPDATA\"\n) | Set-Content (Join-Path $tmp 'RESUMO.txt') -Encoding UTF8\n\nGet-CimInstance Win32_OperatingSystem |\n    Select-Object Caption,Version,BuildNumber,OSArchitecture |\n    Format-List | Out-File (Join-Path $tmp 'WINDOWS.txt') -Encoding utf8\n\nGet-CimInstance Win32_ComputerSystem |\n    Select-Object Manufacturer,Model,SystemType,TotalPhysicalMemory |\n    Format-List | Out-File (Join-Path $tmp 'COMPUTADOR.txt') -Encoding utf8\n\nGet-CimInstance Win32_VideoController |\n    Select-Object Name,AdapterCompatibility,DriverVersion,DriverDate,VideoProcessor,AdapterRAM,Status |\n    Format-List | Out-File (Join-Path $tmp 'GPU.txt') -Encoding utf8\n\nGet-CimInstance Win32_Processor |\n    Select-Object Name,Manufacturer,NumberOfCores,NumberOfLogicalProcessors |\n    Format-List | Out-File (Join-Path $tmp 'CPU.txt') -Encoding utf8\n\nGet-Process |\n    Where-Object { $_.ProcessName -match 'QtWebEngineProcess|msedgewebview2|python|aliyvo' } |\n    Select-Object ProcessName,Id,CPU,WorkingSet64,Path |\n    Format-Table -AutoSize | Out-File (Join-Path $tmp 'PROCESSOS.txt') -Encoding utf8\n\n$since=(Get-Date).AddHours(-6)\nGet-WinEvent -FilterHashtable @{LogName='Application';StartTime=$since} -MaxEvents 300 |\n    Where-Object { $_.ProviderName -match 'Application Error|Windows Error Reporting|Qt|Python' -or $_.Message -match 'QtWebEngine|python|ALIYVO|Qt6WebEngine|chromium' } |\n    Select-Object -First 100 TimeCreated,Id,LevelDisplayName,ProviderName,Message |\n    Format-List | Out-File (Join-Path $tmp 'EVENTOS_WINDOWS.txt') -Encoding utf8\n\n$dest = Join-Path ([Environment]::GetFolderPath('Desktop')) (\"ALIYVO_DIAGNOSTICO_WEB_\" + $stamp + \".zip\")\nCompress-Archive -Path (Join-Path $tmp '*') -DestinationPath $dest -Force\nRemove-Item $tmp -Recurse -Force\n\nWrite-Host ''\nWrite-Host 'Diagnostico criado em:'\nWrite-Host $dest\nWrite-Host ''\nWrite-Host 'Envie esse ZIP no chat para analise.'\n",encoding='utf-8')
(root/'GERAR_DIAGNOSTICO_PARA_CHATGPT.bat').write_text("@echo off\ntitle ALIYVO - Gerar diagnostico para ChatGPT\necho.\necho Gerando diagnostico tecnico do ALIYVO...\necho Isso nao copia mensagens, cookies nem senhas.\necho.\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File \"%~dp0_app\\coletar_diagnostico_web.ps1\"\necho.\npause\n",encoding='utf-8')
(root/'LEIA-ME-DIAGNOSTICO-02290.txt').write_text('ALIYVO 0.22.90 - DIAGNOSTICO DE TELA PRETA\n\n1. Abra o ALIYVO normalmente.\n2. Reproduza a tela preta no Assistente ou na Busca de Produtos.\n3. Aguarde pelo menos 20 segundos com a tela aberta.\n4. Feche o ALIYVO.\n5. Execute GERAR_DIAGNOSTICO_PARA_CHATGPT.bat.\n6. Um ZIP chamado ALIYVO_DIAGNOSTICO_WEB_*.zip sera criado na Area de Trabalho.\n7. Envie esse ZIP no chat.\n\nO diagnostico NAO copia mensagens do WhatsApp, conteudo das paginas,\ncookies ou senhas. Ele coleta versoes, sinais de carregamento, estado\ndo renderizador, metricas visuais agregadas, GPU, Windows e eventos tecnicos.\n',encoding='utf-8')
print('patched web rendering diagnostics v0.22.90')
