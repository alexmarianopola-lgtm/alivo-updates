from pathlib import Path
import sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
p=root/'_app'/'aliyvo_ponto.py'

ms=main.read_text(encoding='utf-8')
ps=p.read_text(encoding='utf-8')

if 'ALIYVO_VERSION = "0.23.17"' not in ms:
    raise SystemExit('base main 0.23.17 nao encontrada')
ms=ms.replace('ALIYVO_VERSION = "0.23.17"','ALIYVO_VERSION = "0.23.18"',1)
ms=ms.replace('aliyvo_version="0.23.17"','aliyvo_version="0.23.18"')

if 'POINT_MODULE_VERSION = "0.23.17"' not in ps:
    raise SystemExit('modulo ponto 0.23.17 nao encontrado')
ps=ps.replace('POINT_MODULE_VERSION = "0.23.17"','POINT_MODULE_VERSION = "0.23.18"',1)

anchor='''    def _ensure_state_no_recursion(self, now: datetime) -> None:
        normalized = normalize_state(self._state, now)
        if normalized.get("date") != self._state.get("date"):
            self._state = normalized
'''
insert='''    def _point_alerts_paused_today(self) -> bool:
        try:
            return str(self._state.get("alerts_paused_date") or "") == _date_key(datetime.now())
        except Exception:
            return False

    def pause_point_alerts_today(self) -> None:
        self._ensure_today()
        self._state["alerts_paused_date"] = _date_key(datetime.now())
        self._state["alerts_paused_at"] = datetime.now().isoformat(timespec="seconds")
        self._log("point_alerts_paused_today")
        self._save_state()
        try:
            if self._dialog is not None:
                self._dialog.close()
        except Exception:
            pass
        self._dialog = None
        self._schedule_in(15 * 60 * 1000)

    def resume_point_alerts_today(self) -> None:
        self._state.pop("alerts_paused_date", None)
        self._state.pop("alerts_paused_at", None)
        self._save_state()
        self._last_notified_key = ""
        QTimer.singleShot(100, self.check_now)

'''
if anchor not in ps:
    raise SystemExit('anchor ensure state nao encontrado')
ps=ps.replace(anchor,insert+anchor,1)

old='''        if pending:
            key = _date_key(now) + "|" + pending["id"]
            if self._last_notified_key != key:
                self._last_notified_key = key
                self._log("point_due", slot_id=pending["id"], scheduled=pending["time"])
            if self._dialog is None or not self._dialog.isVisible():
                self.show_dialog(manual=False)
            self._schedule_in(60_000 if self._can_sync_ahgora() else 120_000)
            return
'''
new='''        if pending:
            if self._point_alerts_paused_today():
                self._schedule_in(15 * 60 * 1000)
                return
            key = _date_key(now) + "|" + pending["id"]
            if self._last_notified_key != key:
                self._last_notified_key = key
                self._log("point_due", slot_id=pending["id"], scheduled=pending["time"])
            if self._dialog is None or not self._dialog.isVisible():
                self.show_dialog(manual=False)
            self._schedule_in(60_000 if self._can_sync_ahgora() else 120_000)
            return
'''
if old not in ps:
    raise SystemExit('anchor check_now pending nao encontrado')
ps=ps.replace(old,new,1)

anchor='''        if pending:
            badge = QLabel("🔴 PONTO PENDENTE • " + pending["label"] + " • " + pending["time"])
'''
insert='''        if pending and not self._point_alerts_paused_today():
            pause_btn = QPushButton("⏸  PAUSAR AVISOS DE PONTO HOJE")
            pause_btn.setToolTip("Oculta os alertas do ALIYVO até amanhã. Não altera nenhuma batida no Ahgora.")
            pause_btn.setStyleSheet(
                "QPushButton{background:#1D3140;color:#DCEAF3;border:1px solid #5F7F94;"
                "border-radius:8px;padding:9px;font-size:10px;font-weight:800;}"
                "QPushButton:hover{background:#294456;border-color:#8CB4CC;}"
            )
            pause_btn.clicked.connect(self.pause_point_alerts_today)
            lay.addWidget(pause_btn)

'''
if anchor not in ps:
    raise SystemExit('anchor dialog pending nao encontrado')
ps=ps.replace(anchor,insert+anchor,1)

anchor='''        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
'''
insert='''        if self._point_alerts_paused_today():
            paused = QLabel("⏸ Avisos automáticos de ponto pausados até amanhã. O Ahgora não foi alterado.")
            paused.setWordWrap(True)
            paused.setStyleSheet(
                "background:#263544;color:#D8E7F0;border:1px solid #587083;"
                "border-radius:8px;padding:9px;font-size:10px;font-weight:800;"
            )
            lay.addWidget(paused)
            resume = QPushButton("REATIVAR AVISOS")
            resume.clicked.connect(self.resume_point_alerts_today)
            lay.addWidget(resume)

'''
if anchor not in ps:
    raise SystemExit('anchor sep nao encontrado')
ps=ps.replace(anchor,insert+anchor,1)

main.write_text(ms,encoding='utf-8')
p.write_text(ps,encoding='utf-8')
print('PATCH_PONTO_PAUSE_ALERTS_V2318=OK')
