# ALIYVO - Analise de Ligacoes por IA
# Captura chamadas do WhatsApp detectadas pelo diagnostico, grava microfone + WASAPI loopback,
# transcreve, avalia, integra CRM e cria follow-up.
from __future__ import annotations

import os, sys, json, time, uuid, wave, threading, tempfile, shutil, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt, QUrl
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QTextEdit, QMessageBox, QComboBox, QCheckBox, QWidget,
    QSplitter
)

APP_DIR = Path(__file__).resolve().parent
VENDOR_DIR = APP_DIR / "vendor"
if VENDOR_DIR.exists() and str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

BASE_DIR = Path(os.environ.get("LOCALAPPDATA") or str(Path.home())) / "ALIYVO" / "ligacoes_ai"
AUDIO_DIR = BASE_DIR / "audios"
DB_FILE = BASE_DIR / "ligacoes.json"
CFG_FILE = BASE_DIR / "config.json"

WEIGHTS = {
    "abordagem": 0.20,
    "tecnica_venda": 0.30,
    "fechamento": 0.30,
    "conhecimento_tecnico": 0.20,
}

VOCABULARY = (
    "Ligação de vendas de autopeças para linha pesada. Termos comuns: Somaforce, Mercedes-Benz, "
    "Scania, Volvo, Iveco, DAF, Volkswagen Caminhões, MAN, Agrale, carreta, implemento, cubo de roda, "
    "rolamento, retentor, lona de freio, tambor de freio, disco, pastilha, cuíca, câmara de freio, "
    "feixe de mola, mola de retorno, terminal, barra de direção, pivô, amortecedor, embreagem, "
    "cardan, cruzeta, diferencial, câmbio, compressor, turbina, filtro, Hengst, Fras-le, Master, "
    "LNG, Paraflu, Meritor, Wabco, Knorr, Nakata, Cofap, SKF, Sabó."
)

SYSTEM_PROMPT = """Você é um coordenador comercial experiente da Somaforce Distribuidora de Autopeças,
atacadista de peças para linha pesada (caminhões, ônibus e implementos), atendendo oficinas,
frotistas e lojas de autopeças em SC e RS.

Você recebe a transcrição de uma ligação entre um VENDEDOR da Somaforce e um CLIENTE.
A transcrição pode não separar perfeitamente os falantes; deduza pelo contexto.

Avalie o vendedor de 0 a 10, usando decimais. Seja exigente e justo:
10 = exemplar; 7 = bom; 5 = mediano; abaixo de 4 = fraco.

Critérios:
1. abordagem: cordialidade e postura, saudação, identificação, chamar o cliente pelo nome,
tom educado e seguro, escuta ativa, não interromper e despedida.
2. tecnica_venda: sondagem da necessidade (aplicação, veículo, ano, quantidade, urgência),
oferta de itens complementares/venda casada, argumentação de valor (qualidade, marca,
disponibilidade, prazo) em vez de só preço e contorno de objeções.
3. fechamento: tentou fechar pedido? confirmou itens, quantidades, preço, condição de pagamento
e entrega? Se não fechou, combinou próximo passo concreto, data de retorno ou envio de orçamento?
4. conhecimento_tecnico: domínio de peças de linha pesada, aplicação, códigos/equivalências,
marcas e explicação técnica clara. Use null se não houve assunto técnico.

Use null em qualquer critério que realmente não se aplique.
Justificativas curtas e concretas. Pontos fortes e pontos a melhorar: 2 a 4 itens cada.
Momentos-chave: até 5 trechos LITERAIS da transcrição com comentário.

Além da avaliação, extraia dados úteis para o CRM sem inventar:
comprador, função, o que compra, marcas/frota e observações comerciais.
Sugira um próximo passo concreto. Se não houver base suficiente, use strings vazias e tipo "nenhum".
Escreva tudo em português do Brasil, linguagem direta de gestor para vendedor."""

EVAL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "dialogo": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "falante": {"type": "string", "enum": ["Vendedor", "Cliente", "Outro"]},
                    "fala": {"type": "string"},
                },
                "required": ["falante", "fala"],
            },
        },
        "tipo_ligacao": {"type": "string", "enum": ["ativa", "receptiva", "indefinida"]},
        "resultado": {"type": "string", "enum": [
            "pedido_fechado", "orcamento_enviado", "retorno_agendado",
            "sem_venda", "pos_venda", "indefinido"
        ]},
        "cliente_mencionado": {"type": "string"},
        "produtos_citados": {"type": "array", "items": {"type": "string"}},
        "resumo": {"type": "string"},
        "criterios": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                k: {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "nota": {"type": ["number", "null"], "minimum": 0, "maximum": 10},
                        "justificativa": {"type": "string"},
                    },
                    "required": ["nota", "justificativa"],
                } for k in WEIGHTS
            },
            "required": list(WEIGHTS),
        },
        "pontos_fortes": {"type": "array", "items": {"type": "string"}},
        "pontos_melhorar": {"type": "array", "items": {"type": "string"}},
        "momentos_chave": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "trecho": {"type": "string"},
                    "comentario": {"type": "string"},
                    "tipo": {"type": "string", "enum": ["positivo", "negativo"]},
                },
                "required": ["trecho", "comentario", "tipo"],
            },
        },
        "oportunidade_perdida": {"type": "string"},
        "sentimento_cliente": {"type": "string", "enum": ["positivo", "neutro", "negativo"]},
        "dica_principal": {"type": "string"},
        "proxima_acao": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "tipo": {"type": "string", "enum": ["ligar", "whatsapp", "cotar", "aguardar", "nenhum"]},
                "prazo_dias": {"type": ["integer", "null"], "minimum": 0, "maximum": 90},
                "motivo": {"type": "string"},
            },
            "required": ["tipo", "prazo_dias", "motivo"],
        },
        "crm": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "comprador": {"type": "string"},
                "funcao": {"type": "string"},
                "o_que_compra": {"type": "string"},
                "marcas_frota": {"type": "string"},
                "observacoes": {"type": "string"},
            },
            "required": ["comprador", "funcao", "o_que_compra", "marcas_frota", "observacoes"],
        },
    },
    "required": [
        "dialogo", "tipo_ligacao", "resultado", "cliente_mencionado", "produtos_citados",
        "resumo", "criterios", "pontos_fortes", "pontos_melhorar", "momentos_chave",
        "oportunidade_perdida", "sentimento_cliente", "dica_principal", "proxima_acao", "crm"
    ],
}


