from pathlib import Path
import sys

p=Path(sys.argv[1] if len(sys.argv)>1 else r'C:\temp\build\_app\updater_worker.pyw')
text=p.read_text(encoding='utf-8')
old='''    proc=launch_exe(Path(args.exe),target)\n    if wait_startup_marker(update_dir,args.version,proc,45):\n        log_status(update_dir,"Atualizacao concluida e validada.")\n    else:\n        log_status(update_dir,"Nova versao nao confirmou a inicializacao. Restaurando a anterior...")\n        try:\n            if proc.poll() is None:\n                proc.terminate();proc.wait(timeout=5)\n        except Exception:pass\n        restored=restore_backup(target)\n        log_status(update_dir,"Versao anterior restaurada automaticamente"+(f" ({restored})" if restored else "")+".")\n        launch_exe(Path(args.exe),target)\n'''
new='''    proc=launch_exe(Path(args.exe),target)\n    startup_ok=wait_startup_marker(update_dir,args.version,proc,90)\n    if startup_ok:\n        log_status(update_dir,"Atualizacao concluida e validada.")\n    elif proc is not None and proc.poll() is None:\n        # O processo continua vivo: nao tratar lentidao como falha.\n        log_status(update_dir,"Atualizacao aplicada. O ALIYVO continua aberto; validacao automatica demorou e a versao nova foi mantida.")\n    else:\n        log_status(update_dir,"A nova versao encerrou durante a inicializacao. Restaurando a anterior...")\n        restored=restore_backup(target)\n        log_status(update_dir,"Versao anterior restaurada automaticamente"+(f" ({restored})" if restored else "")+".")\n        launch_exe(Path(args.exe),target)\n'''
if old not in text:
    raise SystemExit('bloco de validacao do updater nao encontrado')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('patched updater false rollback guard')
