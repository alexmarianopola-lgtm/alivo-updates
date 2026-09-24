from pathlib import Path
import json,sys

app=Path(sys.argv[1])
main=(app/'main.py').read_text(encoding='utf-8')
assert 'ALIYVO_VERSION = "0.23.03"' in main
assert 'ALIYVO_ORIGIN_ID = "ALIYVO-ORIGIN-20260924-2302-6F91D2C4A8E73B5C"' in main
assert 'ALIYVO_ORIGIN_REPOSITORY = "alexmarianopola-lgtm/alivo-updates"' in main
assert 'ALIYVO_ORIGIN_SNAPSHOT_DATE = "2026-09-24"' in main
assert 'ALIYVO_ORIGIN_BASE_RELEASE = "v0.23.02"' in main
p=app/'ALIYVO_PROVENANCE.json'
assert p.exists()
x=json.loads(p.read_text(encoding='utf-8'))
assert x['origin_id']=="ALIYVO-ORIGIN-20260924-2302-6F91D2C4A8E73B5C"
assert x['repository']=="alexmarianopola-lgtm/alivo-updates"
assert len(x['base_release_zip_sha512'])==128
assert len(x['base_main_py_sha512'])==128
assert 'def _crm_detect_state(self,client,context):' in main
assert 'setInterval(20000)' in main
print('PROVENANCE_MARKER=OK')
print('PROVENANCE_MANIFEST=OK')
print('CRM_PRESERVED=OK')
print('WHATSAPP_TURBO_PRESERVED=OK')
print('ALIYVO_V2303_PROVENANCE=OK')
