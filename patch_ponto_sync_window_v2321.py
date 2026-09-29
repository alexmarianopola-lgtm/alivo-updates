from pathlib import Path
import sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
p=root/'_app'/'aliyvo_ponto.py'

ms=main.read_text(encoding='utf-8')
ps=p.read_text(encoding='utf-8')

if 'ALIYVO_VERSION = "0.23.20"' not in ms:
    raise SystemExit('base main 0.23.20 nao encontrada')
ms=ms.replace('ALIYVO_VERSION = "0.23.20"','ALIYVO_VERSION = "0.23.21"',1)
ms=ms.replace('aliyvo_version="0.23.20"','aliyvo_version="0.23.21"')

# O modulo de ponto da 0.23.20 veio da base restaurada 0.23.18.
if 'POINT_MODULE_VERSION = "0.23.18"' in ps:
    ps=ps.replace('POINT_MODULE_VERSION = "0.23.18"','POINT_MODULE_VERSION = "0.23.21"',1)
elif 'POINT_MODULE_VERSION = "0.23.20"' in ps:
    ps=ps.replace('POINT_MODULE_VERSION = "0.23.20"','POINT_MODULE_VERSION = "0.23.21"',1)
else:
    raise SystemExit('versao esperada do modulo de ponto nao encontrada')

old='''def _mirror_month_key(now: datetime) -> str:
    month = now.month + (1 if now.day >= 26 else 0)
    year = now.year
    if month == 13:
        month = 1
        year += 1
    return f"{year:04d}-{month:02d}"
'''
new='''def _month_key_shift(now: datetime, offset: int) -> str:
    month_index = (now.year * 12 + (now.month - 1)) + int(offset)
    year, month0 = divmod(month_index, 12)
    return f"{year:04d}-{month0 + 1:02d}"


def _mirror_month_candidates(now: datetime) -> list[str]:
    """Periodos candidatos do espelho, sempre priorizando o mes civil atual.

    A versao anterior avancava para o mes seguinte a partir do dia 26. Em contas
    como a deste usuario isso fazia 29/09 consultar outubro e retornar zero
    batidas, mesmo com 08:16 visivel no Ahgora.
    """
    out: list[str] = []
    for offset in (0, 1, -1):
        key = _month_key_shift(now, offset)
        if key not in out:
            out.append(key)
    return out


def _mirror_month_key(now: datetime) -> str:
    return _mirror_month_candidates(now)[0]
'''
if old not in ps:
    raise SystemExit('funcao _mirror_month_key antiga nao encontrada')
ps=ps.replace(old,new,1)

old='''    day_key = _date_key(now)
    day = days.get(day_key)
    if day is None:
        # Dia ainda sem batidas pode existir ou não no retorno; isso é válido.
        punch_count = 0
    elif not isinstance(day, dict):
        raise RuntimeError("O registro de hoje no espelho possui formato inesperado.")
    else:
        raw = day.get("batidas")
        if raw is None:
            punch_count = 0
        elif not isinstance(raw, list):
            raise RuntimeError("A lista de batidas de hoje possui formato inesperado.")
        else:
            punch_count = len(raw)
'''
new='''    day_key = _date_key(now)
    day = days.get(day_key)
    if day is None:
        raise RuntimeError(
            f"O periodo {month_key} nao contem o dia {day_key}; tentando outro periodo."
        )
    if not isinstance(day, dict):
        raise RuntimeError("O registro de hoje no espelho possui formato inesperado.")

    raw = day.get("batidas")
    if raw is None:
        punch_count = 0
    elif not isinstance(raw, list):
        raise RuntimeError("A lista de batidas de hoje possui formato inesperado.")
    else:
        punch_count = len(raw)
'''
if old not in ps:
    raise SystemExit('bloco de validacao do dia nao encontrado')
ps=ps.replace(old,new,1)

