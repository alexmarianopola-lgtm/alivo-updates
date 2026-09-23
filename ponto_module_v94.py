from __future__ import annotations

import base64
import ctypes
import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from ctypes import POINTER, Structure, byref, c_char, c_void_p
from ctypes.wintypes import DWORD
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

POINT_MODULE_VERSION = "0.22.94"
POINT_API_PORT = 17892
POINT_API_HEADER = "X-ALIYVO-Ponto"
POINT_API_SECRET = "aliyvo-ponto-02293"

AHGORA_MIRROR_URL = "https://www.ahgora.com.br/externo/getApuracao"
AHGORA_PUNCH_URL = "https://www.ahgora.com.br/batidaonline/verifyIdentification"

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
        return {
            "date": day,
            "slots": {},
            "updated_at": None,
            "ahgora": {
                "last_sync_at": None,
                "last_sync_ok": False,
                "last_error": "",
                "punches_today": [],
            },
        }
    if not isinstance(raw.get("slots"), dict):
        raw["slots"] = {}
    if not isinstance(raw.get("ahgora"), dict):
        raw["ahgora"] = {
            "last_sync_at": None,
            "last_sync_ok": False,
            "last_error": "",
            "punches_today": [],
        }
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
    if is_workday(now):
        current = _now_minutes(now)
        for slot in POINT_SLOTS:
            if current < _slot_minutes(slot) and slot_status(state, slot["id"]) not in RESOLVED_STATUSES:
                h, m = [int(x) for x in slot["time"].split(":")]
                return now.replace(hour=h, minute=m, second=0, microsecond=0)
    probe = (now + timedelta(days=1)).replace(hour=7, minute=50, second=0, microsecond=0)
    for _ in range(8):
        if probe.weekday() < 5:
            return probe
        probe += timedelta(days=1)
    return now + timedelta(hours=12)


def _base_dir() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    return root / "ALIYVO"


class _DATA_BLOB(Structure):
    _fields_ = [("cbData", DWORD), ("pbData", POINTER(c_char))]


def _blob_from_bytes(data: bytes):
    buf = ctypes.create_string_buffer(data, len(data))
    blob = _DATA_BLOB(len(data), ctypes.cast(buf, POINTER(c_char)))
    return blob, buf


