from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v13.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.27 - adiciona apenas cidade/estado aproximados ao registro anônimo de instalação.
# A localização é estimada pelo IP público, sem GPS e sem enviar o IP no payload do ALIYVO.
old='''            install_id=_aliyvo_feedback_install_id()\n            payload="\\n".join([\n                "ALIYVO BETA - INSTALACAO UNICA",\n                "Instalacao: "+str(install_id),\n                "Versao: "+str(globals().get("ALIYVO_VERSION","")),\n                "Plano: "+str(globals().get("ALIYVO_PLAN","BETA_FREE")),\n                "Windows: "+str(_platform.system())+" "+str(_platform.release()),\n                "Data: "+_datetime.now().strftime("%Y-%m-%d %H:%M:%S"),\n            ]).encode("utf-8")'''
if old not in text:
    raise SystemExit('unique install payload anchor not found')
new='''            install_id=_aliyvo_feedback_install_id()\n\n            # Localização aproximada apenas para estatística de adoção.\n            # O serviço externo vê o IP da conexão como qualquer site acessado,\n            # porém o ALIYVO não grava nem envia o IP no relatório.\n            city=""; region=""; country=""\n            try:\n                geo_req=_ur.Request(\n                    "https://ipapi.co/json/",\n                    headers={"User-Agent":"ALIYVO-Beta/"+str(globals().get("ALIYVO_VERSION",""))}\n                )\n                with _ur.urlopen(geo_req,timeout=5) as geo_resp:\n                    geo=json.loads(geo_resp.read(16384).decode("utf-8","replace"))\n                city=str(geo.get("city") or "").strip()[:80]\n                region=str(geo.get("region_code") or geo.get("region") or "").strip()[:80]\n                country=str(geo.get("country_code") or geo.get("country_name") or "").strip()[:80]\n            except Exception:\n                pass\n\n            location="Nao identificado"\n            if city or region or country:\n                parts=[x for x in (city,region,country) if x]\n                location=" / ".join(parts)\n\n            payload="\\n".join([\n                "ALIYVO BETA - INSTALACAO UNICA",\n                "Instalacao: "+str(install_id),\n                "Versao: "+str(globals().get("ALIYVO_VERSION","")),\n                "Plano: "+str(globals().get("ALIYVO_PLAN","BETA_FREE")),\n                "Windows: "+str(_platform.system())+" "+str(_platform.release()),\n                "Cidade/UF aproximada: "+location,\n                "Data: "+_datetime.now().strftime("%Y-%m-%d %H:%M:%S"),\n            ]).encode("utf-8")'''
text=text.replace(old,new,1)

# Transparência também no campo de feedback.
text=text.replace(
    'Será enviado: ALIYVO {globals().get(\'ALIYVO_VERSION\',\'\')} • Beta Grátis • ID anônimo da instalação • versão do Windows.',
    'Será enviado: ALIYVO {globals().get(\'ALIYVO_VERSION\',\'\')} • Beta Grátis • ID anônimo da instalação • versão do Windows. No primeiro uso, cidade/estado aproximados pela internet são registrados para estatística, sem GPS ou endereço exato.',
    1
)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched approximate city/state install stats',version)
