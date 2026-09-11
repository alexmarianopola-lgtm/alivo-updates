import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

SKIP_NAMES={"_update","_rollback"}

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest().lower()

def log_status(update_dir: Path,text: str):
    try:
        update_dir.mkdir(parents=True,exist_ok=True)
        (update_dir/"status.txt").write_text(text,encoding="utf-8")
    except Exception:
        pass

def _remove_path(path: Path):
    if not path.exists() and not path.is_symlink(): return
    if path.is_dir() and not path.is_symlink(): shutil.rmtree(path,ignore_errors=True)
    else:
        try:path.unlink(missing_ok=True)
        except Exception:pass

def _copy_item(src: Path,dst: Path):
    if src.is_dir():
        shutil.copytree(src,dst)
    else:
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)

def _wait_pid_exit(pid:int,timeout=45):
    if not pid:return
    deadline=time.time()+timeout
    while time.time()<deadline:
        try:
            os.kill(pid,0)
            time.sleep(0.4)
        except OSError:
            return

def backup_before_update(target:Path,src_root:Path,current_version:str):
    rollback=target/"_rollback"/"previous"
    if rollback.exists():shutil.rmtree(rollback,ignore_errors=True)
    rollback.mkdir(parents=True,exist_ok=True)
    items=[]
    for src in src_root.iterdir():
        if src.name in SKIP_NAMES:continue
        dst=target/src.name
        existed=dst.exists() or dst.is_symlink()
        items.append({"name":src.name,"existed":bool(existed)})
        if existed:_copy_item(dst,rollback/src.name)
    meta={"version":str(current_version or ""),"created_at":time.time(),"items":items}
    (rollback/"manifest.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    return rollback

def restore_backup(target:Path):
    rollback=target/"_rollback"/"previous"
    manifest=rollback/"manifest.json"
    if not manifest.exists():raise RuntimeError("Nao existe versao anterior salva")
    meta=json.loads(manifest.read_text(encoding="utf-8"))
    for row in meta.get("items") or []:
        name=str(row.get("name") or "").strip()
        if not name or name in SKIP_NAMES:continue
        dst=target/name
        _remove_path(dst)
        if bool(row.get("existed")):
            src=rollback/name
            if not src.exists():raise RuntimeError("Backup incompleto: "+name)
            _copy_item(src,dst)
    return str(meta.get("version") or "")

def apply_update(target:Path,src_root:Path):
    for item in src_root.iterdir():
        if item.name in SKIP_NAMES:continue
        dst=target/item.name
        if item.is_dir():
            if dst.exists():shutil.rmtree(dst,ignore_errors=True)
            shutil.copytree(item,dst)
        else:
            temp_dst=target/(item.name+".new")
            shutil.copy2(item,temp_dst)
            os.replace(temp_dst,dst)

def launch_exe(exe:Path,target:Path):
    if not exe.exists():raise RuntimeError("Executavel do ALIYVO nao encontrado")
    flags=getattr(subprocess,"DETACHED_PROCESS",0)|getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0)
    return subprocess.Popen([str(exe)],cwd=str(target),creationflags=flags)

def wait_startup_marker(update_dir:Path,version:str,proc,timeout=45):
    marker=update_dir/"startup_ok.json"
    deadline=time.time()+timeout
    while time.time()<deadline:
        if marker.exists():
            try:
                data=json.loads(marker.read_text(encoding="utf-8"))
                if str(data.get("version") or "")==str(version or ""):
                    return True
            except Exception:pass
        if proc is not None and proc.poll() is not None:
            return False
        time.sleep(0.5)
    return False

