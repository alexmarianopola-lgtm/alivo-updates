from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

POINT_MODULE_VERSION = "0.22.92"
POINT_API_PORT = 17892
POINT_API_HEADER = "X-ALIYVO-Ponto"
POINT_API_SECRET = "aliyvo-ponto-02292"

POINT_SLOTS = (
    {"id": "entrada", "time": "07:50", "label": "Entrada"},
    {"id": "saida_almoco", "time": "12:08", "label": "Saída para almoço"},
    {"id": "volta_almoco", "time": "13:30", "label": "Volta do almoço"},
    {"id": "saida_final", "time": "18:00", "label": "Saída final"},
)

RESOLVED_STATUSES = {"confirmed", "missed"}


def _date_key(now: datetime) -> str:
    return now.strftime("%Y-%m-%d")


def _slot_minutes(slot: dict[str, str]) -> int:
    h, m = slot["time"].split(":")
    return int(h) * 60 + int(m)


def _now_minutes(now: datetime) -> int:
    return now.hour * 60 + now.minute


def is_workday(now: datetime) -> bool:
    return now.weekday() < 5


def normalize_state(raw: Any, now: datetime) -> dict[str, Any]:
    day = _date_key(now)
    if not isinstance(raw, dict) or raw.get("date") != day:
        return {"date": day, "slots": {}, "updated_at": None}
    slots = raw.get("slots")
    if not isinstance(slots, dict):
        raw["slots"] = {}
    return raw


def slot_status(state: dict[str, Any], slot_id: str) -> str:
    item = (state.get("slots") or {}).get(slot_id)
    if not isinstance(item, dict):
        return "open"
    status = str(item.get("status") or "open")
    return status if status in {"open", "confirmed", "missed"} else "open"


def pending_slot_for(now: datetime, state: dict[str, Any]) -> dict[str, str] | None:
    if not is_workday(now):
        return None
    current = _now_minutes(now)
    for slot in POINT_SLOTS:
        if current >= _slot_minutes(slot) and slot_status(state, slot["id"]) not in RESOLVED_STATUSES:
            return dict(slot)
    return None


def next_future_slot_for(now: datetime, state: dict[str, Any]) -> dict[str, str] | None:
    if not is_workday(now):
        return None
    current = _now_minutes(now)
    for slot in POINT_SLOTS:
        if current < _slot_minutes(slot) and slot_status(state, slot["id"]) not in RESOLVED_STATUSES:
            return dict(slot)
    return None