def _dpapi_protect(text: str) -> str:
    if os.name != "nt":
        raise RuntimeError("Proteção DPAPI disponível somente no Windows.")
    raw = text.encode("utf-8")
    in_blob, in_buf = _blob_from_bytes(raw)
    out_blob = _DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptProtectData(
        byref(in_blob),
        "ALIYVO Ahgora",
        None,
        None,
        None,
        0,
        byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        encrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(c_void_p(ctypes.addressof(out_blob.pbData.contents)))
    return base64.b64encode(encrypted).decode("ascii")


def _dpapi_unprotect(encoded: str) -> str:
    if os.name != "nt":
        raise RuntimeError("Proteção DPAPI disponível somente no Windows.")
    raw = base64.b64decode(encoded.encode("ascii"))
    in_blob, in_buf = _blob_from_bytes(raw)
    out_blob = _DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptUnprotectData(
        byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        clear = ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(c_void_p(ctypes.addressof(out_blob.pbData.contents)))
    return clear.decode("utf-8")


def _normalize_punch_time(value: Any) -> str:
    s = str(value or "").strip()
    digits = "".join(ch for ch in s if ch.isdigit())
    if ":" in s:
        parts = s.split(":")
        if len(parts) >= 2:
            try:
                return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
            except Exception:
                pass
    if len(digits) >= 4:
        return f"{digits[-4:-2]}:{digits[-2:]}"
    return s


def extract_today_punches(payload: Any, now: datetime) -> list[str]:
    """Extrai as batidas reais de hoje da resposta do espelho Ahgora."""
    if not isinstance(payload, dict):
        return []
    days = payload.get("dias")
    if not isinstance(days, dict):
        return []
    day = days.get(_date_key(now))
    if not isinstance(day, dict):
        return []
    punches = day.get("batidas")
    if not isinstance(punches, list):
        return []
    out: list[str] = []
    for item in punches:
        if not isinstance(item, dict):
            continue
        hour = _normalize_punch_time(item.get("hora"))
        if hour and hour not in out:
            out.append(hour)
    return out


def validate_mirror_payload(
    payload: Any,
    now: datetime,
    expected_registration: str = "",
    expected_company: str = "",
) -> dict[str, Any]:
    """Valida a resposta do espelho antes de tratá-la como sincronização bem-sucedida."""
    if not isinstance(payload, dict):
        raise RuntimeError("O Ahgora retornou uma resposta inválida.")

    error = str(payload.get("error") or "").strip()
    if error:
        known = {
            "empty_required_data": "O Ahgora informou que faltam dados obrigatórios.",
            "not_found": "O Ahgora não encontrou funcionário/empresa com os dados informados.",
        }
        raise RuntimeError(known.get(error, "O Ahgora retornou erro: " + error))

    company = payload.get("empresa")
    employee = payload.get("funcionario")
    days = payload.get("dias")
    if not isinstance(company, dict) or not isinstance(employee, dict) or not isinstance(days, dict):
        raise RuntimeError("O Ahgora respondeu, mas não retornou um espelho de ponto válido.")

    returned_registration = str(employee.get("matricula") or "").strip()
    returned_company = str(company.get("empresa") or "").strip()
    if expected_registration and returned_registration and returned_registration != str(expected_registration).strip():
        raise RuntimeError("A matrícula retornada pelo Ahgora não corresponde à matrícula configurada.")
    if expected_company and returned_company and returned_company != str(expected_company).strip():
        raise RuntimeError("O código da empresa retornado pelo Ahgora não corresponde ao configurado.")

    day_key = _date_key(now)
    day = days.get(day_key)
    if not isinstance(day, dict):
        raise RuntimeError(
            "O Ahgora respondeu, mas não retornou os dados de hoje (" + day_key + ")."
        )

    raw_punches = day.get("batidas")
    if not isinstance(raw_punches, list):
        raise RuntimeError("O Ahgora retornou o dia de hoje sem a lista de batidas.")

    return {
        "registration_match": True,
        "company_match": True,
        "day_key": day_key,
        "punch_count": len(raw_punches),
    }


def reconcile_real_punches(state: dict[str, Any], punches: list[str], now: datetime) -> dict[str, Any]:
    """Mapeia 1ª/2ª/3ª/4ª batida real para os quatro eventos do dia."""
    state = normalize_state(state, now)
    slots = state.setdefault("slots", {})
    for index, slot in enumerate(POINT_SLOTS):
        existing = slots.get(slot["id"]) if isinstance(slots.get(slot["id"]), dict) else {}
        if index < len(punches):
            slots[slot["id"]] = {
                "status": "confirmed",
                "scheduled_time": slot["time"],
                "resolved_at": now.isoformat(timespec="seconds"),
                "actual_time": punches[index],
                "source": "ahgora_sync",
            }
        else:
            # Uma sincronização real bem-sucedida é a fonte de verdade.
            # Se o espelho não contém esta batida, removemos estados locais antigos
            # (inclusive "missed" marcado nas versões RC anteriores).
            slots.pop(slot["id"], None)
    return state


def _post_form_json(url: str, fields: dict[str, Any], timeout: float = 12.0) -> dict[str, Any]:
    data = urllib.parse.urlencode({k: str(v) for k, v in fields.items()}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "ALIYVO/0.22.94",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(2_000_000)
    except urllib.error.HTTPError as exc:
        body = exc.read(200_000)
        msg = body.decode("utf-8", "replace").strip()
        raise RuntimeError(f"Ahgora HTTP {exc.code}: {msg[:220]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Não foi possível conectar ao Ahgora: {exc.reason}") from exc
    try:
        decoded = json.loads(body.decode("utf-8", "replace"))
    except Exception as exc:
        preview = body.decode("utf-8", "replace").strip()
        raise RuntimeError(f"Resposta inesperada do Ahgora: {preview[:220]}") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError("Resposta inesperada do Ahgora.")
    return decoded


class AliyvoPontoController(QObject):
    """Controle de ponto com sincronização Ahgora.

    A batida nunca é automática: o POST de registro só ocorre após clique e
    confirmação explícita do usuário.
    """

    apiCommand = pyqtSignal(str, str)
    syncFinished = pyqtSignal(bool, object, str)
    punchFinished = pyqtSignal(bool, object, str)

    def __init__(self, owner: QWidget, nav_button: QPushButton | None = None):
        super().__init__(owner)
        self.owner = owner
        self.nav_button = nav_button
        self._state_file = _base_dir() / "ponto" / "status.json"
        self._credentials_file = _base_dir() / "ponto" / "ahgora_credentials.dpapi"
        self._log_file = _base_dir() / "logs" / "DIAGNOSTICO_PONTO_02294.jsonl"
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
        self._sync_busy = False
        self._punch_busy = False
        self._force_check_after_sync = False
        self.apiCommand.connect(self._on_api_command)
        self.syncFinished.connect(self._on_sync_finished)
        self.punchFinished.connect(self._on_punch_finished)

    # ---------- startup / persistence ----------

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
        if self._credentials_available():
            QTimer.singleShot(450, lambda: self.sync_ahgora_async(reason="startup"))
        else:
            QTimer.singleShot(350, self.check_now)

    def _on_application_state(self, state) -> None:
        try:
            if state != Qt.ApplicationState.ApplicationActive:
                return
            if self._credentials_available() and self._sync_is_stale(60):
                QTimer.singleShot(150, lambda: self.sync_ahgora_async(reason="focus"))
            else:
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
                if key.lower() in {"password", "senha"}:
                    continue
                if isinstance(value, (str, int, float, bool)) or value is None:
                    row[str(key)] = value
            with self._log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # ---------- encrypted Ahgora credentials ----------

    def _credentials_available(self) -> bool:
        try:
            cfg = self._load_credentials()
            return bool(cfg.get("registration") and cfg.get("password") and cfg.get("company_id"))
        except Exception:
            return False

    def _load_credentials(self) -> dict[str, str]:
        if not self._credentials_file.exists():
            return {}
        encrypted = self._credentials_file.read_text(encoding="ascii").strip()
        if not encrypted:
            return {}
        data = json.loads(_dpapi_unprotect(encrypted))
        if not isinstance(data, dict):
            return {}
        return {
            "registration": str(data.get("registration") or "").strip(),
            "password": str(data.get("password") or ""),
            "company_id": str(data.get("company_id") or "").strip(),
            "identity": str(data.get("identity") or "").strip(),
        }

    def _save_credentials(self, config: dict[str, str]) -> None:
        safe = {
            "registration": str(config.get("registration") or "").strip(),
            "password": str(config.get("password") or ""),
            "company_id": str(config.get("company_id") or "").strip(),
            "identity": str(config.get("identity") or "").strip(),
        }
        if not safe["registration"] or not safe["password"] or not safe["company_id"]:
            raise ValueError("Preencha matrícula, senha e código da empresa.")
        if not safe["identity"]:
            safe["identity"] = safe["company_id"]
        self._credentials_file.parent.mkdir(parents=True, exist_ok=True)
        encrypted = _dpapi_protect(json.dumps(safe, ensure_ascii=False))
        tmp = self._credentials_file.with_suffix(".tmp")
        tmp.write_text(encrypted, encoding="ascii")
        tmp.replace(self._credentials_file)
        self._log("ahgora_credentials_saved", company_id=safe["company_id"], registration_set=True)

    def show_ahgora_settings(self) -> None:
        try:
            current = self._load_credentials()
        except Exception:
            current = {}

        dlg = QDialog(self.owner)
        dlg.setWindowTitle("ALIYVO • Conectar Ahgora")
        dlg.setMinimumWidth(510)
        dlg.setStyleSheet(
            "QDialog{background:#081827;color:#F4FAF8;}"
            "QLabel{color:#DDE9F2;}"
            "QLineEdit{background:#10283A;color:#FFFFFF;border:1px solid #284A62;"
            "border-radius:6px;padding:8px;}"
            "QPushButton{background:#0B2E35;color:white;border:1px solid #20C77A;"
            "border-radius:7px;padding:9px 12px;font-weight:800;}"
            "QPushButton:hover{background:#104037;border-color:#20E983;}"
        )
        root = QVBoxLayout(dlg)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(12)

        title = QLabel("CONECTAR AO AHGORA")
        title.setStyleSheet("font-size:18px;font-weight:900;color:white;")
        root.addWidget(title)

        explain = QLabel(
            "O ALIYVO usará a consulta do espelho do Ahgora para conferir as batidas reais. "
            "Sua senha fica criptografada pelo Windows neste computador e não é gravada nos logs."
        )
        explain.setWordWrap(True)
        explain.setStyleSheet("color:#AFC2D0;font-size:11px;")
        root.addWidget(explain)

        form = QFormLayout()
        form.setSpacing(9)
        registration = QLineEdit(current.get("registration", ""))
        registration.setPlaceholderText("Sua matrícula no Ahgora")
        password = QLineEdit(current.get("password", ""))
        password.setEchoMode(QLineEdit.EchoMode.Password)
        password.setPlaceholderText("Sua senha do Ahgora")
        company = QLineEdit(current.get("company_id", ""))
        company.setPlaceholderText("Código usado no espelho / link externo")
        identity = QLineEdit(current.get("identity", ""))
        identity.setPlaceholderText("Código de ativação da Batida Online")

        form.addRow("Matrícula:", registration)
        form.addRow("Senha:", password)
        form.addRow("Código da empresa:", company)
        form.addRow("Código de ativação:", identity)
        root.addLayout(form)

        hint = QLabel(
            "Se o código de ativação for o mesmo da empresa, pode deixar esse último campo em branco. "
            "Salvar/testar NÃO bate ponto; apenas consulta o espelho."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#7F96A8;font-size:10px;")
        root.addWidget(hint)

        actions = QHBoxLayout()
        save = QPushButton("🔐 SALVAR E SINCRONIZAR")
        cancel = QPushButton("Cancelar")
        cancel.setStyleSheet(
            "QPushButton{background:#142A3B;color:#DCE8F1;border:1px solid #2A465B;"
            "border-radius:7px;padding:9px;font-weight:700;}"
        )
        actions.addWidget(save, 1)
        actions.addWidget(cancel)
        root.addLayout(actions)

        def do_save():
            try:
                self._save_credentials(
                    {
                        "registration": registration.text(),
                        "password": password.text(),
                        "company_id": company.text(),
                        "identity": identity.text(),
                    }
                )
            except Exception as exc:
                QMessageBox.warning(dlg, "Não foi possível salvar", str(exc))
                return
            dlg.accept()
            self.sync_ahgora_async(reason="settings")

        save.clicked.connect(do_save)
        cancel.clicked.connect(dlg.reject)
        dlg.exec()

    # ---------- Ahgora network ----------

    def _sync_is_stale(self, seconds: int) -> bool:
        ah = self._state.get("ahgora") or {}
        value = ah.get("last_sync_at")
        if not value:
            return True
        try:
            dt = datetime.fromisoformat(str(value))
            return (datetime.now() - dt).total_seconds() >= seconds
        except Exception:
            return True

    def sync_ahgora_async(self, reason: str = "manual") -> None:
        if self._sync_busy:
            return
        if not self._credentials_available():
            if reason in {"manual", "settings"}:
                self.show_ahgora_settings()
            else:
                self.check_now()
            return
        self._sync_busy = True
        self._log("ahgora_sync_started", reason=reason)

        def worker():
            try:
                cfg = self._load_credentials()
                now = datetime.now()
                payload = _post_form_json(
                    AHGORA_MIRROR_URL,
                    {
                        "ano": now.year,
                        "company": cfg["company_id"],
                        "matricula": cfg["registration"],
                        "mes": now.month,
                        "senha": cfg["password"],
                    },
                )
                validation = validate_mirror_payload(
                    payload,
                    now,
                    expected_registration=cfg["registration"],
                    expected_company=cfg["company_id"],
                )
                punches = extract_today_punches(payload, now)
                self.syncFinished.emit(
                    True,
                    {
                        "payload": payload,
                        "punches": punches,
                        "reason": reason,
                        "validation": validation,
                    },
                    "",
                )
            except Exception as exc:
                self.syncFinished.emit(False, {"reason": reason}, str(exc))

        threading.Thread(target=worker, name="ALIYVO-Ahgora-Sync", daemon=True).start()

    def _on_sync_finished(self, ok: bool, data: object, error: str) -> None:
        self._sync_busy = False
        self._ensure_today()
        ah = self._state.setdefault("ahgora", {})
        ah["last_sync_at"] = datetime.now().isoformat(timespec="seconds")
        ah["last_sync_ok"] = bool(ok)
        ah["last_error"] = "" if ok else str(error)[:500]

        if ok and isinstance(data, dict):
            punches = [str(x) for x in data.get("punches", [])][:12]
            validation = data.get("validation") if isinstance(data.get("validation"), dict) else {}
            ah["punches_today"] = punches
            ah["validation"] = {
                "day_key": str(validation.get("day_key") or ""),
                "punch_count": int(validation.get("punch_count") or 0),
                "registration_match": bool(validation.get("registration_match")),
                "company_match": bool(validation.get("company_match")),
            }
            self._state = reconcile_real_punches(self._state, punches, datetime.now())
            self._log(
                "ahgora_sync_ok",
                punches_count=len(punches),
                day_present=True,
                registration_match=True,
                company_match=True,
                reason=str(data.get("reason") or ""),
            )
        else:
            self._log("ahgora_sync_error", error=str(error)[:300])

        self._save_state()
        self._rebuild_dialog_if_open()
        QTimer.singleShot(120, self.check_now)

    def punch_ahgora(self) -> None:
        if self._punch_busy:
            return
        if not self._credentials_available():
            self.show_ahgora_settings()
            return
        now = datetime.now()
        pending = pending_slot_for(now, self._state)
        label = pending["label"] if pending else "batida"
        ans = QMessageBox.question(
            self.owner,
            "Registrar ponto agora?",
            f"O ALIYVO vai enviar AGORA uma batida para o Ahgora.\n\n"
            f"Horário deste computador: {now.strftime('%H:%M:%S')}\n"
            f"Evento esperado: {label}\n\n"
            "Confirme somente se você está registrando seu próprio ponto neste momento.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        self._punch_busy = True
        self._log("ahgora_punch_started", expected_slot=pending["id"] if pending else "")

        def worker():
            try:
                cfg = self._load_credentials()
                identity = cfg.get("identity") or cfg.get("company_id") or ""
                payload = _post_form_json(
                    AHGORA_PUNCH_URL,
                    {
                        "account": cfg["registration"],
                        "password": cfg["password"],
                        "identity": identity,
                        "key": "",
                    },
                )
                result = bool(payload.get("result"))
                if not result:
                    msg = (
                        payload.get("message")
                        or payload.get("mensagem")
                        or payload.get("error")
                        or "O Ahgora não confirmou a batida."
                    )
                    raise RuntimeError(str(msg))
                self.punchFinished.emit(True, payload, "")
            except Exception as exc:
                self.punchFinished.emit(False, {}, str(exc))

        threading.Thread(target=worker, name="ALIYVO-Ahgora-Punch", daemon=True).start()

    def _on_punch_finished(self, ok: bool, data: object, error: str) -> None:
        self._punch_busy = False
        if not ok:
            self._log("ahgora_punch_error", error=str(error)[:300])
            QMessageBox.warning(
                self.owner,
                "Batida não confirmada",
                "O ALIYVO não recebeu confirmação do Ahgora.\n\n"
                + str(error)
                + "\n\nNão considere o ponto registrado até o Ahgora confirmar.",
            )
            self._rebuild_dialog_if_open()
            return

        payload = data if isinstance(data, dict) else {}
        raw_punches = payload.get("batidas_dia")
        punches: list[str] = []
        if isinstance(raw_punches, list):
            punches = [_normalize_punch_time(x) for x in raw_punches if _normalize_punch_time(x)]
        if punches:
            ah = self._state.setdefault("ahgora", {})
            ah["punches_today"] = punches
            ah["last_sync_at"] = datetime.now().isoformat(timespec="seconds")
            ah["last_sync_ok"] = True
            ah["last_error"] = ""
            self._state = reconcile_real_punches(self._state, punches, datetime.now())
            self._save_state()

        self._log("ahgora_punch_ok", returned_punches=len(punches))
        time_txt = str(payload.get("time") or "").strip()
        QMessageBox.information(
            self.owner,
            "Ponto registrado",
            "O Ahgora confirmou a batida."
            + (f"\n\nHorário retornado: {time_txt}" if time_txt else "")
            + "\n\nO ALIYVO vai sincronizar o espelho para conferir.",
        )
        self.sync_ahgora_async(reason="after_punch")

    # ---------- local state / UI ----------

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
            ah = state.get("ahgora") or {}
            payload = {
                "ok": True,
                "module_version": POINT_MODULE_VERSION,
                "date": _date_key(now),
                "workday": is_workday(now),
                "pending": pending_slot_for(now, state),
                "next": next_future_slot_for(now, state),
                "missed": [
                    {"id": x.get("id"), "time": x.get("time"), "label": x.get("label")}
                    for x in missed_slots_for(state)
                ],
                "slots": self._status_rows(),
                "ahgora_configured": self._credentials_available(),
                "ahgora_last_sync_at": ah.get("last_sync_at"),
                "ahgora_last_sync_ok": bool(ah.get("last_sync_ok")),
                "ahgora_punches_today": list(ah.get("punches_today") or []),
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
            configured = self._credentials_available()
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
            elif not configured:
                btn.setText("⚙  Ponto • conectar Ahgora")
                btn.setStyleSheet(
                    "QPushButton{background:#162C3D;color:#EAF3FA;border:1px solid #5683A3;"
                    "border-radius:6px;padding:6px 12px;min-height:25px;font-size:11px;font-weight:700;}"
                    "QPushButton:hover{background:#1B374C;border-color:#7EB4D8;}"
                )
            elif not is_workday(now):
                btn.setText("✓  Ponto • sincronizado")
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

        # Antes de acusar uma batida como esquecida, consulta o Ahgora real.
        if self._credentials_available() and self._sync_is_stale(55) and not self._sync_busy:
            self.sync_ahgora_async(reason="due_check")
            self._schedule_in(7_000)
            return

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
            self._schedule_in(60_000 if self._credentials_available() else 120_000)
            return

        target = _next_business_slot_datetime(now, self._state)
        delay = max(1000, int((target - now).total_seconds() * 1000) + 500)
        self._timer.start(min(delay, 24 * 60 * 60 * 1000))

    def _schedule_in(self, ms: int) -> None:
        self._timer.start(max(1000, min(int(ms), 24 * 60 * 60 * 1000)))

    def confirm_pending(self, slot_id: str = "", source: str = "manual_fallback") -> bool:
        self._ensure_today()
        now = datetime.now()
        pending = pending_slot_for(now, self._state)
        if not pending or (slot_id and slot_id != pending["id"]):
            return False
        slots = self._state.setdefault("slots", {})
        slots[pending["id"]] = {
            "status": "confirmed",
            "scheduled_time": pending["time"],
            "resolved_at": now.isoformat(timespec="seconds"),
            "actual_time": now.strftime("%H:%M:%S"),
            "source": source,
        }
        self._log("point_confirmed_fallback", slot_id=pending["id"], scheduled=pending["time"], source=source)
        self._save_state()
        self._after_resolution()
        return True

    def mark_missed(self, slot_id: str = "", source: str = "aliyvo") -> bool:
        self._ensure_today()
        now = datetime.now()
        pending = pending_slot_for(now, self._state)
        if not pending or (slot_id and slot_id != pending["id"]):
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
            source = "Ahgora" if row.get("source") == "ahgora_sync" else "local"
            return f"✅ {source} {str(actual)[:5]}"
        if status == "missed":
            return "🟠 precisa de ajuste"
        if status == "pending":
            return "🔴 pendente"
        return "⏳ aguardando"

    def _rebuild_dialog_if_open(self) -> None:
        if self._dialog is None or not self._dialog.isVisible():
            return
        try:
            self._dialog.close()
        except Exception:
            pass
        self._dialog = None
        QTimer.singleShot(100, lambda: self.show_dialog(manual=True))

    def show_dialog(self, manual: bool = True) -> None:
        self._ensure_today()
        now = datetime.now()
        pending = pending_slot_for(now, self._state)
        configured = self._credentials_available()

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
        dlg.setMinimumWidth(560)
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
        lay.setSpacing(10)

        head = QHBoxLayout()
        title = QLabel("CONTROLE DE PONTO")
        title.setStyleSheet("font-size:18px;font-weight:900;color:#FFFFFF;")
        settings = QPushButton("⚙ Ahgora")
        settings.setMaximumWidth(115)
        settings.clicked.connect(self.show_ahgora_settings)
        head.addWidget(title, 1)
        head.addWidget(settings)
        lay.addLayout(head)

        ah = self._state.get("ahgora") or {}
        if configured and ah.get("last_sync_ok"):
            count = len(ah.get("punches_today") or [])
            if count:
                sync_text = f"● Ahgora conectado • {count} batida(s) real(is) encontrada(s) hoje"
            else:
                sync_text = "● Ahgora consultado • 0 batidas encontradas hoje"
            sync_status = QLabel(sync_text)
            sync_status.setStyleSheet(
                "background:#0B2D27;color:#8EF0BA;border:1px solid #1B8E60;"
                "border-radius:7px;padding:7px;font-size:11px;font-weight:800;"
            )
        elif configured:
            err = str(ah.get("last_error") or "aguardando sincronização")
            sync_status = QLabel("● Ahgora configurado • " + err[:110])
            sync_status.setStyleSheet(
                "background:#3B2A12;color:#FFD58E;border:1px solid #A97628;"
                "border-radius:7px;padding:7px;font-size:11px;font-weight:700;"
            )
        else:
            sync_status = QLabel("⚙ Ahgora ainda não conectado ao ALIYVO")
            sync_status.setStyleSheet(
                "background:#142A3B;color:#CFE3F2;border:1px solid #426985;"
                "border-radius:7px;padding:7px;font-size:11px;font-weight:700;"
            )
        sync_status.setWordWrap(True)
        lay.addWidget(sync_status)

        punches = [str(x) for x in ah.get("punches_today") or []]
        if punches:
            real = QLabel("Batidas reais hoje:  " + "  •  ".join(punches))
            real.setStyleSheet("color:#A9EBC9;font-size:11px;font-weight:800;padding:2px 0;")
            lay.addWidget(real)

        sync_btn = QPushButton("↻ SINCRONIZAR AGORA")
        sync_btn.clicked.connect(lambda: self.sync_ahgora_async(reason="manual"))
        lay.addWidget(sync_btn)

        diag_btn = QPushButton("🔎 DIAGNÓSTICO DA SINCRONIZAÇÃO")
        diag_btn.setStyleSheet(
            "QPushButton{background:#142A3B;color:#DCE8F1;border:1px solid #426985;"
            "border-radius:7px;padding:8px;font-size:10px;font-weight:800;}"
        )

        def show_sync_diag():
            ahg = self._state.get("ahgora") or {}
            validation = ahg.get("validation") if isinstance(ahg.get("validation"), dict) else {}
            lines = [
                "Última sincronização: " + str(ahg.get("last_sync_at") or "nunca"),
                "Consulta válida: " + ("SIM" if ahg.get("last_sync_ok") else "NÃO"),
                "Batidas encontradas hoje: " + str(len(ahg.get("punches_today") or [])),
                "Dia retornado: " + str(validation.get("day_key") or "-"),
                "Matrícula corresponde: " + ("SIM" if validation.get("registration_match") else "-"),
                "Empresa corresponde: " + ("SIM" if validation.get("company_match") else "-"),
            ]
            if ahg.get("last_error"):
                lines.append("Erro: " + str(ahg.get("last_error"))[:500])
            QMessageBox.information(
                dlg,
                "Diagnóstico da sincronização",
                "\n".join(lines)
                + "\n\nEste diagnóstico não mostra sua senha.",
            )

        diag_btn.clicked.connect(show_sync_diag)
        lay.addWidget(diag_btn)

        if pending:
            badge = QLabel("🔴 PONTO PENDENTE • " + pending["label"] + " • " + pending["time"])
            badge.setStyleSheet(
                "background:#3A1720;color:#FFF4F4;border:1px solid #FF5C67;"
                "border-radius:8px;padding:10px;font-size:14px;font-weight:900;"
            )
            lay.addWidget(badge)

            if configured and ah.get("last_sync_ok"):
                punch = QPushButton("🟢  BATER PONTO AGORA NO AHGORA")
                punch.setStyleSheet(
                    "QPushButton{background:#087047;color:white;border:1px solid #20E983;"
                    "border-radius:8px;padding:12px;font-size:13px;font-weight:900;}"
                    "QPushButton:hover{background:#0A8354;}"
                )
                punch.clicked.connect(self.punch_ahgora)
                lay.addWidget(punch)
                info = QLabel(
                    "O botão acima registra a batida somente quando você clicar e confirmar. "
                    "Não existe batida automática por horário."
                )
            else:
                setup = QPushButton("⚙  REVISAR CONEXÃO COM O AHGORA" if configured else "⚙  CONECTAR AO AHGORA")
                setup.clicked.connect(self.show_ahgora_settings)
                lay.addWidget(setup)
                info = QLabel(
                    "A sincronização precisa ser validada antes de liberar batida direta pelo ALIYVO."
                    if configured else
                    "Conecte o Ahgora para o ALIYVO conferir as batidas reais e permitir registrar o ponto aqui."
                )
            info.setWordWrap(True)
            info.setStyleSheet("color:#AFC2D0;font-size:10px;")
            lay.addWidget(info)

            fallback = QCheckBox("Usei o Ahgora oficial e já confirmei a batida (modo de contingência).")
            lay.addWidget(fallback)
            confirm = QPushButton("CONFIRMAR MANUALMENTE")
            confirm.setEnabled(False)
            confirm.setStyleSheet(
                "QPushButton{background:#233441;color:#DDE8EF;border:1px solid #4D6372;"
                "border-radius:7px;padding:8px;font-size:10px;font-weight:800;}"
                "QPushButton:disabled{color:#71828E;border-color:#334956;}"
            )
            fallback.toggled.connect(confirm.setEnabled)
            confirm.clicked.connect(
                lambda _=False, sid=pending["id"]: self.confirm_pending(sid, "manual_fallback")
            )
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
                    "Use somente se você realmente não bateu no Ahgora.\n\n"
                    "O ALIYVO libera as próximas etapas, mas mantém aviso de ajuste necessário.",
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
            "A sincronização usa os registros reais do Ahgora. O registro pelo ALIYVO só acontece "
            "após clique + confirmação e pode depender das permissões definidas pela sua empresa."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#73889A;font-size:10px;margin-top:3px;")
        lay.addWidget(note)

        close_btn = QPushButton("Fechar")
        close_btn.setStyleSheet(
            "QPushButton{background:#142A3B;color:#DCE8F1;border:1px solid #2A465B;"
            "border-radius:7px;padding:8px;font-weight:700;}"
        )
        close_btn.clicked.connect(dlg.close)
        lay.addWidget(close_btn)

        def finished(_result=0):
            if self._dialog is dlg:
                self._dialog = None
            if pending_slot_for(datetime.now(), self._state):
                self._schedule_in(60_000 if self._credentials_available() else 120_000)

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

    # ---------- local bridge for Chrome Sankhya extension ----------

    def _origin_allowed(self, origin: str) -> bool:
        return (not origin) or origin.startswith("chrome-extension://")

    def _start_api(self) -> None:
        if self._api_server is not None:
            return
        controller = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "ALIYVO-Ponto/0.22.94"

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
                if self.path not in ("/confirm", "/missed", "/sync"):
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
                action = self.path.lstrip("/")
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
                self.confirm_pending(slot_id, "chrome_extension_fallback")
            elif action == "missed":
                self.mark_missed(slot_id, "chrome_extension")
            elif action == "sync":
                self.sync_ahgora_async(reason="chrome_extension")
        except Exception as exc:
            self._log("point_api_command_error", action=action, error=repr(exc))
