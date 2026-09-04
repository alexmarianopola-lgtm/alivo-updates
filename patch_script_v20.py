from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v20.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.34 - faz urllib/HTTPS confiar tambem nos certificados raiz do Windows.
# Mantem a verificacao SSL ativa; apenas adiciona o trust store do Windows ao contexto.
if '_aliyvo_install_windows_certificate_bridge' not in text:
    vm=re.search(r'(?m)^ALIYVO_VERSION\s*=.*$',text)
    if not vm:
        raise SystemExit('ALIYVO_VERSION anchor not found')
    bridge=r'''

# -----------------------------------------------------------------------------
# ALIYVO HTTPS - ponte segura com os certificados confiaveis do Windows
# Evita CERTIFICATE_VERIFY_FAILED em PCs onde Python/OpenSSL nao enxerga a mesma
# cadeia de certificados que Edge/Chrome/Windows. A verificacao SSL continua ativa.
# -----------------------------------------------------------------------------
def _aliyvo_install_windows_certificate_bridge():
    try:
        import os as _os
        import ssl as _ssl
        if _os.name != "nt" or not hasattr(_ssl,"enum_certificates"):
            return
        pem=[]
        seen=set()
        for store in ("ROOT","CA"):
            try:
                certs=_ssl.enum_certificates(store)
            except Exception:
                certs=[]
            for cert,encoding,trust in certs:
                try:
                    if encoding != "x509_asn":
                        continue
                    key=bytes(cert[:40])
                    if key in seen:
                        continue
                    seen.add(key)
                    pem.append(_ssl.DER_cert_to_PEM_cert(cert))
                except Exception:
                    pass
        if not pem:
            return
        cadata="\n".join(pem)
        def _aliyvo_https_context(*args,**kwargs):
            ctx=_ssl.create_default_context()
            try:
                ctx.load_verify_locations(cadata=cadata)
            except Exception:
                pass
            return ctx
        _ssl._create_default_https_context=_aliyvo_https_context
    except Exception:
        pass

_aliyvo_install_windows_certificate_bridge()
'''
    text=text[:vm.end()]+bridge+text[vm.end():]

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched Windows certificate bridge',version)