def missed_slots_for(state: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for slot in POINT_SLOTS:
        if slot_status(state, slot["id"]) == "missed":
            row = dict(slot)
            row.update((state.get("slots") or {}).get(slot["id"]) or {})
            out.append(row)
    return out


def _next_business_slot_datetime(now: datetime, state: dict[str, Any]) -> datetime:
    # First unresolved future slot today.
    if is_workday(now):
        current = _now_minutes(now)
        for slot in POINT_SLOTS:
            if current < _slot_minutes(slot) and slot_status(state, slot["id"]) not in RESOLVED_STATUSES:
                h, m = [int(x) for x in slot["time"].split(":")]
                return now.replace(hour=h, minute=m, second=0, microsecond=0)

    # Otherwise the next weekday begins with 07:50.
    probe = (now + timedelta(days=1)).replace(hour=7, minute=50, second=0, microsecond=0)
    for _ in range(8):
        if probe.weekday() < 5:
            return probe
        probe += timedelta(days=1)
    return now + timedelta(hours=12)


def _base_dir() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    return root / "ALIYVO"


class AliyvoPontoController(QObject):
    """Controle local de lembretes de ponto.

    Não registra ponto no Ahgora e não armazena matrícula/senha.
    """

    apiCommand = pyqtSignal(str, str)

    def __init__(self, owner: QWidget, nav_button: QPushButton | None = None):
        super().__init__(owner)
        self.owner = owner
        self.nav_button = nav_button
        self._state_file = _base_dir() / "ponto" / "status.json"
        self._log_file = _base_dir() / "logs" / "DIAGNOSTICO_PONTO_02292.jsonl"
        self._state: dict[str, Any] = {}
        self._dialog: QDialog | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.check_now)
        self._last_notified_key = ""
        self._snapshot_lock = threading.Lock()
        self._api_snapshot: dict[str, Any] = {}
        self._api_server: ThreadingHTTPServer | None = None
        self._api_thread: threading.Thread | None = None
        self.apiCommand.connect(self._on_api_command)

    def start(self) -> None:
        self._load_state()
        self._update_snapshot()
        self._refresh_nav_button()
        self._start_api()
        app = QApplication.instance()
        if app is not None:
            try:
                app.applicationStateChanged.connect(self._on_application_state)
            except Exception:
                pass
        QTimer.singleShot(350, self.check_now)

    def _on_application_state(self, state) -> None:
        try:
            if state == Qt.ApplicationState.ApplicationActive:
                QTimer.singleShot(150, self.check_now)
        except Exception:
            pass

    def _load_state(self) -> None:
        now = datetime.now()
        raw: Any = {}
        try:
            if self._state_file.exists():
                raw = json.loads(self._state_file.read_text(encoding="utf-8"))
        except Exception as exc:
            self._log("state_read_error", error=repr(exc))
            raw = {}
        self._state = normalize_state(raw, now)
        self._save_state()

    def _ensure_today(self) -> None:
        now = datetime.now()
        normalized = normalize_state(self._state, now)
        if normalized.get("date") != self._state.get("date"):
            self._state = normalized
            self._last_notified_key = ""
            self._save_state()
        else:
            self._state = normalized

    def _save_state(self) -> None:
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state["updated_at"] = datetime.now().isoformat(timespec="seconds")
            tmp = self._state_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self._state_file)
        except Exception as exc:
            self._log("state_write_error", error=repr(exc))
        self._update_snapshot()
        self._refresh_nav_button()

    def _log(self, event: str, **data: Any) -> None:
        try:
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
            row = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "event": str(event),
                "module_version": POINT_MODULE_VERSION,
            }
            for key, value in data.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    row[str(key)] = value
            with self._log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _status_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        slots_state = self._state.get("slots") or {}
        now = datetime.now()
        current = _now_minutes(now)
        for slot in POINT_SLOTS:
            item = slots_state.get(slot["id"]) if isinstance(slots_state, dict) else None
            status = slot_status(self._state, slot["id"])
            if status == "open":
                status = "pending" if is_workday(now) and current >= _slot_minutes(slot) else "future"
            row: dict[str, Any] = {
                "id": slot["id"],
                "time": slot["time"],
                "label": slot["label"],
                "status": status,
            }
            if isinstance(item, dict):
                for key in ("resolved_at", "actual_time", "source"):
                    if item.get(key) is not None:
                        row[key] = item.get(key)
            rows.append(row)
        return rows

    def status_payload(self) -> dict[str, Any]:
        with self._snapshot_lock:
            return deepcopy(self._api_snapshot)

    def _update_snapshot(self) -> None:
        try:
            now = datetime.now()
            state = normalize_state(self._state, now)
            pending = pending_slot_for(now, state)
            nxt = next_future_slot_for(now, state)
            payload = {
                "ok": True,
                "module_version": POINT_MODULE_VERSION,
                "date": _date_key(now),
                "workday": is_workday(now),
                "pending": pending,
                "next": nxt,
                "missed": [{"id": x.get("id"), "time": x.get("time"), "label": x.get("label")} for x in missed_slots_for(state)],
                "slots": self._status_rows(),
            }
            with self._snapshot_lock:
                self._api_snapshot = payload
        except Exception:
            pass

    def _refresh_nav_button(self) -> None:
        btn = self.nav_button
        if btn is None:
            return
        try:
            now = datetime.now()
            self._ensure_state_no_recursion(now)
            pending = pending_slot_for(now, self._state)
            missed = missed_slots_for(self._state)
            nxt = next_future_slot_for(now, self._state)
            if pending:
                btn.setText("🔴  Ponto pendente " + pending["time"])
                btn.setStyleSheet(
                    "QPushButton{background:#3A1720;color:#FFF4F4;border:1px solid #FF5C67;"
                    "border-radius:6px;padding:6px 12px;min-height:25px;font-size:11px;font-weight:800;}"
                    "QPushButton:hover{background:#52202A;border-color:#FF8991;}"
                )
            elif missed:
                btn.setText("🟠  Ponto: ajuste necessário")
                btn.setStyleSheet(
                    "QPushButton{background:#3B2A12;color:#FFF7E6;border:1px solid #F0A43A;"
                    "border-radius:6px;padding:6px 12px;min-height:25px;font-size:11px;font-weight:800;}"
                    "QPushButton:hover{background:#513817;border-color:#FFC46D;}"
                )
            elif not is_workday(now):
                btn.setText("✓  Ponto • fora do expediente")
                btn.setStyleSheet(
                    "QPushButton{background:#0B2D27;color:#E8FFF5;border:1px solid #20B978;"
                    "border-radius:6px;padding:6px 12px;min-height:25px;font-size:11px;font-weight:700;}"
                    "QPushButton:hover{background:#104037;border-color:#20E983;}"
                )
            elif nxt:
                btn.setText("✓  Ponto OK • próx. " + nxt["time"])
                btn.setStyleSheet(
                    "QPushButton{background:#0B2D27;color:#E8FFF5;border:1px solid #20B978;"
                    "border-radius:6px;padding:6px 12px;min-height:25px;font-size:11px;font-weight:700;}"
                    "QPushButton:hover{background:#104037;border-color:#20E983;}"
                )
            else:
                btn.setText("✓  Ponto OK • dia concluído")
                btn.setStyleSheet(
                    "QPushButton{background:#0B2D27;color:#E8FFF5;border:1px solid #20B978;"
                    "border-radius:6px;padding:6px 12px;min-height:25px;font-size:11px;font-weight:700;}"
                    "QPushButton:hover{background:#104037;border-color:#20E983;}"
                )
        except Exception:
            try:
                btn.setText("🕒  Ponto")
            except Exception:
                pass

    def _ensure_state_no_recursion(self, now: datetime) -> None:
        normalized = normalize_state(self._state, now)
        if normalized.get("date") != self._state.get("date"):
            self._state = normalized

    def check_now(self) -> None:
        self._ensure_today()
        now = datetime.now()
        pending = pending_slot_for(now, self._state)
        self._update_snapshot()
        self._refresh_nav_button()

        if pending:
            key = _date_key(now) + "|" + pending["id"]
            if self._last_notified_key != key:
                self._last_notified_key = key
                self._log("point_due", slot_id=pending["id"], scheduled=pending["time"])
            if self._dialog is None or not self._dialog.isVisible():
                self.show_dialog(manual=False)
            self._schedule_in(2 * 60 * 1000)
            return

        target = _next_business_slot_datetime(now, self._state)
        delay = max(1000, int((target - now).total_seconds() * 1000) + 500)
        self._timer.start(min(delay, 24 * 60 * 60 * 1000))

    def _schedule_in(self, ms: int) -> None:
        self._timer.start(max(1000, min(int(ms), 24 * 60 * 60 * 1000)))

    def confirm_pending(self, slot_id: str = "", source: str = "aliyvo") -> bool:
        self._ensure_today()
        now = datetime.now()
        pending = pending_slot_for(now, self._state)
        if not pending:
            return False
        if slot_id and slot_id != pending["id"]:
            return False
        slots = self._state.setdefault("slots", {})
        slots[pending["id"]] = {
            "status": "confirmed",
            "scheduled_time": pending["time"],
            "resolved_at": now.isoformat(timespec="seconds"),
            "actual_time": now.strftime("%H:%M:%S"),
            "source": source,
        }
        self._log("point_confirmed", slot_id=pending["id"], scheduled=pending["time"], source=source)
        self._save_state()
        self._after_resolution()
        return True

    def mark_missed(self, slot_id: str = "", source: str = "aliyvo") -> bool:
        self._ensure_today()
        now = datetime.now()
        pending = pending_slot_for(now, self._state)
        if not pending:
            return False
        if slot_id and slot_id != pending["id"]:
            return False
        slots = self._state.setdefault("slots", {})
        slots[pending["id"]] = {
            "status": "missed",
            "scheduled_time": pending["time"],
            "resolved_at": now.isoformat(timespec="seconds"),
            "actual_time": now.strftime("%H:%M:%S"),
            "source": source,
        }
        self._log("point_missed_needs_adjustment", slot_id=pending["id"], scheduled=pending["time"], source=source)
        self._save_state()
        self._after_resolution()
        return True

    def _after_resolution(self) -> None:
        try:
            if self._dialog is not None:
                self._dialog.close()
        except Exception:
            pass
        self._dialog = None
        self._last_notified_key = ""
        QTimer.singleShot(100, self.check_now)

    def _status_text(self, row: dict[str, Any]) -> str:
        status = row.get("status")
        if status == "confirmed":
            actual = row.get("actual_time") or "--:--"
            return "✅ confirmado " + str(actual)[:5]
        if status == "missed":
            return "🟠 precisa de ajuste"
        if status == "pending":
            return "🔴 pendente"
        return "⏳ aguardando"

    def show_dialog(self, manual: bool = True) -> None:
        self._ensure_today()
        now = datetime.now()
        pending = pending_slot_for(now, self._state)

        if self._dialog is not None and self._dialog.isVisible():
            try:
                self._dialog.raise_()
                self._dialog.activateWindow()
            except Exception:
                pass
            return

        dlg = QDialog(self.owner)
        self._dialog = dlg
        dlg.setWindowTitle("ALIYVO • Controle de Ponto")
        dlg.setModal(False)
        dlg.setMinimumWidth(520)
        dlg.setStyleSheet(
            "QDialog{background:#081827;color:#F4FAF8;}"
            "QLabel{color:#F4FAF8;}"
            "QFrame#pontoCard{background:#0C2235;border:1px solid #173B52;border-radius:10px;}"
            "QCheckBox{color:#F4FAF8;font-size:12px;spacing:9px;}"
            "QPushButton{background:#0B2E35;color:#F4FAF8;border:1px solid #20C77A;"
            "border-radius:7px;padding:9px 12px;font-weight:800;}"
            "QPushButton:hover{background:#104037;border-color:#20E983;}"
        )
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        title = QLabel("CONTROLE DE PONTO")
        title.setStyleSheet("font-size:18px;font-weight:900;color:#FFFFFF;")
        lay.addWidget(title)

        if pending:
            badge = QLabel("🔴 PONTO PENDENTE • " + pending["label"] + " • " + pending["time"])
            badge.setStyleSheet(
                "background:#3A1720;color:#FFF4F4;border:1px solid #FF5C67;"
                "border-radius:8px;padding:10px;font-size:14px;font-weight:900;"
            )
            lay.addWidget(badge)
            info = QLabel(
                "Bata o ponto no Ahgora pelo ícone do Chrome. "
                "Só confirme aqui depois que o Ahgora informar que a batida foi registrada."
            )
            info.setWordWrap(True)
            info.setStyleSheet("color:#C9D8E5;font-size:12px;line-height:1.4;")
            lay.addWidget(info)

            check = QCheckBox("O Ahgora confirmou que minha batida foi registrada.")
            lay.addWidget(check)

            confirm = QPushButton("✅  CONFIRMEI NO AHGORA")
            confirm.setEnabled(False)
            confirm.setStyleSheet(
                "QPushButton{background:#0A6B46;color:white;border:1px solid #20E983;"
                "border-radius:8px;padding:11px;font-size:13px;font-weight:900;}"
                "QPushButton:disabled{background:#233441;color:#81909C;border-color:#3B4D59;}"
                "QPushButton:hover:!disabled{background:#0C8053;}"
            )
            check.toggled.connect(confirm.setEnabled)
            confirm.clicked.connect(lambda _=False, sid=pending["id"]: self.confirm_pending(sid, "aliyvo_dialog"))
            lay.addWidget(confirm)

            missed = QPushButton("⚠  PERDI ESSA BATIDA — PRECISO CORRIGIR")
            missed.setStyleSheet(
                "QPushButton{background:#352A18;color:#FFF4DB;border:1px solid #D99A39;"
                "border-radius:8px;padding:9px;font-size:11px;font-weight:800;}"
                "QPushButton:hover{background:#493820;border-color:#FFC46D;}"
            )

            def on_missed(_checked=False, sid=pending["id"]):
                ans = QMessageBox.question(
                    dlg,
                    "Marcar como perdida?",
                    "Use esta opção somente se você realmente não bateu o ponto no Ahgora.\n\n"
                    "O ALIYVO vai liberar as próximas etapas, mas deixará um aviso de ajuste necessário.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if ans == QMessageBox.StandardButton.Yes:
                    self.mark_missed(sid, "aliyvo_dialog")

            missed.clicked.connect(on_missed)
            lay.addWidget(missed)
        else:
            ok = QLabel("✅ Nenhuma batida pendente agora.")
            ok.setStyleSheet(
                "background:#0B2D27;color:#E8FFF5;border:1px solid #20B978;"
                "border-radius:8px;padding:10px;font-size:13px;font-weight:800;"
            )
            lay.addWidget(ok)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#173B52;")
        lay.addWidget(sep)

        today = QLabel("Hoje")
        today.setStyleSheet("font-size:13px;font-weight:900;color:#BFEBDD;")
        lay.addWidget(today)

        for row in self._status_rows():
            card = QFrame()
            card.setObjectName("pontoCard")
            h = QHBoxLayout(card)
            h.setContentsMargins(12, 8, 12, 8)
            t = QLabel(str(row["time"]))
            t.setStyleSheet("font-size:14px;font-weight:900;color:#FFFFFF;min-width:48px;")
            name = QLabel(str(row["label"]))
            name.setStyleSheet("font-size:12px;font-weight:700;color:#D9E6EF;")
            st = QLabel(self._status_text(row))
            st.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if row.get("status") == "missed":
                st.setStyleSheet("font-size:11px;font-weight:800;color:#FFC46D;")
            elif row.get("status") == "pending":
                st.setStyleSheet("font-size:11px;font-weight:800;color:#FF8991;")
            elif row.get("status") == "confirmed":
                st.setStyleSheet("font-size:11px;font-weight:800;color:#66E3A5;")
            else:
                st.setStyleSheet("font-size:11px;color:#8FA3B5;")
            h.addWidget(t)
            h.addWidget(name, 1)
            h.addWidget(st)
            lay.addWidget(card)

        note = QLabel(
            "O ALIYVO não registra ponto automaticamente e não lê sua matrícula ou senha. "
            "Este módulo serve para impedir que a batida seja esquecida."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#73889A;font-size:10px;margin-top:4px;")
        lay.addWidget(note)

        close_btn = QPushButton("Fechar")
        close_btn.setStyleSheet(
            "QPushButton{background:#142A3B;color:#DCE8F1;border:1px solid #2A465B;"
            "border-radius:7px;padding:8px;font-weight:700;}"
            "QPushButton:hover{background:#1A3448;}"
        )
        close_btn.clicked.connect(dlg.close)
        lay.addWidget(close_btn)

        def finished(_result=0):
            if self._dialog is dlg:
                self._dialog = None
            if pending_slot_for(datetime.now(), self._state):
                self._schedule_in(2 * 60 * 1000)

        dlg.finished.connect(finished)
        dlg.show()
        try:
            dlg.raise_()
            dlg.activateWindow()
            QApplication.alert(self.owner, 0)
        except Exception:
            pass
        if not manual and pending:
            self._log("point_dialog_shown", slot_id=pending["id"], scheduled=pending["time"])

    def _origin_allowed(self, origin: str) -> bool:
        return (not origin) or origin.startswith("chrome-extension://")

    def _start_api(self) -> None:
        if self._api_server is not None:
            return
        controller = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "ALIYVO-Ponto/0.22.92"

            def log_message(self, fmt, *args):
                return

            def _origin(self) -> str:
                return str(self.headers.get("Origin") or "")

            def _authorized(self) -> bool:
                if not controller._origin_allowed(self._origin()):
                    return False
                return str(self.headers.get(POINT_API_HEADER) or "") == POINT_API_SECRET

            def _send(self, code: int, payload: dict[str, Any]):
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                origin = self._origin()
                if origin and controller._origin_allowed(origin):
                    self.send_header("Access-Control-Allow-Origin", origin)
                    self.send_header("Vary", "Origin")
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_OPTIONS(self):
                origin = self._origin()
                if not controller._origin_allowed(origin):
                    self.send_response(403)
                    self.end_headers()
                    return
                self.send_response(204)
                if origin:
                    self.send_header("Access-Control-Allow-Origin", origin)
                    self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", POINT_API_HEADER + ", Content-Type")
                self.send_header("Access-Control-Max-Age", "600")
                self.end_headers()

            def do_GET(self):
                if self.path == "/health":
                    self._send(200, {"ok": True, "module_version": POINT_MODULE_VERSION})
                    return
                if self.path != "/status":
                    self._send(404, {"ok": False, "error": "not_found"})
                    return
                if not self._authorized():
                    self._send(403, {"ok": False, "error": "forbidden"})
                    return
                self._send(200, controller.status_payload())

            def do_POST(self):
                if self.path not in ("/confirm", "/missed"):
                    self._send(404, {"ok": False, "error": "not_found"})
                    return
                if not self._authorized():
                    self._send(403, {"ok": False, "error": "forbidden"})
                    return
                try:
                    length = min(int(self.headers.get("Content-Length") or "0"), 4096)
                    raw = self.rfile.read(length) if length > 0 else b"{}"
                    data = json.loads(raw.decode("utf-8")) if raw else {}
                    slot_id = str(data.get("slot_id") or "")
                except Exception:
                    slot_id = ""
                action = "confirm" if self.path == "/confirm" else "missed"
                controller.apiCommand.emit(action, slot_id)
                self._send(202, {"ok": True, "queued": True, "action": action, "slot_id": slot_id})

        try:
            server = ThreadingHTTPServer(("127.0.0.1", POINT_API_PORT), Handler)
            server.daemon_threads = True
            self._api_server = server
            thread = threading.Thread(target=server.serve_forever, name="ALIYVO-Ponto-Bridge", daemon=True)
            self._api_thread = thread
            thread.start()
            self._log("point_api_started", port=POINT_API_PORT)
        except Exception as exc:
            self._api_server = None
            self._api_thread = None
            self._log("point_api_start_error", port=POINT_API_PORT, error=repr(exc))

    def _on_api_command(self, action: str, slot_id: str) -> None:
        try:
            if action == "confirm":
                self.confirm_pending(slot_id, "chrome_extension")
            elif action == "missed":
                self.mark_missed(slot_id, "chrome_extension")
        except Exception as exc:
            self._log("point_api_command_error", action=action, error=repr(exc))
