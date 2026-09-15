from pathlib import Path
import re, sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
text=main.read_text(encoding='utf-8')

text,n=re.subn(r'ALIYVO_VERSION\s*=\s*["\']0\.22\.86["\']','ALIYVO_VERSION = "0.22.88"',text,count=1)
if n!=1:
    raise SystemExit(f'Versao 0.22.86 nao encontrada exatamente; ocorrencias={n}')

call='_prepare_webview2_whatsapp_profile()\n'
idx=text.find(call)
if idx<0:
    raise SystemExit('chamada _prepare_webview2_whatsapp_profile nao encontrada')

helper='''def _reset_whatsapp_media_permissions():\n    """Remove somente permissoes salvas de microfone/camera do WhatsApp no perfil WebView2."""\n    try:\n        import json as _json\n        pref_candidates=[\n            WEBVIEW2_PROFILE_DIR/"Default"/"Preferences",\n            WEBVIEW2_PROFILE_DIR/"Preferences",\n        ]\n        for pref in pref_candidates:\n            try:\n                if not pref.exists():\n                    continue\n                data=_json.loads(pref.read_text(encoding="utf-8"))\n                exc=(data.get("profile",{}).get("content_settings",{}).get("exceptions",{}))\n                changed=False\n                for bucket in ("media_stream_mic","media_stream_camera"):\n                    entries=exc.get(bucket)\n                    if not isinstance(entries,dict):\n                        continue\n                    for key in list(entries.keys()):\n                        lk=str(key).lower()\n                        if "whatsapp.com" in lk or "whatsapp.net" in lk:\n                            entries.pop(key,None)\n                            changed=True\n                if changed:\n                    tmp=pref.with_name(pref.name+".aliyvo_tmp")\n                    tmp.write_text(_json.dumps(data,ensure_ascii=False,separators=(",",":")),encoding="utf-8")\n                    tmp.replace(pref)\n            except Exception:\n                pass\n    except Exception:\n        pass\n\n'''

# A definicao fica imediatamente ANTES da chamada de inicializacao para evitar NameError.
text=text[:idx]+helper+'_reset_whatsapp_media_permissions()\n'+text[idx:]

old='''            if "whatsapp.com" not in uri:\n                return\n'''
new='''            if "whatsapp.com" not in uri and "whatsapp.net" not in uri:\n                return\n'''
if old not in text:
    raise SystemExit('filtro de origem WhatsApp nao encontrado')
text=text.replace(old,new,1)

old_save='''                try:args.SavesInProfile=True\n                except Exception:pass\n'''
new_save='''                try:args.SavesInProfile=False\n                except Exception:pass\n'''
if old_save not in text:
    raise SystemExit('SavesInProfile=True nao encontrado')
text=text.replace(old_save,new_save,1)

main.write_text(text,encoding='utf-8')
print('patched 0.22.88: corrigido startup + reset seletivo de permissoes WhatsApp')