def _safe_name(value: str) -> str:
    s = "".join(ch if ch.isalnum() or ch in " -_." else "_" for ch in str(value or "").strip())
    return (s[:80] or "Contato").strip()


def _json_atomic(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _score_general(evaluation: dict) -> float | None:
    criterios = evaluation.get("criterios") if isinstance(evaluation, dict) else {}
    if not isinstance(criterios, dict):
        return None
    total = 0.0
    weight = 0.0
    for key, w in WEIGHTS.items():
        row = criterios.get(key) if isinstance(criterios.get(key), dict) else {}
        value = row.get("nota")
        if isinstance(value, (int, float)):
            total += float(value) * w
            weight += w
    if weight <= 0:
        return None
    return round(max(0.0, min(10.0, total / weight)), 1)


def _wav_mono_16k(path: Path) -> bytes:
    import audioop
    with wave.open(str(path), "rb") as w:
        channels = int(w.getnchannels())
        width = int(w.getsampwidth())
        rate = int(w.getframerate())
        data = w.readframes(w.getnframes())
    if width != 2:
        data = audioop.lin2lin(data, width, 2)
        width = 2
    if channels == 2:
        data = audioop.tomono(data, 2, 0.5, 0.5)
    elif channels > 2:
        # WASAPI comum é estéreo; se vier multicanal, usa os dois primeiros canais.
        frame = channels * 2
        out = bytearray()
        for i in range(0, len(data) - frame + 1, frame):
            a = int.from_bytes(data[i:i+2], "little", signed=True)
            b = int.from_bytes(data[i+2:i+4], "little", signed=True)
            m = max(-32768, min(32767, int((a + b) / 2)))
            out += int(m).to_bytes(2, "little", signed=True)
        data = bytes(out)
    if rate != 16000:
        data, _ = audioop.ratecv(data, 2, 1, rate, 16000, None)
    return data


def mix_wavs(loopback: Path | None, mic: Path | None, target: Path) -> Path:
    import audioop
    a = _wav_mono_16k(loopback) if loopback and loopback.exists() else b""
    b = _wav_mono_16k(mic) if mic and mic.exists() else b""
    if not a and not b:
        raise RuntimeError("Nenhum áudio foi capturado.")
    if not a:
        mixed = b
    elif not b:
        mixed = a
    else:
        n = max(len(a), len(b))
        a = a + (b"\x00" * (n - len(a)))
        b = b + (b"\x00" * (n - len(b)))
        a = audioop.mul(a, 2, 0.78)
        b = audioop.mul(b, 2, 0.78)
        mixed = audioop.add(a, b, 2)
    target.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(mixed)
    return target


class DualAudioRecorder:
    def __init__(self, folder: Path):
        self.folder = folder
        self.p = None
        self.streams = []
        self.files = []
        self.loop_path = folder / "sistema.wav"
        self.mic_path = folder / "microfone.wav"
        self.device_info = {}

    def start(self):
        self.folder.mkdir(parents=True, exist_ok=True)
        try:
            import pyaudiowpatch as pyaudio
        except Exception as exc:
            raise RuntimeError("Componente de gravação não disponível: " + str(exc))

        self.p = pyaudio.PyAudio()
        errors = []

        try:
            sp = self.p.get_default_wasapi_loopback()
            channels = max(1, min(2, int(sp.get("maxInputChannels") or 2)))
            rate = int(float(sp.get("defaultSampleRate") or 48000))
            wf = wave.open(str(self.loop_path), "wb")
            wf.setnchannels(channels); wf.setsampwidth(2); wf.setframerate(rate)
            def speaker_cb(in_data, frame_count, time_info, status):
                try: wf.writeframes(in_data)
                except Exception: pass
                return (in_data, pyaudio.paContinue)
            st = self.p.open(
                format=pyaudio.paInt16, channels=channels, rate=rate, input=True,
                input_device_index=int(sp["index"]), frames_per_buffer=1024,
                stream_callback=speaker_cb
            )
            self.files.append(wf); self.streams.append(st)
            self.device_info["speaker"] = str(sp.get("name") or "")
        except Exception as exc:
            errors.append("sistema: " + str(exc))

        try:
            mic = self.p.get_default_input_device_info()
            channels = 1
            rate = int(float(mic.get("defaultSampleRate") or 48000))
            wf = wave.open(str(self.mic_path), "wb")
            wf.setnchannels(channels); wf.setsampwidth(2); wf.setframerate(rate)
            def mic_cb(in_data, frame_count, time_info, status):
                try: wf.writeframes(in_data)
                except Exception: pass
                return (in_data, pyaudio.paContinue)
            try:
                st = self.p.open(
                    format=pyaudio.paInt16, channels=channels, rate=rate, input=True,
                    input_device_index=int(mic["index"]), frames_per_buffer=1024,
                    stream_callback=mic_cb
                )
            except Exception:
                channels = max(1, min(2, int(mic.get("maxInputChannels") or 1)))
                wf.close()
                wf = wave.open(str(self.mic_path), "wb")
                wf.setnchannels(channels); wf.setsampwidth(2); wf.setframerate(rate)
                st = self.p.open(
                    format=pyaudio.paInt16, channels=channels, rate=rate, input=True,
                    input_device_index=int(mic["index"]), frames_per_buffer=1024,
                    stream_callback=mic_cb
                )
            self.files.append(wf); self.streams.append(st)
            self.device_info["microphone"] = str(mic.get("name") or "")
        except Exception as exc:
            errors.append("microfone: " + str(exc))

        if not self.streams:
            self.stop()
            raise RuntimeError("Não consegui capturar áudio. " + " | ".join(errors))
        return {"devices": self.device_info, "warnings": errors}

    def stop(self):
        for st in list(self.streams):
            try:
                if st.is_active(): st.stop_stream()
            except Exception: pass
            try: st.close()
            except Exception: pass
        self.streams = []
        for f in list(self.files):
            try: f.close()
            except Exception: pass
        self.files = []
        try:
            if self.p is not None: self.p.terminate()
        except Exception: pass
        self.p = None
        return {
            "loopback": str(self.loop_path) if self.loop_path.exists() and self.loop_path.stat().st_size > 44 else "",
            "microphone": str(self.mic_path) if self.mic_path.exists() and self.mic_path.stat().st_size > 44 else "",
            "devices": self.device_info,
        }


def _multipart_transcription(path: Path, key: str, prompt: str) -> str:
    boundary = "----ALIYVO" + uuid.uuid4().hex
    crlf = b"\r\n"
    parts = []
    def field(name, value):
        parts.extend([
            ("--" + boundary).encode(), crlf,
            f'Content-Disposition: form-data; name="{name}"'.encode(), crlf, crlf,
            str(value).encode("utf-8"), crlf
        ])
    field("model", "gpt-4o-transcribe")
    field("language", "pt")
    field("response_format", "json")
    field("prompt", prompt)
    parts.extend([
        ("--" + boundary).encode(), crlf,
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"'.encode(), crlf,
        b"Content-Type: audio/wav", crlf, crlf,
        path.read_bytes(), crlf,
        ("--" + boundary + "--").encode(), crlf
    ])
    body = b"".join(parts)
    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/transcriptions",
        data=body,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "multipart/form-data; boundary=" + boundary,
            "User-Agent": "ALIYVO-call-ai",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read().decode("utf-8", "replace"))
    return str(data.get("text") or "").strip()


