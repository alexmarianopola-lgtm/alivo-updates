from pathlib import Path
import sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
p=root/'_app'/'aliyvo_ponto.py'

ms=main.read_text(encoding='utf-8')
ps=p.read_text(encoding='utf-8')

if 'ALIYVO_VERSION = "0.23.15"' not in ms:
    raise SystemExit('base main 0.23.15 nao encontrada')
ms=ms.replace('ALIYVO_VERSION = "0.23.15"','ALIYVO_VERSION = "0.23.16"',1)
ms=ms.replace('aliyvo_version="0.23.15"','aliyvo_version="0.23.16"')

if 'POINT_MODULE_VERSION = "0.23.01"' not in ps:
    raise SystemExit('versao modulo ponto esperada nao encontrada')
ps=ps.replace('POINT_MODULE_VERSION = "0.23.01"','POINT_MODULE_VERSION = "0.23.16"',1)

old='''    def _credentials_available(self) -> bool:
        try:
            cfg = self._load_credentials()
            return bool(cfg.get("registration") and cfg.get("password") and cfg.get("company_id"))
        except Exception:
            return False
'''
new='''    def _credentials_available(self) -> bool:
        try:
            cfg = self._load_credentials()
            return bool(cfg.get("registration") and cfg.get("password") and cfg.get("company_id"))
        except Exception:
            return False

    def _browser_session_available(self) -> bool:
        """Retorna True quando ja existe perfil persistente do Ahgora neste PC.

        A sessao web vinculada e uma fonte valida de leitura do espelho mesmo
        quando nao dependemos das credenciais salvas para fazer a consulta.
        """
        try:
            root = _base_dir() / "ahgora_browser_profile"
            if not root.exists():
                return False
            for sub in ("storage", "cache"):
                folder = root / sub
                if folder.exists() and any(folder.rglob("*")):
                    return True
            return False
        except Exception:
            return False

    def _can_sync_ahgora(self) -> bool:
        return self._credentials_available() or self._browser_session_available()
'''
if old not in ps:
    raise SystemExit('anchor credentials nao encontrado')
ps=ps.replace(old,new,1)

# Onde o ALIYVO decidia se podia sincronizar, aceitar tambem sessao web persistida.
ps=ps.replace('self._credentials_available()', 'self._can_sync_ahgora()')

# Corrigir a propria implementacao de _can_sync_ahgora que foi afetada pelo replace global.
ps=ps.replace(
    'return self._can_sync_ahgora() or self._browser_session_available()',
    'return self._credentials_available() or self._browser_session_available()',
    1
)

# sync_ahgora_async: se nao ha credenciais mas ha sessao web, sincroniza normalmente.
old='''    def sync_ahgora_async(self, reason: str = "manual") -> None:
        if not self._can_sync_ahgora():
            if reason in {"manual", "settings"}:
                self.show_ahgora_settings()
            else:
                self.check_now()
            return
        self._sync_via_persistent_browser(reason=reason)
'''
new='''    def sync_ahgora_async(self, reason: str = "manual") -> None:
        if not self._can_sync_ahgora():
            if reason in {"manual", "settings"}:
                self.show_ahgora_settings()
            else:
                self.check_now()
            return
        self._sync_via_persistent_browser(reason=reason)
'''
# Mantem bloco como gate de sanidade; global replace ja faz o comportamento correto.
if old not in ps:
    raise SystemExit('sync_ahgora_async esperado nao encontrado')

# No dialogo de vinculacao, quando o usuario ja esta autenticado e o espelho abrir,
# sincronizar automaticamente. Evita ficar mostrando "nao batido" ate clicar no botao.
anchor='''        dlg.finished.connect(finished)
        view.setUrl(QUrl(self._company_external_url()))
        dlg.show()
'''
insert='''        dlg.finished.connect(finished)

        auto_sync = {"started": False}
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
            # O portal ja abriu autenticado. Aguarda renderizacao e usa a mesma
            # sessao/cookies para consultar o espelho. Nao registra batida.
            auto_sync["started"] = True
            QTimer.singleShot(900, start_sync)

        view.loadFinished.connect(maybe_auto_sync_after_login)
        view.setUrl(QUrl(self._company_external_url()))
        dlg.show()
'''
if anchor not in ps:
    raise SystemExit('anchor browser link nao encontrado')
ps=ps.replace(anchor,insert,1)

# Mensagem visual mais clara: batida tardia continua sendo batida confirmada.
old='''        if status == "confirmed":
            actual = row.get("actual_time") or "--:--"
            source = "Ahgora" if row.get("source") == "ahgora_sync" else "local"
            return f"✅ {source} {str(actual)[:5]}"
'''
new='''        if status == "confirmed":
            actual = row.get("actual_time") or "--:--"
            source = "Ahgora" if row.get("source") == "ahgora_sync" else "local"
            try:
                sh, sm = str(row.get("scheduled_time") or "00:00").split(":")[:2]
                ah, am = str(actual)[:5].split(":")[:2]
                delay = (int(ah) * 60 + int(am)) - (int(sh) * 60 + int(sm))
            except Exception:
                delay = 0
            late = f" • atrasado {delay} min" if delay > 0 and row.get("source") == "ahgora_sync" else ""
            return f"✅ {source} {str(actual)[:5]}{late}"
'''
if old not in ps:
    raise SystemExit('anchor status_text nao encontrado')
ps=ps.replace(old,new,1)

main.write_text(ms,encoding='utf-8')
p.write_text(ps,encoding='utf-8')
print('PATCH_PONTO_LATE_SYNC_V2316=OK')