old='''def reconcile_real_punches(state: dict[str, Any], punches: list[str], now: datetime) -> dict[str, Any]:
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
'''
new='''PUNCH_MATCH_WINDOW_MINUTES = 60


def _hhmm_minutes(value: Any) -> int | None:
    s = _normalize_punch_time(value)
    try:
        h, m = s[:5].split(":")
        hh, mm = int(h), int(m)
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return hh * 60 + mm
    except Exception:
        pass
    return None


def _match_punches_to_slots(
    punches: list[str],
    *,
    window_minutes: int = PUNCH_MATCH_WINDOW_MINUTES,
) -> dict[str, str]:
    """Casa cada batida ao horario previsto mais proximo dentro de +/- 1 hora."""
    parsed: list[tuple[int, str]] = []
    seen: set[str] = set()
    for raw in punches:
        normalized = _normalize_punch_time(raw)
        minute = _hhmm_minutes(normalized)
        if minute is None or normalized in seen:
            continue
        seen.add(normalized)
        parsed.append((minute, normalized))

    pairs: list[tuple[int, int, int]] = []
    for slot_index, slot in enumerate(POINT_SLOTS):
        slot_minute = _hhmm_minutes(slot["time"])
        if slot_minute is None:
            continue
        for punch_index, (punch_minute, _text) in enumerate(parsed):
            diff = abs(punch_minute - slot_minute)
            if diff <= int(window_minutes):
                pairs.append((diff, slot_index, punch_index))

    pairs.sort(key=lambda row: (row[0], row[1], row[2]))
    used_slots: set[int] = set()
    used_punches: set[int] = set()
    matched: dict[str, str] = {}

    for _diff, slot_index, punch_index in pairs:
        if slot_index in used_slots or punch_index in used_punches:
            continue
        used_slots.add(slot_index)
        used_punches.add(punch_index)
        matched[POINT_SLOTS[slot_index]["id"]] = parsed[punch_index][1]

    return matched


def reconcile_real_punches(state: dict[str, Any], punches: list[str], now: datetime) -> dict[str, Any]:
    """Confirma somente batidas reais dentro de +/- 60 min do horario previsto."""
    state = normalize_state(state, now)
    slots = state.setdefault("slots", {})
    matched = _match_punches_to_slots(punches)

    for slot in POINT_SLOTS:
        slot_id = slot["id"]
        actual = matched.get(slot_id)
        existing = slots.get(slot_id) if isinstance(slots.get(slot_id), dict) else {}

        if actual:
            slots[slot_id] = {
                "status": "confirmed",
                "scheduled_time": slot["time"],
                "resolved_at": now.isoformat(timespec="seconds"),
                "actual_time": actual,
                "source": "ahgora_sync",
            }
        elif existing.get("source") == "ahgora_sync":
            # Remove apenas confirmacoes vindas de sincronizacao anterior.
            # Confirmacoes manuais/contingencia continuam preservadas.
            slots.pop(slot_id, None)

    return state
'''
if old not in ps:
    raise SystemExit('reconcile_real_punches antigo nao encontrado')
ps=ps.replace(old,new,1)

old='''    month_key = _mirror_month_key(now)
    descriptor = months.get(month_key)
    if not isinstance(descriptor, dict):
        raise RuntimeError(f"O Ahgora não disponibilizou o mês {month_key} no espelho.")
    reference = str(descriptor.get("referencia") or "").strip()
    if not reference:
        raise RuntimeError(f"O mês {month_key} veio sem referência no espelho.")

    detail_url = AHGORA_MIRROR_API + urllib.parse.quote(reference, safe="")
    detail = _decode_json_body(
        _request_bytes(opener, detail_url, headers={"Accept": "application/json"}),
        "Espelho mensal Ahgora",
    )
    validation = validate_modern_mirror_payload(index, detail, now, month_key)
    punches = extract_today_punches(detail, now)
    return {
        "index": index,
        "payload": detail,
        "validation": validation,
        "punches": punches,
    }
'''
new='''    last_error = ""
    for month_key in _mirror_month_candidates(now):
        descriptor = months.get(month_key)
        if not isinstance(descriptor, dict):
            continue
        reference = str(descriptor.get("referencia") or "").strip()
        if not reference:
            continue

        detail_url = AHGORA_MIRROR_API + urllib.parse.quote(reference, safe="")
        detail = _decode_json_body(
            _request_bytes(opener, detail_url, headers={"Accept": "application/json"}),
            "Espelho mensal Ahgora",
        )

        days = detail.get("dias") if isinstance(detail, dict) else None
        if not isinstance(days, dict) or _date_key(now) not in days:
            last_error = f"{month_key} sem o dia {_date_key(now)}"
            continue

        validation = validate_modern_mirror_payload(index, detail, now, month_key)
        punches = extract_today_punches(detail, now)
        return {
            "index": index,
            "payload": detail,
            "validation": validation,
            "punches": punches,
        }

    raise RuntimeError(
        "Nenhum periodo do espelho retornou o dia de hoje. "
        + (last_error or "Mes atual/adjacentes indisponiveis.")
    )
'''
if old not in ps:
    raise SystemExit('fluxo de mes da consulta direta nao encontrado')
