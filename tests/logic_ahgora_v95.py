import base64
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

os.environ["QT_QPA_PLATFORM"]="offscreen"
os.environ["LOCALAPPDATA"]=str(Path(tempfile.gettempdir())/"aliyvo-v95-test")

appdir=Path(sys.argv[1])
sys.path.insert(0,str(appdir))
import aliyvo_ponto as p

assert p.POINT_MODULE_VERSION=="0.22.95"
assert "getApuracao" not in (appdir/"aliyvo_ponto.py").read_text(encoding="utf-8")
assert p.AHGORA_MIRROR_API=="https://app.ahgora.com.br/api-espelho/apuracao/"
assert p.AHGORA_PUNCH_BASE=="https://app.ahgora.com.br/batidaonline"

# Horarios reais retornados em formatos diferentes.
assert p._normalize_punch_time("0751")=="07:51"
assert p._normalize_punch_time("07:51")=="07:51"
assert p._normalize_punch_time("090008")=="09:00"

now=datetime(2026,9,23,10,40)
assert p._mirror_month_key(now)=="2026-09"
assert p._mirror_month_key(datetime(2026,9,26,8,0))=="2026-10"
assert p._mirror_month_key(datetime(2026,12,30,8,0))=="2027-01"

index={
  "meses":{
    "2026-09":{"referencia":"ref-set-2026"}
  }
}
detail={
  "dias":{
    "2026-09-23":{
      "batidas":[{"hora":"07:49"},{"hora":"12:09"}]
    }
  }
}
v=p.validate_modern_mirror_payload(index,detail,now,"2026-09")
assert v["session_ok"] is True
assert v["modern_api"] is True
assert v["punch_count"]==2
assert p.extract_today_punches(detail,now)==["07:49","12:09"]

# Simula o fluxo HTTP atual sem rede real.
calls=[]
old_request=p._request_bytes
def fake_request(opener,url,**kwargs):
    calls.append((url,kwargs.get("method"),kwargs.get("data")))
    if url==p.AHGORA_LOGIN_URL:
        return b"<html>ok</html>"
    if url==p.AHGORA_MIRROR_HOME:
        return b"<html>mirror</html>"
    if url==p.AHGORA_MIRROR_API:
        return json.dumps(index).encode()
    if url==p.AHGORA_MIRROR_API+"ref-set-2026":
        return json.dumps(detail).encode()
    raise AssertionError("URL inesperada "+url)
p._request_bytes=fake_request
try:
    result=p._login_and_fetch_modern_mirror(
        {"company_id":"EMP","registration":"123","password":"secret"},
        now
    )
finally:
    p._request_bytes=old_request
assert result["punches"]==["07:49","12:09"]
assert calls[0][0]==p.AHGORA_LOGIN_URL
assert p.AHGORA_MIRROR_API in [x[0] for x in calls]

# Resposta deprecated antiga jamais pode ser aceita pelo novo contrato.
try:
    p.validate_modern_mirror_payload({"error":"deprecated"},{},now,"2026-09")
except RuntimeError:
    pass
else:
    raise AssertionError("deprecated foi aceito")

# Reconcilia o que realmente existe no espelho e limpa estado local antigo.
state=p.normalize_state({},now)
state["slots"]["entrada"]={"status":"missed","source":"local"}
state=p.reconcile_real_punches(state,["07:49","12:09"],now)
assert state["slots"]["entrada"]["actual_time"]=="07:49"
assert state["slots"]["saida_almoco"]["actual_time"]=="12:09"
assert state["slots"]["entrada"]["source"]=="ahgora_sync"

# RSA PKCS#1 v1.5 puro do modulo deve ser compativel com uma chave real.
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
public_pem=private.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo
).decode()
cipher_b64=p._rsa_pkcs1_v15_encrypt_b64(public_pem,"SenhaTeste123")
plain=private.decrypt(base64.b64decode(cipher_b64),padding.PKCS1v15()).decode()
assert plain=="SenhaTeste123"

# Dispositivo modern punch: mock completo, sem registrar batida real.
old_post=p._post_json
old_req=p._request_bytes
post_calls=[]
def fake_post(url,fields,headers=None,timeout=15.0):
    post_calls.append((url,dict(fields),dict(headers or {})))
    if url.endswith("/activateDeviceOnLineByLoginAndPassword"):
        return {"activationKey":"key123"}
    if url.endswith("/activateFunctionality"):
        return {"identity":"identity123"}
    if url.endswith("/getDefaultExternalInfo"):
        return {"token":"token123"}
    raise AssertionError(url)

def fake_req(opener,url,**kwargs):
    if "/getPublicKey?" in url:
        return json.dumps({"public_key":public_pem}).encode()
    if url.endswith("/verifyIdentification"):
        assert kwargs["headers"]["Authorization"]=="token123"
        body=kwargs["data"]
        assert b'name="enc"' in body and b"true" in body
        assert b'name="origin"' in body and b"pw2" in body
        return json.dumps({
            "result":True,
            "time":"105501",
            "batidas_dia":["074901","120901","133102"]
        }).encode()
    raise AssertionError(url)

p._post_json=fake_post
p._request_bytes=fake_req
try:
    punch,updated=p._modern_punch({
        "company_id":"EMP",
        "registration":"123",
        "password":"SenhaTeste123",
        "device_identity":"",
        "activation_key":"",
        "public_key":"",
    })
finally:
    p._post_json=old_post
    p._request_bytes=old_req

assert punch["result"] is True
assert updated["device_identity"]=="identity123"
assert updated["activation_key"]=="key123"
assert "BEGIN PUBLIC KEY" in updated["public_key"]

source=(appdir/"aliyvo_ponto.py").read_text(encoding="utf-8")
assert "self._timer.setSingleShot(True)" in source
assert "setInterval(" not in source
assert "runJavaScript" not in source
assert "evaluate_js" not in source
assert 'POINT_API_SECRET = "aliyvo-ponto-02295"' in source

print("AHGORA_V95_MODERN_MIRROR=OK")
print("AHGORA_V95_REAL_PUNCH_RECONCILE=OK")
print("AHGORA_V95_RSA=OK")
print("AHGORA_V95_MODERN_PUNCH=OK")
print("ALIYVO_V95_AHGORA_CURRENT=OK")
