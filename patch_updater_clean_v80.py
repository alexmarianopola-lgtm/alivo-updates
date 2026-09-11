from pathlib import Path
import re, sys
root=Path(sys.argv[1])
main=root/'_app'/'main.py'
worker=root/'_app'/'updater_worker.pyw'

t=main.read_text(encoding='utf-8')
t=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"','ALIYVO_VERSION = "0.22.80"',t,count=1)
old='QTimer.singleShot(500,self.close)'
new='QTimer.singleShot(500,QApplication.instance().quit)'
if old not in t:
    raise SystemExit('gatilho self.close nao encontrado')
t=t.replace(old,new,1)
main.write_text(t,encoding='utf-8')

w=worker.read_text(encoding='utf-8')
w=w.replace('def wait_pid(pid,timeout=60):','def wait_pid(pid,timeout=15):',1)
w=w.replace('    wait_pid(pid,60)\n    time.sleep(.8)', '''    wait_pid(pid,15)\n    # Se a janela fechou mas o processo ficou preso (ex.: WebView2), encerra\n    # somente a arvore do processo antigo antes de substituir os arquivos.\n    if pid and os.name=="nt":\n        try:\n            import ctypes\n            SYNCHRONIZE=0x00100000\n            h=ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE,False,int(pid))\n            if h:\n                state=ctypes.windll.kernel32.WaitForSingleObject(h,0)\n                ctypes.windll.kernel32.CloseHandle(h)\n                if state==0x00000102:  # WAIT_TIMEOUT = processo ainda vivo\n                    log(f"Processo antigo {pid} ainda ativo; encerrando arvore.")\n                    subprocess.run(["taskkill","/PID",str(pid),"/T","/F"],\n                                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,\n                                   creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),timeout=10)\n                    time.sleep(1.5)\n        except Exception as e:\n            log("Aviso ao encerrar processo antigo: "+repr(e))\n    time.sleep(.8)''',1)
worker.write_text(w,encoding='utf-8')
print('patched clean updater 0.22.80')