def _split_wav(path: Path, minutes: int = 8) -> list[Path]:
    out = []
    with wave.open(str(path), "rb") as src:
        rate = src.getframerate(); channels = src.getnchannels(); width = src.getsampwidth()
        frames_per = int(rate * 60 * minutes)
        idx = 0
        while True:
            data = src.readframes(frames_per)
            if not data: break
            part = path.parent / f"_parte_{idx:02d}.wav"
            with wave.open(str(part), "wb") as w:
                w.setnchannels(channels); w.setsampwidth(width); w.setframerate(rate); w.writeframes(data)
            out.append(part); idx += 1
    return out


def _extract_response_text(data: dict) -> str:
    direct = str(data.get("output_text") or "").strip()
    if direct: return direct
    parts = []
    for item in data.get("output") or []:
        if not isinstance(item, dict): continue
        for c in item.get("content") or []:
            if isinstance(c, dict) and c.get("type") in ("output_text", "text"):
                t = str(c.get("text") or "").strip()
                if t: parts.append(t)
    return "\n".join(parts).strip()


def _post_json(url: str, key: str, payload: dict, timeout: int = 300) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": "ALIYVO-call-ai"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def evaluate_transcript(transcript: str, client: str, key: str, preferred_model: str = "") -> dict:
    user_input = (
        f"Cliente conhecido pelo ALIYVO: {client or '-'}\n"
        "Observação: ligação capturada automaticamente no WhatsApp pelo ALIYVO.\n\n"
        "TRANSCRIÇÃO:\n" + transcript
    )
    models = ["gpt-4.1"]
    if preferred_model and preferred_model not in models:
        models.append(preferred_model)
    last_error = None

    for model in models:
        payload = {
            "model": model,
            "store": False,
            "instructions": SYSTEM_PROMPT,
            "input": user_input,
            "max_output_tokens": 4000,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "avaliacao_ligacao",
                    "strict": True,
                    "schema": EVAL_SCHEMA,
                }
            },
        }
        try:
            data = _post_json("https://api.openai.com/v1/responses", key, payload, 300)
            raw = _extract_response_text(data)
            result = json.loads(raw)
            if isinstance(result, dict):
                return result
        except Exception as exc:
            last_error = exc

    # Fallback sem Structured Output, mantendo a mesma régua.
    fallback_model = preferred_model or "gpt-4.1"
    prompt = SYSTEM_PROMPT + "\n\nResponda SOMENTE um JSON válido obedecendo exatamente este schema:\n" + json.dumps(EVAL_SCHEMA, ensure_ascii=False)
    payload = {
        "model": fallback_model,
        "store": False,
        "instructions": prompt,
        "input": user_input,
        "max_output_tokens": 4000,
    }
    try:
        data = _post_json("https://api.openai.com/v1/responses", key, payload, 300)
        raw = _extract_response_text(data).strip()
        if raw.startswith("```"):
            raw = raw.strip("`").replace("json\n", "", 1)
        a = raw.find("{"); b = raw.rfind("}")
        if a >= 0 and b > a: raw = raw[a:b+1]
        result = json.loads(raw)
        if isinstance(result, dict): return result
    except Exception as exc:
        last_error = exc
    raise RuntimeError("Falha na avaliação da IA: " + str(last_error or "resposta inválida"))


