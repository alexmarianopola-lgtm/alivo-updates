from pathlib import Path
import sys,re

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
p=root/'_app'/'aliyvo_ponto.py'

ms=main.read_text(encoding='utf-8')
ps=p.read_text(encoding='utf-8')

if 'ALIYVO_VERSION = "0.23.20"' not in ms and 'ALIYVO_VERSION = "0.23.21"' not in ms:
    raise SystemExit('base main nao encontrada')
ms=re.sub(r'ALIYVO_VERSION = "0\\.23\\.(20|21)"','ALIYVO_VERSION = "0.23.21"',ms,count=1)
ms=ms.replace('aliyvo_version="0.23.20"','aliyvo_version="0.23.21"')
ps=re.sub(r'POINT_MODULE_VERSION = "0\\.23\\.(18|20|21)"','POINT_MODULE_VERSION = "0.23.21"',ps,count=1)

auto = '''        auto_sync = {"started": False}
        def maybe_auto_sync_after_login(ok: bool):
            if not ok or auto_sync["started"] or self._sync_busy:
                return
            try:
                current_url = view.url().toString().lower()
            except Exception:
                current_url = ""
            if "app.ahgora.com.br" not in current_url:
                return
            if "login" in current_url:
                return
            auto_sync["started"] = True
            QTimer.singleShot(900, start_sync)

        view.loadFinished.connect(maybe_auto_sync_after_login)
'''
ps=ps.replace(auto,'',1)

old = '''        def start_sync():
            sync_btn.setEnabled(False)
            sync_btn.setText("Sincronizando...")
            self._sync_from_visible_ahgora_portal(
                view,
                reason="browser_link",
                done=lambda ok, msg: self._finish_browser_link_sync(
                    dlg, sync_btn, ok, msg
                ),
            )
'''
new = '''        def start_sync():
            sync_btn.setEnabled(False)
            sync_btn.setText("Sincronizando...")
            if self._ahgora_sync_view is None:
                self._ahgora_sync_view = self._new_ahgora_view(self.owner)
                self._ahgora_sync_view.hide()
            self._sync_using_view(
                self._ahgora_sync_view,
                reason="browser_link",
                done=lambda ok, msg: self._finish_browser_link_sync(
                    dlg, sync_btn, ok, msg
                ),
            )
'''
if old in ps:
    ps=ps.replace(old,new,1)
else:
    old2='''        def start_sync():
            sync_btn.setEnabled(False)
            sync_btn.setText("Sincronizando...")
            self._sync_using_view(
                view,
                reason="browser_link",
                done=lambda ok, msg: self._finish_browser_link_sync(
                    dlg, sync_btn, ok, msg
                ),
            )
'''
    if old2 not in ps:
        raise SystemExit('start_sync nao encontrado')
    ps=ps.replace(old2,new,1)

old = '''    def sync_ahgora_async(self, reason: str = "manual") -> None:
        if not self._can_sync_ahgora():
            if reason in {"manual", "settings"}:
                self.show_ahgora_settings()
            else:
                self.check_now()
            return
        try:
            dlg = self._ahgora_link_dialog
            if dlg is not None and dlg.isVisible():
                views = dlg.findChildren(QWebEngineView)
                if views:
                    self._sync_from_visible_ahgora_portal(views[0], reason=reason)
                    return
        except Exception:
            pass
        self._sync_via_persistent_browser(reason=reason)
'''
new = '''    def sync_ahgora_async(self, reason: str = "manual") -> None:
        if not self._can_sync_ahgora():
            if reason in {"manual", "settings"}:
                self.show_ahgora_settings()
            else:
                self.check_now()
            return
        self._sync_via_persistent_browser(reason=reason)
'''
if old in ps:
    ps=ps.replace(old,new,1)

main.write_text(ms,encoding='utf-8')
p.write_text(ps,encoding='utf-8')
print('PATCH_LOGIN_FLOW_V2321=OK')
