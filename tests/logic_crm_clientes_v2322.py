from pathlib import Path
import ast,sys,re
root=Path(sys.argv[1])
s=(root/'main.py').read_text(encoding='utf-8')
ast.parse(s)

need=[
 'ALIYVO_VERSION = "0.23.22"',
 'self.reminder_toggle=QPushButton("👥  CRM")',
 'def _crm_clients_file(self):',
 'return USER_DATA_DIR/"crm_clientes.json"',
 'def _crm_profile_dialog(',
 'def _crm_clients_dialog(',
 'def _crm_register_contact_dialog(',
 'def _crm_schedule_followup(',
 '"source":"crm_followup"',
 'clients_btn=QPushButton("👥 Clientes")',
 "clients=QPushButton('👥 Clientes CRM')",
]
for x in need: assert x in s,x

# Telefone salvo no CRM precisa alimentar Abrir WhatsApp.
m=re.search(r'def _attendance_phone_for_contact\(self,name\):(.{0,2200})',s,re.S)
assert m and '_crm_client_profile(raw)' in m.group(1)

# Follow-up deve fechar o anterior aberto do mesmo cliente e criar um novo.
m=re.search(r'def _crm_schedule_followup\(self,client,days=1,reason=""\):(.{0,5000})',s,re.S)
assert m
blk=m.group(1)
assert 'r["done"]=True' in blk and 'self._reminders.append' in blk and '_reminder_save' in blk

# Cadastro deve conter exatamente os campos comerciais pedidos.
m=re.search(r'def _crm_profile_dialog\(self,parent=None,name="",on_saved=None\):(.{0,7000})',s,re.S)
assert m
blk=m.group(1)
for fld in ['buyer','buyer_role','buys','brands','notes','phone']:
    assert fld in blk,fld

print('CRM_CLIENTES_V2322=OK')
