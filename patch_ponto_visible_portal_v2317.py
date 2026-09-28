from pathlib import Path
import sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
p=root/'_app'/'aliyvo_ponto.py'

ms=main.read_text(encoding='utf-8')
ps=p.read_text(encoding='utf-8')

if 'ALIYVO_VERSION = "0.23.16"' not in ms:
    raise SystemExit('base main 0.23.16 nao encontrada')
ms=ms.replace('ALIYVO_VERSION = "0.23.16"','ALIYVO_VERSION = "0.23.17"',1)
ms=ms.replace('aliyvo_version="0.23.16"','aliyvo_version="0.23.17"')

if 'POINT_MODULE_VERSION = "0.23.16"' not in ps:
    raise SystemExit('modulo ponto 0.23.16 nao encontrado')
ps=ps.replace('POINT_MODULE_VERSION = "0.23.16"','POINT_MODULE_VERSION = "0.23.17"',1)

anchor='''    def _finish_browser_link_sync(
        self,
        dlg: QDialog,
        button: QPushButton,
        ok: bool,
        message: str,
    ) -> None:
'''
helper='''    def _sync_from_visible_ahgora_portal(self, view: QWebEngineView, *, reason: str, done=None) -> None:
        """Lê SOMENTE as batidas já exibidas no portal oficial aberto.

        Algumas contas autenticam corretamente no MyAhgora, mas a navegação direta
        para /api-espelho/apuracao/ devolve HTML em vez de JSON. Nesse caso, a tela
        oficial já mostra as batidas reais do dia (os círculos de horário). Esta
        rotina identifica apenas horários dentro de controles circulares/ovais e
        ignora saldo de banco de horas e "Horas Previstas".
        """
        if self._sync_busy:
            if done:
                done(False, "Já existe uma sincronização em andamento.")
            return

        js = r"""
(() => {
  const timeRx = /^([01]?\d|2[0-3]):[0-5]\d$/;
  const out = [];
  const seen = new Set();

  function visible(el){
    const r=el.getBoundingClientRect();
    const cs=getComputedStyle(el);
    return r.width>0 && r.height>0 && cs.display!=='none' && cs.visibility!=='hidden' && Number(cs.opacity||1)>0;
  }
  function roundedPunchAncestor(el){
    let n=el;
    for(let i=0;i<6 && n;i++,n=n.parentElement){
      if(!visible(n)) continue;
      const r=n.getBoundingClientRect();
      if(r.width<30 || r.height<30 || r.width>130 || r.height>130) continue;
      const cs=getComputedStyle(n);
      const br=parseFloat(cs.borderTopLeftRadius||'0')||0;
      const bw=Math.max(
        parseFloat(cs.borderTopWidth||'0')||0,
        parseFloat(cs.borderRightWidth||'0')||0,
        parseFloat(cs.borderBottomWidth||'0')||0,
        parseFloat(cs.borderLeftWidth||'0')||0
      );
      const roughlyRound=Math.abs(r.width-r.height)<=Math.max(16,Math.min(r.width,r.height)*0.35);
      if(roughlyRound && (br>=14 || bw>=1)) return {el:n,rect:r,br:br,bw:bw};
    }
    return null;
  }

  for(const el of Array.from(document.querySelectorAll('body *'))){
    if(!visible(el)) continue;
    if(el.children.length>0) continue;
    const txt=(el.textContent||'').trim();
    if(!timeRx.test(txt) || seen.has(txt)) continue;

    const context=(el.parentElement?.parentElement?.innerText||'').toLowerCase();
    if(context.includes('saldo de banco de horas')) continue;
    if(context.includes('horas previstas')) continue;

    const circle=roundedPunchAncestor(el);
    if(!circle) continue;

    seen.add(txt);
    out.push({
      time:txt,
      x:Math.round(circle.rect.x),
      y:Math.round(circle.rect.y),
      w:Math.round(circle.rect.width),
      h:Math.round(circle.rect.height)
    });
  }

  out.sort((a,b)=>a.x-b.x);
  return {
    url:location.href,
    title:document.title,
    punches:out.map(x=>x.time),
    details:out
  };
})()
"""

        self._sync_busy = True
        self._log("ahgora_visible_portal_sync_started", reason=reason)

        def finish(result):
            try:
                data = result if isinstance(result, dict) else {}
                punches = [str(x) for x in (data.get("punches") or []) if str(x).strip()][:12]
                if not punches:
                    self._sync_busy = False
                    # Sem batidas visíveis, usa a API antiga como fallback.
                    self._sync_using_view(view, reason=reason + "_api_fallback", done=done)
                    return

                now = datetime.now()
                month_key = _mirror_month_key(now)
                payload = {
                    "punches": punches,
                    "reason": reason + "_visible_portal",
                    "validation": {
                        "day_key": _date_key(now),
                        "month_key": month_key,
                        "punch_count": len(punches),
                        "session_ok": True,
                        "modern_api": False,
                        "visible_portal": True,
                    },
                }
                self._sync_busy = False
                self._log(
                    "ahgora_visible_portal_sync_ok",
                    punches_count=len(punches),
                    punches="|".join(punches),
                    url=str(data.get("url") or "")[:180],
                )
                self.syncFinished.emit(True, payload, "")
                if done:
                    QTimer.singleShot(50, lambda: done(True, "OK"))
            except Exception as exc:
                self._sync_busy = False
                self._log("ahgora_visible_portal_sync_error", error=repr(exc))
                self._sync_using_view(view, reason=reason + "_api_fallback", done=done)

        try:
            view.page().runJavaScript(js, finish)
        except Exception as exc:
            self._sync_busy = False
            self._log("ahgora_visible_portal_js_error", error=repr(exc))
            self._sync_using_view(view, reason=reason + "_api_fallback", done=done)

'''
if anchor not in ps:
    raise SystemExit('anchor finish browser link nao encontrado')
ps=ps.replace(anchor,helper+anchor,1)

old='''        def start_sync():
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
new='''        def start_sync():
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
if old not in ps:
    raise SystemExit('start_sync esperado nao encontrado')
ps=ps.replace(old,new,1)

# O sync em segundo plano continua usando a API persistente. Quando o dialogo do portal
# estiver aberto, prefira ler a propria tela oficial que ja esta autenticada.
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
if old not in ps:
    raise SystemExit('sync_ahgora_async esperado nao encontrado')
ps=ps.replace(old,new,1)

# Mostrar no diagnostico se a fonte foi a tela visivel.
old='''                "API atual do espelho: " + ("SIM" if validation.get("modern_api") else "-"),
                "Mês consultado: " + str(validation.get("month_key") or "-"),
'''
new='''                "API atual do espelho: " + ("SIM" if validation.get("modern_api") else "-"),
                "Leitura da tela oficial: " + ("SIM" if validation.get("visible_portal") else "-"),
                "Mês consultado: " + str(validation.get("month_key") or "-"),
'''
if old not in ps:
    raise SystemExit('diagnostico anchor nao encontrado')
ps=ps.replace(old,new,1)

# Preservar flag visible_portal no estado.
old='''                "modern_api": bool(validation.get("modern_api")),
            }
'''
new='''                "modern_api": bool(validation.get("modern_api")),
                "visible_portal": bool(validation.get("visible_portal")),
            }
'''
if old not in ps:
    raise SystemExit('validation state anchor nao encontrado')
ps=ps.replace(old,new,1)

main.write_text(ms,encoding='utf-8')
p.write_text(ps,encoding='utf-8')
print('PATCH_PONTO_VISIBLE_PORTAL_V2317=OK')