ps=ps.replace(old,new,1)

old='''        def load_detail(index: dict[str, Any]):
            months = index.get("meses") if isinstance(index, dict) else None
            if not isinstance(months, dict):
                fail(
                    "O portal abriu, mas a sessão atual não liberou o espelho de ponto. "
                    "Entre novamente no Ahgora por esta janela."
                )
                return

            now = datetime.now()
            month_key = _mirror_month_key(now)
            descriptor = months.get(month_key)
            if not isinstance(descriptor, dict):
                fail(f"O mês {month_key} não apareceu no espelho do Ahgora.")
                return
            reference = str(descriptor.get("referencia") or "").strip()
            if not reference:
                fail("O Ahgora retornou o mês sem referência de apuração.")
                return

            detail_url = AHGORA_MIRROR_API + urllib.parse.quote(reference, safe="")

            def detail_loaded(ok: bool):
                try:
                    view.loadFinished.disconnect(detail_loaded)
                except Exception:
                    pass
                if not ok:
                    fail("Não foi possível abrir o detalhe do espelho do Ahgora.")
                    return

                def use_detail(detail):
                    try:
                        validation = validate_modern_mirror_payload(
                            index, detail, now, month_key
                        )
                        punches = extract_today_punches(detail, now)
                    except Exception as exc:
                        fail(str(exc))
                        return
                    success(
                        {
                            "payload": detail,
                            "punches": punches,
                            "reason": reason,
                            "validation": validation,
                        }
                    )

                read_page_json("Detalhe do espelho Ahgora", use_detail)

            view.loadFinished.connect(detail_loaded)
            view.setUrl(QUrl(detail_url))
'''
new='''        def load_detail(index: dict[str, Any]):
            months = index.get("meses") if isinstance(index, dict) else None
            if not isinstance(months, dict):
                fail(
                    "O portal abriu, mas a sessão atual não liberou o espelho de ponto. "
                    "Entre novamente no Ahgora por esta janela."
                )
                return

            now = datetime.now()
            candidates = [
                key for key in _mirror_month_candidates(now)
                if isinstance(months.get(key), dict)
            ]
            if not candidates:
                fail("O Ahgora não retornou o mês atual nem períodos adjacentes.")
                return

            def try_candidate(pos: int):
                if pos >= len(candidates):
                    fail(
                        "O espelho abriu, mas nenhum período consultado contém o dia de hoje."
                    )
                    return

                month_key = candidates[pos]
                descriptor = months.get(month_key) or {}
                reference = str(descriptor.get("referencia") or "").strip()
                if not reference:
                    try_candidate(pos + 1)
                    return

                detail_url = AHGORA_MIRROR_API + urllib.parse.quote(reference, safe="")

                def detail_loaded(ok: bool):
                    try:
                        view.loadFinished.disconnect(detail_loaded)
                    except Exception:
                        pass
                    if not ok:
                        try_candidate(pos + 1)
                        return

                    def use_detail(detail):
                        days = detail.get("dias") if isinstance(detail, dict) else None
                        if not isinstance(days, dict) or _date_key(now) not in days:
                            try_candidate(pos + 1)
                            return
                        try:
                            validation = validate_modern_mirror_payload(
                                index, detail, now, month_key
                            )
                            punches = extract_today_punches(detail, now)
                        except Exception:
                            try_candidate(pos + 1)
                            return
                        success(
                            {
                                "payload": detail,
                                "punches": punches,
                                "reason": reason,
                                "validation": validation,
                            }
                        )

                    read_page_json("Detalhe do espelho Ahgora", use_detail)

                view.loadFinished.connect(detail_loaded)
                view.setUrl(QUrl(detail_url))

            try_candidate(0)
'''
if old not in ps:
    raise SystemExit('load_detail antigo nao encontrado')
ps=ps.replace(old,new,1)

main.write_text(ms,encoding='utf-8')
p.write_text(ps,encoding='utf-8')
print('PATCH_PONTO_SYNC_WINDOW_V2321=OK')
