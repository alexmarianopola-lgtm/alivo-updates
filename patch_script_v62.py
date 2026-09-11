from pathlib import Path
import sys,re,json

p=Path(sys.argv[1] if len(sys.argv)>1 else r'C:\temp\build\_app\main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v62.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"',f'ALIYVO_VERSION = "{version}"',text,count=1)

# O worker precisa saber qual versao esta sendo protegida antes da troca.
old='"--version",ver]'
new='"--version",ver,"--current-version",ALIYVO_VERSION]'
if old not in text:
    raise SystemExit('comando do updater nao encontrado')
text=text.replace(old,new,1)

# Funcoes de protecao/rollback. Ficam fora do __init__ e nao interferem no WhatsApp.
anchor='if __name__=="__main__":\n'
if anchor not in text:
    raise SystemExit('entrypoint nao encontrado')
helper=r'''def _aliyvo_mark_startup_ok():
    try:
        import json,time
        target=Path(__file__).resolve().parent.parent
        upd=target/"_update";upd.mkdir(parents=True,exist_ok=True)
        (upd/"startup_ok.json").write_text(json.dumps({"version":ALIYVO_VERSION,"ts":time.time()}),encoding="utf-8")
    except Exception:
        pass


def _aliyvo_rollback_info():
    try:
        target=Path(__file__).resolve().parent.parent
        mf=target/"_rollback"/"previous"/"manifest.json"
        if not mf.exists():return None
        import json
        d=json.loads(mf.read_text(encoding="utf-8"))
        if not isinstance(d,dict) or not d.get("items"):return None
        return d
    except Exception:
        return None


def _aliyvo_restore_previous(parent=None):
    try:
        info=_aliyvo_rollback_info()
        if not info:
            QMessageBox.information(parent,"Restaurar versao","Ainda nao existe uma versao anterior salva neste computador.")
            return
        oldver=str(info.get("version") or "anterior")
        ans=QMessageBox.question(parent,"Restaurar versao anterior",f"Deseja fechar o ALIYVO e restaurar a versao {oldver}?\n\nSeus dados locais, WhatsApp, IA e lembretes nao serao apagados.")
        if ans!=QMessageBox.StandardButton.Yes:return
        import shutil,subprocess,os
        target=Path(__file__).resolve().parent.parent
        update_dir=target/"_update";update_dir.mkdir(parents=True,exist_ok=True)
        worker_src=target/"_app"/"updater_worker.pyw"
        worker_dst=update_dir/"updater_worker.pyw"
        shutil.copy2(worker_src,worker_dst)
        pythonw=target/"_runtime"/"pythonw.exe"
        if not pythonw.exists():pythonw=Path(sys.executable)
        exe=target/"ALIYVO.exe"
        cmd=[str(pythonw),str(worker_dst),"--restore","--pid",str(os.getpid()),"--target",str(target),"--exe",str(exe)]
        flags=getattr(subprocess,"DETACHED_PROCESS",0)|getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0)
        subprocess.Popen(cmd,cwd=str(target),creationflags=flags)
        QTimer.singleShot(250,QApplication.instance().quit)
    except Exception as e:
        QMessageBox.warning(parent,"Restaurar versao","Nao foi possivel iniciar a restauracao: "+str(e)[:220])


# Acrescenta o botao ao painel existente sem reescrever seu funcionamento de atualizacao.
_ALIYVO_UPDATEPANEL_INIT=UpdatePanel.__init__
def _aliyvo_updatepanel_init_with_restore(self,*args,**kwargs):
    _ALIYVO_UPDATEPANEL_INIT(self,*args,**kwargs)
    try:
        self.restore_btn=QPushButton("↩ Restaurar versao anterior",self)
        self.restore_btn.setObjectName("restorePreviousButton")
        info=_aliyvo_rollback_info()
        if info:
            oldver=str(info.get("version") or "anterior")
            self.restore_btn.setToolTip("Voltar para a versao "+oldver)
            self.restore_btn.setEnabled(True)
        else:
            self.restore_btn.setToolTip("Nenhuma versao anterior salva")
            self.restore_btn.setEnabled(False)
        self.restore_btn.clicked.connect(lambda:_aliyvo_restore_previous(self.window()))
        lay=self.layout()
        idx=max(0,lay.count()-1)
        lay.insertWidget(idx,self.restore_btn)
    except Exception:
        pass
UpdatePanel.__init__=_aliyvo_updatepanel_init_with_restore


'''
text=text.replace(anchor,helper+anchor,1)

# Marca sucesso somente depois que a janela principal foi criada e mostrada.
old='    win.show()\n    sys.exit(app.exec())'
new='    win.show()\n    QTimer.singleShot(1200,_aliyvo_mark_startup_ok)\n    sys.exit(app.exec())'
if old not in text:
    raise SystemExit('win.show entrypoint nao encontrado')
text=text.replace(old,new,1)

p.write_text(text,encoding='utf-8')
print('patched rollback/update safety',version)