def main_update(args):
    target=Path(args.target).resolve();update_dir=target/"_update";update_dir.mkdir(exist_ok=True)
    zip_path=update_dir/"update.zip";extract_dir=update_dir/"extract";marker=update_dir/"startup_ok.json"
    try:marker.unlink(missing_ok=True)
    except Exception:pass
    log_status(update_dir,"Baixando atualizacao...")
    req=urllib.request.Request(args.url,headers={"User-Agent":"ALIYVO-Updater/2.0"})
    with urllib.request.urlopen(req,timeout=90) as r,zip_path.open("wb") as w:shutil.copyfileobj(r,w)
    if sha256_file(zip_path)!=args.sha256.strip().lower():raise RuntimeError("SHA256 da atualizacao nao confere")
    log_status(update_dir,"Preparando arquivos...")
    if extract_dir.exists():shutil.rmtree(extract_dir,ignore_errors=True)
    extract_dir.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(zip_path,"r") as z:z.extractall(extract_dir)
    src_root=extract_dir
    children=list(extract_dir.iterdir());dirs=[p for p in children if p.is_dir()];files=[p for p in children if p.is_file()]
    if len(dirs)==1 and not files:src_root=dirs[0]
    _wait_pid_exit(args.pid,45);time.sleep(0.8)
    log_status(update_dir,"Salvando versao anterior...")
    backup_before_update(target,src_root,args.current_version)
    log_status(update_dir,"Aplicando atualizacao...")
    apply_update(target,src_root)
    try:(update_dir/"last_version.txt").write_text(args.version,encoding="utf-8")
    except Exception:pass
    log_status(update_dir,"Validando abertura da nova versao...")
    proc=launch_exe(Path(args.exe),target)
    if wait_startup_marker(update_dir,args.version,proc,45):
        log_status(update_dir,"Atualizacao concluida e validada.")
    else:
        log_status(update_dir,"Nova versao nao confirmou a inicializacao. Restaurando a anterior...")
        try:
            if proc.poll() is None:
                proc.terminate();proc.wait(timeout=5)
        except Exception:pass
        restored=restore_backup(target)
        log_status(update_dir,"Versao anterior restaurada automaticamente"+(f" ({restored})" if restored else "")+".")
        launch_exe(Path(args.exe),target)
    try:zip_path.unlink(missing_ok=True)
    except Exception:pass
    try:shutil.rmtree(extract_dir,ignore_errors=True)
    except Exception:pass

def main_restore(args):
    target=Path(args.target).resolve();update_dir=target/"_update";update_dir.mkdir(exist_ok=True)
    log_status(update_dir,"Restaurando versao anterior...")
    _wait_pid_exit(args.pid,45);time.sleep(0.8)
    restored=restore_backup(target)
    log_status(update_dir,"Versao anterior restaurada"+(f" ({restored})" if restored else "")+".")
    launch_exe(Path(args.exe),target)

def self_test():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/"app";src=Path(td)/"new";root.mkdir();src.mkdir()
        (root/"a.txt").write_text("old",encoding="utf-8")
        (root/"dir").mkdir();(root/"dir"/"x.txt").write_text("old-dir",encoding="utf-8")
        (src/"a.txt").write_text("new",encoding="utf-8")
        (src/"dir").mkdir();(src/"dir"/"x.txt").write_text("new-dir",encoding="utf-8")
        (src/"new.txt").write_text("new-only",encoding="utf-8")
        backup_before_update(root,src,"0.22.72")
        apply_update(root,src)
        assert (root/"a.txt").read_text()=="new"
        assert (root/"new.txt").exists()
        ver=restore_backup(root)
        assert ver=="0.22.72"
        assert (root/"a.txt").read_text()=="old"
        assert (root/"dir"/"x.txt").read_text()=="old-dir"
        assert not (root/"new.txt").exists()
    print("rollback self-test OK")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--restore",action="store_true")
    ap.add_argument("--pid",type=int,default=0)
    ap.add_argument("--url",default="")
    ap.add_argument("--sha256",default="")
    ap.add_argument("--target",default="")
    ap.add_argument("--exe",default="")
    ap.add_argument("--version",default="")
    ap.add_argument("--current-version",default="")
    args=ap.parse_args()
    if args.self_test:return self_test()
    if not args.target or not args.exe:raise RuntimeError("Parametros target/exe ausentes")
    if args.restore:return main_restore(args)
    if not args.url or not args.sha256:raise RuntimeError("Parametros da atualizacao ausentes")
    return main_update(args)

if __name__=="__main__":
    try:main()
    except Exception as exc:
        try:
            upd=Path(__file__).resolve().parent
            (upd/"status.txt").write_text("ERRO: "+str(exc),encoding="utf-8")
        except Exception:pass
