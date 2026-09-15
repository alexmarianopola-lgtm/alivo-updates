from pathlib import Path
import re, sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
text=main.read_text(encoding='utf-8')

text,n=re.subn(r'ALIYVO_VERSION\s*=\s*["\']0\.22\.86["\']','ALIYVO_VERSION = "0.22.87"',text,count=1)
if n!=1:
    raise SystemExit(f'Versao 0.22.86 nao encontrada exatamente; ocorrencias={n}')

# Adiciona limpeza defensiva apenas das permissoes de microfone/camera do WhatsApp
# no perfil persistente do WebView2, preservando login, cookies e demais dados.
anchor='''def _prepare_stable_whatsapp_profile():\n'''
if anchor not in text:
    raise SystemExit('prepare_stable_whatsapp_profile nao encontrado')
helper='''def _reset_whatsapp_media_permissions():\n    """Remove somente decisoes salvas de microfone/camera do WhatsApp no perfil WebView2."""\n    try:\n        import json as _json\n        pref_candidates=[\n            WEBVIEW2_PROFILE_DIR/"Default"/"Preferences",\n            WEBVIEW2_PROFILE_DIR/"Preferences",\n        ]\n        changed_any=False\n        for pref in pref_candidates:\n            try:\n                if not pref.exists():\n                    continue\n                data=_json.loads(pref.read_text(encoding="utf-8"))\n                exc=(data.get("profile",{}).get("content_settings",{}).get("exceptions",{}))\n                changed=False\n                for bucket in ("media_stream_mic","media_stream_camera"):\n                    entries=exc.get(bucket)\n                    if not isinstance(entries,dict):\n                        continue\n                    for key in list(entries.keys()):\n                        lk=str(key).lower()\n                        if "whatsapp.com" in lk or "whatsapp.net" in lk:\n                            entries.pop(key,None)\n                            changed=True\n                if changed:\n                    tmp=pref.with_name(pref.name+".aliyvo_tmp")\n                    tmp.write_text(_json.dumps(data,ensure_ascii=False,separators=(",",":")),encoding="utf-8")\n                    tmp.replace(pref)\n                    changed_any=True\n            except Exception:\n                pass\n        if changed_any:\n            try:\n                log_dir=ALIYVO_USER_DIR/"logs"; log_dir.mkdir(parents=True,exist_ok=True)\n                import time as _time\n                with (log_dir/"WEBVIEW2_MEDIA.log").open("a",encoding="utf-8") as f:\n                    f.write("["+_time.strftime("%Y-%m-%d %H:%M:%S")+"] permissoes salvas de microfone/camera do WhatsApp redefinidas\\n")\n            except Exception:\n                pass\n    except Exception:\n        pass\n\n'''
text=text.replace(anchor,helper+anchor,1)

# Executa a limpeza antes de preparar/abrir o perfil WebView2.
call_anchor='_prepare_webview2_whatsapp_profile()\n'
idx=text.find(call_anchor)
if idx<0:
    raise SystemExit('chamada _prepare_webview2_whatsapp_profile nao encontrada')
text=text[:idx]+'_reset_whatsapp_media_permissions()\n'+text[idx:]

# Permite tambem origens auxiliares whatsapp.net.
old='''            if "whatsapp.com" not in uri:\n                return\n'''
new='''            if "whatsapp.com" not in uri and "whatsapp.net" not in uri:\n                return\n'''
if old not in text:
    raise SystemExit('filtro de origem WhatsApp nao encontrado')
text=text.replace(old,new,1)

# Nao deixa Allow/Deny antigo ficar preso no perfil: a rotina do ALIYVO decide a cada pedido.
old_save='''                try:args.SavesInProfile=True\n                except Exception:pass\n'''
new_save='''                try:args.SavesInProfile=False\n                except Exception:pass\n'''
if old_save not in text:
    raise SystemExit('SavesInProfile=True nao encontrado')
text=text.replace(old_save,new_save,1)

main.write_text(text,encoding='utf-8')
print('patched 0.22.87: reset seletivo de permissoes WhatsApp + permissao nao persistente')
