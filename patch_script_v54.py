from pathlib import Path
import sys,re,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v54.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

old='crm.clicked.connect(lambda:self._reminder_crm_dialog(dlg))'
new='crm.clicked.connect(lambda:self._ai_crm_reminders_dialog(dlg))'
if old not in text:
    raise SystemExit('CRM button connection anchor not found')
text=text.replace(old,new,1)

old_prompt='"instructions":self._ai_prompt("conversation" if mode=="conversation" else "observer"),'
new_prompt='"instructions":self._ai_prompt(mode),'
if old_prompt in text:
    text=text.replace(old_prompt,new_prompt,1)
else:
    # aceita pequenas variacoes de espaco
    text=re.sub(r'"instructions"\s*:\s*self\._ai_prompt\("conversation"\s*if\s*mode\s*==\s*"conversation"\s*else\s*"observer"\)\s*,', '"instructions":self._ai_prompt(mode),', text, count=1)

p.write_text(text,encoding='utf-8')
print('patched CRM button + AI prompt routing',version)