class AliyvoCallAIManager(QObject):
    updated = pyqtSignal(str)

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._active = None
        self._dashboard = None
        self._list = None
        self._detail = None
        self._filter = None
        self.updated.connect(self._on_updated)
        self._cfg = self._load_cfg()
        self._poll_busy = False
        self._poll_missing = 0
        self._call_poll_timer = QTimer(self)
        self._call_poll_timer.setInterval(1000)
        self._call_poll_timer.timeout.connect(self._poll_call_ui)
        self._call_poll_timer.start()

    def _poll_call_ui(self):
        """Detector leve (1 s) para iniciar a gravação sem esperar o diagnóstico de 20 s."""
        if self._poll_busy:
            return
        try:
            web = getattr(self.owner, "web", None)
            if web is None:
                return
            self._poll_busy = True
            js = r"""
            (() => {
              try{
                const clean=t=>String(t||'').replace(/\s+/g,' ').trim();
                const vis=e=>{try{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&r.bottom>0&&r.right>0&&s.display!=='none'&&s.visibility!=='hidden';}catch(_){return false;}};
                const meta=e=>clean((e.getAttribute&&e.getAttribute('aria-label')||'')+' '+(e.getAttribute&&e.getAttribute('data-testid')||'')+' '+(e.getAttribute&&e.getAttribute('data-icon')||'')+' '+(e.getAttribute&&e.getAttribute('title')||''));
                const controls=Array.from(document.querySelectorAll('[aria-label],[data-testid],[data-icon],button'));
                const hang=controls.find(e=>vis(e)&&/(encerrar\s*(?:a\s*)?(?:liga[cç][aã]o|chamada)|desligar|finalizar\s*(?:liga[cç][aã]o|chamada)|end[-_ ]?call|call[-_ ]?end|hang[-_ ]?up)/i.test(meta(e)));
                if(!hang)return {active:false};
                let box=hang,best=hang.parentElement||hang;
                for(let i=0;i<10&&box&&box.parentElement;i++){
                  box=box.parentElement;if(!vis(box))continue;
                  const r=box.getBoundingClientRect(),t=String(box.innerText||box.textContent||'');
                  if(r.width>=220&&r.width<=900&&r.height>=70&&r.height<=760&&/\b\d{1,3}:\d{2}(?::\d{2})?\b/.test(t))best=box;
                }
                const raw=String(best.innerText||best.textContent||'');
                const lines=raw.split(/\n+/).map(clean).filter(Boolean);
                let duration=0;
                for(const ln of lines){
                  let m=ln.match(/^\s*(\d{1,2}):(\d{2}):(\d{2})\s*$/);
                  if(m){duration=parseInt(m[1])*3600+parseInt(m[2])*60+parseInt(m[3]);break;}
                  m=ln.match(/^\s*(\d{1,3}):(\d{2})\s*$/);
                  if(m){duration=parseInt(m[1])*60+parseInt(m[2]);break;}
                }
                let cname='';
                const titled=Array.from(best.querySelectorAll('span[title],[title]')).filter(vis);
                for(const e of titled){
                  const v=clean(e.getAttribute('title')||e.textContent||'');
                  if(v&&v.length>=2&&!/^\d{1,3}:\d{2}(?::\d{2})?$/.test(v)&&!/(encerrar|desligar|microfone|c[aâ]mera|camera|liga[cç][aã]o|chamada|call)/i.test(v)){cname=v;break;}
                }
                const allMeta=controls.filter(e=>vis(e)&&best.contains(e)).map(meta).join(' ');
                const callType=/(chamada de v[ií]deo|video call)/i.test(raw+' '+allMeta)?'video':'voice';
                return {active:true,client:cname,duration_seconds:Math.max(0,duration||0),call_type:callType};
              }catch(e){return {active:false,error:String(e)};}
            })();
            """
            web.page().runJavaScript(js, self._poll_call_done)
        except Exception:
            self._poll_busy = False

    def _poll_call_done(self, result):
        self._poll_busy = False
        now = time.time()
        live = result if isinstance(result, dict) else {}
        if bool(live.get("active")):
            self._poll_missing = 0
            client = str(live.get("client") or getattr(self.owner, "_diagnostic_active_name", "") or "Contato").strip() or "Contato"
            duration = max(0, int(live.get("duration_seconds") or 0))
            if self._active is None:
                self.on_call_started({
                    "client": client,
                    "start_ts": now - duration if duration > 0 else now,
                    "duration_seconds": duration,
                    "call_type": str(live.get("call_type") or "voice"),
                    "session_id": f"fast|{client}|{int(now-duration if duration>0 else now)}",
                })
            return
        if self._active is not None:
            self._poll_missing += 1
            if self._poll_missing >= 2:
                call = self._find(self._active.get("id"))
                started = float(call.get("started_ts") or now)
                self._poll_missing = 0
                self.on_call_finished({
                    "client": call.get("client") or "Contato",
                    "started_ts": started,
                    "ended_ts": now,
                    "duration_seconds": max(0, int(now-started)),
                    "session_id": call.get("session_id") or "",
                    "call_type": call.get("call_type") or "voice",
                    "end_reason": "fast_overlay_gone",
                })

    def _load_cfg(self):
        cfg = {"auto_record": True, "auto_crm": True, "auto_followup": True, "keep_sources": False}
        try:
            if CFG_FILE.exists():
                x = json.loads(CFG_FILE.read_text(encoding="utf-8"))
                if isinstance(x, dict): cfg.update(x)
        except Exception: pass
        return cfg

    def _save_cfg(self):
        try: _json_atomic(CFG_FILE, self._cfg)
        except Exception: pass

    def _load(self):
        with self._lock:
            data = {"version": 1, "calls": []}
            try:
                if DB_FILE.exists():
                    x = json.loads(DB_FILE.read_text(encoding="utf-8"))
                    if isinstance(x, dict):
                        data.update(x)
                        if not isinstance(data.get("calls"), list): data["calls"] = []
            except Exception: pass
            return data

    def _save(self, data):
        with self._lock:
            _json_atomic(DB_FILE, data)

    def _update_call(self, call_id, **changes):
        data = self._load()
        found = None
        for row in data["calls"]:
            if str(row.get("id")) == str(call_id):
                row.update(changes); found = row; break
        if found is not None: self._save(data)
        return found

    def _find(self, call_id):
        for row in self._load().get("calls", []):
            if str(row.get("id")) == str(call_id): return dict(row)
        return {}

    def on_call_started(self, call: dict):
        if not self._cfg.get("auto_record", True): return
        if self._active is not None: return
        client = str((call or {}).get("client") or "Contato").strip() or "Contato"
        session = str((call or {}).get("session_id") or uuid.uuid4().hex)
        started = float((call or {}).get("start_ts") or time.time())
        call_id = uuid.uuid4().hex
        folder = AUDIO_DIR / datetime.fromtimestamp(started).strftime("%Y%m") / (datetime.fromtimestamp(started).strftime("%Y%m%d_%H%M%S") + "_" + call_id[:8])
        rec = DualAudioRecorder(folder)
        row = {
            "id": call_id, "session_id": session, "client": client, "started_ts": started,
            "started_at": datetime.fromtimestamp(started).isoformat(timespec="seconds"),
            "ended_ts": None, "duration_seconds": 0, "call_type": str((call or {}).get("call_type") or "voice"),
            "status": "iniciando_gravacao", "score": None, "created_ts": time.time(),
        }
        data = self._load(); data["calls"].append(row); self._save(data)
        try:
            info = rec.start()
            row = self._update_call(call_id, status="gravando", capture=info) or row
            self._active = {"id": call_id, "session": session, "recorder": rec, "client": client}
            try: self.owner._diagnostic_log("call_ai_recording_started", client=client, call_ai_id=call_id, devices=info.get("devices"))
            except Exception: pass
        except Exception as exc:
            try: rec.stop()
            except Exception: pass
            self._update_call(call_id, status="erro_gravacao", error=str(exc)[:800])
            try: self.owner._diagnostic_log("call_ai_recording_error", client=client, error=str(exc)[:400])
            except Exception: pass
            self.updated.emit(call_id)

    def on_call_finished(self, call: dict):
        active = self._active
        if not isinstance(active, dict): return
        self._active = None
        call_id = active["id"]; rec = active["recorder"]
        ended = float((call or {}).get("ended_ts") or time.time())
        started = float((call or {}).get("started_ts") or self._find(call_id).get("started_ts") or ended)
        duration = max(0, int((call or {}).get("duration_seconds") or (ended - started)))
        try:
            paths = rec.stop()
            self._update_call(
                call_id, ended_ts=ended, ended_at=datetime.fromtimestamp(ended).isoformat(timespec="seconds"),
                duration_seconds=duration, status="gravacao_concluida", sources=paths
            )
        except Exception as exc:
            self._update_call(call_id, ended_ts=ended, duration_seconds=duration, status="erro_gravacao", error=str(exc)[:800])
            self.updated.emit(call_id); return

        if duration < 8:
            self._update_call(call_id, status="ligacao_curta", error="Ligação muito curta para avaliação automática.")
            self.updated.emit(call_id); return

        try:
            key = str(self.owner._ai_api_key() or "").strip()
        except Exception:
            key = ""
        try:
            cfg = self.owner._ai_config_load() or {}
            model = str(cfg.get("model") or "")
        except Exception:
            model = ""

        th = threading.Thread(target=self._process_call, args=(call_id, key, model), name="ALIYVO-CallAI-" + call_id[:6], daemon=True)
        th.start()

    def _process_call(self, call_id: str, key: str, model: str):
        call = self._find(call_id)
        try:
            self._update_call(call_id, status="preparando_audio")
            src = call.get("sources") if isinstance(call.get("sources"), dict) else {}
            loop = Path(src.get("loopback")) if src.get("loopback") else None
            mic = Path(src.get("microphone")) if src.get("microphone") else None
            folder = Path(loop or mic).parent if (loop or mic) else None
            if folder is None: raise RuntimeError("Arquivos de áudio não encontrados.")
            mixed = folder / "ligacao.wav"
            mix_wavs(loop, mic, mixed)
            self._update_call(call_id, mixed_audio=str(mixed), status="audio_pronto")

            if not self._cfg.get("keep_sources", False):
                for p in (loop, mic):
                    try:
                        if p and p.exists(): p.unlink()
                    except Exception: pass

            if not key:
                self._update_call(call_id, status="aguardando_chave_ia", error="Configure a chave da API na IA Observadora e clique Reprocessar.")
                self.updated.emit(call_id); return

            self._update_call(call_id, status="transcrevendo", error="")
            parts = _split_wav(mixed, 8)
            texts = []
            try:
                for i, part in enumerate(parts, 1):
                    self._update_call(call_id, status=f"transcrevendo_{i}_{len(parts)}")
                    txt = _multipart_transcription(part, key, VOCABULARY)
                    if txt: texts.append(txt)
            finally:
                for part in parts:
                    try: part.unlink()
                    except Exception: pass
            transcript = "\n".join(texts).strip()
            if not transcript:
                raise RuntimeError("A transcrição voltou vazia. Confira o áudio gravado.")
            self._update_call(call_id, transcript=transcript, status="avaliando")

            evaluation = evaluate_transcript(transcript, str(call.get("client") or ""), key, model)
            score = _score_general(evaluation)
            self._update_call(call_id, evaluation=evaluation, score=score, status="concluido", processed_ts=time.time(), error="")
            try: self.owner._diagnostic_log("call_ai_completed", client=call.get("client"), call_ai_id=call_id, score=score, result=evaluation.get("resultado"))
            except Exception: pass
        except urllib.error.HTTPError as exc:
            try: detail = exc.read().decode("utf-8", "replace")[:1200]
            except Exception: detail = str(exc)
            self._update_call(call_id, status="erro", error=f"OpenAI HTTP {getattr(exc,'code','?')}: {detail}")
        except Exception as exc:
            self._update_call(call_id, status="erro", error=str(exc)[:1200])
        self.updated.emit(call_id)

    def reprocess(self, call_id: str):
        call = self._find(call_id)
        audio = str(call.get("mixed_audio") or "")
        if not audio or not Path(audio).exists():
            QMessageBox.warning(self.owner, "Ligações IA", "O áudio desta ligação não está disponível.")
            return
        try: key = str(self.owner._ai_api_key() or "").strip()
        except Exception: key = ""
        if not key:
            QMessageBox.information(self.owner, "Ligações IA", "Configure primeiro a chave da API na IA Observadora.")
            try: self.owner._ai_settings_dialog(self.owner)
            except Exception: pass
            return
        try:
            model = str((self.owner._ai_config_load() or {}).get("model") or "")
        except Exception: model = ""
        self._update_call(call_id, status="reprocessando", error="")
        threading.Thread(target=self._process_existing_audio, args=(call_id,key,model), daemon=True).start()

    def _process_existing_audio(self, call_id, key, model):
        call = self._find(call_id)
        mixed = Path(str(call.get("mixed_audio") or ""))
        try:
            transcript = str(call.get("transcript") or "").strip()
            if not transcript:
                parts = _split_wav(mixed, 8); texts=[]
                try:
                    for part in parts:
                        txt=_multipart_transcription(part,key,VOCABULARY)
                        if txt:texts.append(txt)
                finally:
                    for part in parts:
                        try:part.unlink()
                        except Exception:pass
                transcript="\n".join(texts).strip()
                if not transcript:raise RuntimeError("Transcrição vazia.")
                self._update_call(call_id, transcript=transcript)
            self._update_call(call_id,status="avaliando")
            ev=evaluate_transcript(transcript,str(call.get("client") or ""),key,model)
            self._update_call(call_id,evaluation=ev,score=_score_general(ev),status="concluido",processed_ts=time.time(),error="")
        except Exception as exc:
            self._update_call(call_id,status="erro",error=str(exc)[:1200])
        self.updated.emit(call_id)

    def _on_updated(self, call_id):
        call = self._find(call_id)
        if call.get("status") == "concluido" and self._cfg.get("auto_crm", True) and not call.get("crm_applied"):
            self._apply_crm(call_id)
        self._refresh_dashboard()

    def _apply_crm(self, call_id):
        call=self._find(call_id); ev=call.get("evaluation") if isinstance(call.get("evaluation"),dict) else {}
        client=str(call.get("client") or ev.get("cliente_mencionado") or "").strip()
        if not client:return
        try: profile=self.owner._crm_client_profile(client) or {"name":client}
        except Exception: profile={"name":client}
        crm=ev.get("crm") if isinstance(ev.get("crm"),dict) else {}
        mapping={"comprador":"buyer","funcao":"buyer_role","o_que_compra":"buys","marcas_frota":"brands"}
        for src,dst in mapping.items():
            value=str(crm.get(src) or "").strip()
            if value and not str(profile.get(dst) or "").strip():profile[dst]=value
        obs=str(crm.get("observacoes") or "").strip()
        if obs:
            old=str(profile.get("notes") or "").strip()
            if obs.lower() not in old.lower():profile["notes"]=(old+"\nIA ligação: "+obs).strip()
        hist=profile.get("history") if isinstance(profile.get("history"),list) else []
        score=call.get("score"); summary=str(ev.get("resumo") or "").strip()
        products=", ".join(str(x) for x in (ev.get("produtos_citados") or [])[:10] if x)
        note=(f"Nota IA: {score if score is not None else '-'} • {summary}"+(f" • Produtos: {products}" if products else "")).strip()
        hist.append({"ts":float(call.get("ended_ts") or time.time()),"type":"Ligação avaliada pela IA","note":note})
        profile["history"]=hist[-200:]; profile["last_contact_ts"]=float(call.get("ended_ts") or time.time()); profile["last_summary"]=summary or note
        try:self.owner._crm_save_profile(profile,client)
        except Exception:return
        follow_created=False
        action=ev.get("proxima_acao") if isinstance(ev.get("proxima_acao"),dict) else {}
        if self._cfg.get("auto_followup",True) and not call.get("followup_created"):
            kind=str(action.get("tipo") or "nenhum")
            days=action.get("prazo_dias")
            reason=str(action.get("motivo") or "").strip()
            if kind!="nenhum" and isinstance(days,int):
                try:
                    self.owner._crm_schedule_followup(client,days,reason or f"{kind.title()} após ligação")
                    follow_created=True
                except Exception:pass
        self._update_call(call_id,crm_applied=True,followup_created=bool(call.get("followup_created") or follow_created))

    def shutdown(self):
        try:self._call_poll_timer.stop()
        except Exception:pass
        active=self._active;self._active=None
        if isinstance(active,dict):
            try:active["recorder"].stop()
            except Exception:pass

    def _filtered_calls(self):
        rows=list(reversed(self._load().get("calls",[])))
        mode=self._filter.currentText() if self._filter is not None else "Últimos 30 dias"
        if mode=="Todos":return rows
        now=time.time()
        if mode=="Com erro":return [x for x in rows if str(x.get("status") or "").startswith("erro") or x.get("status")=="aguardando_chave_ia"]
        return [x for x in rows if now-float(x.get("started_ts") or now)<=30*86400]

    def show_dashboard(self):
        if self._dashboard is not None and self._dashboard.isVisible():
            self._dashboard.raise_(); self._dashboard.activateWindow(); return
        dlg=QDialog(self.owner); self._dashboard=dlg
        dlg.setWindowTitle("📞 ALIYVO — Análise de Ligações");dlg.resize(1080,740)
        dlg.setStyleSheet("QDialog{background:#F4F5F7;} QPushButton{padding:7px 10px;} QListWidget{background:white;} QTextEdit{background:white;}")
        lay=QVBoxLayout(dlg)
        title=QLabel("ANÁLISE DE LIGAÇÕES");title.setStyleSheet("font-size:20px;font-weight:900;color:#0B3349;");lay.addWidget(title)
        sub=QLabel("Gravação automática das ligações detectadas no WhatsApp → transcrição → avaliação IA → CRM → follow-up.")
        sub.setWordWrap(True);sub.setStyleSheet("color:#5B6872;font-weight:600;");lay.addWidget(sub)

        opts=QHBoxLayout()
        auto=QCheckBox("Gravar automaticamente");auto.setChecked(bool(self._cfg.get("auto_record",True)))
        auto_crm=QCheckBox("Salvar resultado no CRM");auto_crm.setChecked(bool(self._cfg.get("auto_crm",True)))
        auto_fu=QCheckBox("Criar follow-up sugerido");auto_fu.setChecked(bool(self._cfg.get("auto_followup",True)))
        self._filter=QComboBox();self._filter.addItems(["Últimos 30 dias","Todos","Com erro"])
        opts.addWidget(auto);opts.addWidget(auto_crm);opts.addWidget(auto_fu);opts.addStretch(1);opts.addWidget(self._filter);lay.addLayout(opts)
        def save_opts():
            self._cfg["auto_record"]=auto.isChecked();self._cfg["auto_crm"]=auto_crm.isChecked();self._cfg["auto_followup"]=auto_fu.isChecked();self._save_cfg()
        auto.toggled.connect(save_opts);auto_crm.toggled.connect(save_opts);auto_fu.toggled.connect(save_opts)

        self._summary=QLabel("");self._summary.setStyleSheet("background:white;border:1px solid #D7DDE3;border-radius:8px;padding:10px;font-size:12px;font-weight:800;color:#173B52;");lay.addWidget(self._summary)

        split=QSplitter(Qt.Orientation.Horizontal);self._list=QListWidget();self._detail=QTextEdit();self._detail.setReadOnly(True)
        split.addWidget(self._list);split.addWidget(self._detail);split.setSizes([420,650]);lay.addWidget(split,1)

        bar=QHBoxLayout();openb=QPushButton("🔎 Abrir detalhe");play=QPushButton("▶ Ouvir");retry=QPushButton("↻ Reprocessar IA");settings=QPushButton("⚙ Configurar IA");refresh=QPushButton("Atualizar");close=QPushButton("Fechar")
        for b in (openb,play,retry,settings,refresh):bar.addWidget(b)
        bar.addStretch(1);bar.addWidget(close);lay.addLayout(bar)

        def selected_id():
            it=self._list.currentItem();return str(it.data(Qt.ItemDataRole.UserRole) or "") if it else ""
        self._list.currentItemChanged.connect(lambda _a,_b:self._show_selected_text())
        self._list.itemDoubleClicked.connect(lambda _it:self.show_detail(selected_id()))
        openb.clicked.connect(lambda:self.show_detail(selected_id()))
        play.clicked.connect(lambda:self.play_audio(selected_id()))
        retry.clicked.connect(lambda:self.reprocess(selected_id()))
        settings.clicked.connect(lambda:self._open_ai_settings(dlg))
        refresh.clicked.connect(self._refresh_dashboard);self._filter.currentIndexChanged.connect(lambda _=None:self._refresh_dashboard())
        close.clicked.connect(dlg.accept)
        dlg.finished.connect(lambda _=0:setattr(self,"_dashboard",None))
        self._refresh_dashboard();dlg.exec()

    def _open_ai_settings(self,parent):
        try:self.owner._ai_settings_dialog(parent)
        except Exception as exc:QMessageBox.information(parent,"IA","Abra a IA Observadora para configurar a chave.\n"+str(exc))

    def _refresh_dashboard(self):
        if self._dashboard is None or not self._dashboard.isVisible() or self._list is None:return
        rows=self._filtered_calls();self._list.clear()
        done=[x for x in rows if x.get("status")=="concluido" and isinstance(x.get("score"),(int,float))]
        avg=round(sum(float(x["score"]) for x in done)/len(done),1) if done else None
        closed=sum(1 for x in done if isinstance(x.get("evaluation"),dict) and x["evaluation"].get("resultado")=="pedido_fechado")
        errs=sum(1 for x in rows if str(x.get("status") or "").startswith("erro") or x.get("status")=="aguardando_chave_ia")
        self._summary.setText(f"Ligações: {len(rows)}   •   Avaliadas: {len(done)}   •   Nota média: {avg if avg is not None else '-'}   •   Pedidos fechados: {closed}   •   Pendências/erros: {errs}")
        for row in rows:
            score=row.get("score");status=str(row.get("status") or "")
            icon="✅" if status=="concluido" else "🔴" if status.startswith("erro") else "⏳" if status not in ("ligacao_curta","aguardando_chave_ia") else "⚠"
            when=str(row.get("started_at") or "")[:16].replace("T"," ")
            txt=f"{icon} {when}  •  {row.get('client') or 'Contato'}\n{status}"+(f"  •  nota {score}" if score is not None else "")
            it=QListWidgetItem(txt);it.setData(Qt.ItemDataRole.UserRole,str(row.get("id") or ""));self._list.addItem(it)
        if self._list.count():self._list.setCurrentRow(0)
        else:self._detail.setPlainText("Ainda não há ligações gravadas.")

    def _show_selected_text(self):
        if self._list is None or self._detail is None:return
        it=self._list.currentItem()
        if not it:return
        call=self._find(str(it.data(Qt.ItemDataRole.UserRole) or ""))
        self._detail.setPlainText(self._call_text(call,compact=True))

    def _call_text(self,call,compact=False):
        ev=call.get("evaluation") if isinstance(call.get("evaluation"),dict) else {}
        lines=[
            f"{call.get('client') or 'Contato'}",
            f"Data: {str(call.get('started_at') or '-').replace('T',' ')}",
            f"Duração: {int(call.get('duration_seconds') or 0)//60}m {int(call.get('duration_seconds') or 0)%60:02d}s",
            f"Status: {call.get('status') or '-'}",
            f"Nota geral: {call.get('score') if call.get('score') is not None else '-'}",
        ]
        if call.get("error"):lines += ["", "ERRO/PENDÊNCIA", str(call.get("error"))]
        if ev:
            lines += ["","RESUMO",str(ev.get("resumo") or "-"),"","CRITÉRIOS"]
            for key,label in (("abordagem","Abordagem e cordialidade"),("tecnica_venda","Técnica de venda"),("fechamento","Fechamento"),("conhecimento_tecnico","Conhecimento técnico")):
                row=(ev.get("criterios") or {}).get(key) if isinstance(ev.get("criterios"),dict) else {}
                row=row if isinstance(row,dict) else {}
                lines.append(f"{label}: {row.get('nota') if row.get('nota') is not None else '—'} — {row.get('justificativa') or ''}")
            lines += ["","MANDOU BEM"]+[f"• {x}" for x in ev.get("pontos_fortes") or []]
            lines += ["","PARA MELHORAR"]+[f"• {x}" for x in ev.get("pontos_melhorar") or []]
            if ev.get("dica_principal"):lines += ["","DICA PRINCIPAL",str(ev.get("dica_principal"))]
            if ev.get("oportunidade_perdida"):lines += ["","OPORTUNIDADE PERDIDA",str(ev.get("oportunidade_perdida"))]
            action=ev.get("proxima_acao") if isinstance(ev.get("proxima_acao"),dict) else {}
            lines += ["","PRÓXIMO PASSO",f"{action.get('tipo') or 'nenhum'} • prazo: {action.get('prazo_dias')} dia(s) • {action.get('motivo') or ''}"]
            if not compact:
                lines += ["","MOMENTOS-CHAVE"]
                for x in ev.get("momentos_chave") or []:
                    if isinstance(x,dict):lines.append(f"• {x.get('trecho') or ''}\n  {x.get('comentario') or ''}")
        if not compact and call.get("transcript"):lines += ["","TRANSCRIÇÃO",str(call.get("transcript"))]
        return "\n".join(lines)

    def show_detail(self,call_id):
        call=self._find(call_id)
        if not call:return
        dlg=QDialog(self.owner);dlg.setWindowTitle("📞 Ligação — "+str(call.get("client") or "Contato"));dlg.resize(900,760);lay=QVBoxLayout(dlg)
        txt=QTextEdit();txt.setReadOnly(True);txt.setPlainText(self._call_text(call,compact=False));lay.addWidget(txt,1)
        bar=QHBoxLayout();play=QPushButton("▶ Ouvir áudio");retry=QPushButton("↻ Reprocessar IA");crm=QPushButton("👤 Abrir CRM");follow=QPushButton("⏰ Agendar retorno");close=QPushButton("Fechar")
        for b in (play,retry,crm,follow):bar.addWidget(b)
        bar.addStretch(1);bar.addWidget(close);lay.addLayout(bar)
        play.clicked.connect(lambda:self.play_audio(call_id));retry.clicked.connect(lambda:self.reprocess(call_id))
        crm.clicked.connect(lambda:self._open_crm_client(call))
        follow.clicked.connect(lambda:self._manual_followup(call,dlg))
        close.clicked.connect(dlg.accept);dlg.exec()

    def play_audio(self,call_id):
        call=self._find(call_id);path=str(call.get("mixed_audio") or "")
        if not path or not Path(path).exists():
            QMessageBox.information(self.owner,"Ligações IA","Áudio não encontrado.");return
        try:os.startfile(path)
        except Exception as exc:QMessageBox.warning(self.owner,"Ligações IA","Não consegui abrir o áudio:\n"+str(exc))

    def _open_crm_client(self,call):
        client=str(call.get("client") or "").strip()
        try:self.owner._crm_clients_dialog(self.owner)
        except Exception as exc:QMessageBox.warning(self.owner,"CRM",str(exc))

    def _manual_followup(self,call,parent):
        client=str(call.get("client") or "").strip();ev=call.get("evaluation") if isinstance(call.get("evaluation"),dict) else {}
        action=ev.get("proxima_acao") if isinstance(ev.get("proxima_acao"),dict) else {}
        try:self.owner._crm_followup_dialog(client,parent,None,str(action.get("motivo") or "Retornar após ligação"))
        except Exception as exc:QMessageBox.warning(parent,"CRM",str(exc))
