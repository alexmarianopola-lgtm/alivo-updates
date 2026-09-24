from pathlib import Path
import json,sys

root=Path(sys.argv[1])
origin_id=sys.argv[2]
base_zip_sha512=sys.argv[3]
base_main_sha512=sys.argv[4]

main=root/'_app'/'main.py'
text=main.read_text(encoding='utf-8')

if 'ALIYVO_VERSION = "0.23.02"' not in text:
    raise SystemExit('base esperada 0.23.02 nao encontrada')

text=text.replace('ALIYVO_VERSION = "0.23.02"', '''ALIYVO_VERSION = "0.23.03"
# Proveniencia tecnica do ALIYVO.
# Nao e mecanismo de seguranca nem substitui registro juridico.
# Serve como marcador persistente ligado ao snapshot e ao historico Git.
ALIYVO_ORIGIN_ID = "ALIYVO-ORIGIN-20260924-2302-6F91D2C4A8E73B5C"
ALIYVO_ORIGIN_REPOSITORY = "alexmarianopola-lgtm/alivo-updates"
ALIYVO_ORIGIN_SNAPSHOT_DATE = "2026-09-24"
ALIYVO_ORIGIN_BASE_RELEASE = "v0.23.02"''',1)

text=text.replace('aliyvo_version="0.23.02"','aliyvo_version="0.23.03"')
main.write_text(text,encoding='utf-8')

prov={
  "schema":"aliyvo-provenance-v1",
  "origin_id":origin_id,
  "repository":"alexmarianopola-lgtm/alivo-updates",
  "snapshot_date":"2026-09-24",
  "base_release":"v0.23.02",
  "base_release_zip_sha512":base_zip_sha512.lower(),
  "base_main_py_sha512":base_main_sha512.lower(),
  "purpose":"technical provenance marker and historical fingerprint",
  "note":"This file is a technical provenance record, not a substitute for formal IP registration."
}
(root/'_app'/'ALIYVO_PROVENANCE.json').write_text(json.dumps(prov,ensure_ascii=False,indent=2),encoding='utf-8')
print('PATCH_PROVENANCE_V2303=OK')
