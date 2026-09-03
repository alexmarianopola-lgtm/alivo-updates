from pathlib import Path
import shutil,sys,re

build=Path(sys.argv[1])
repo=Path(__file__).resolve().parent

for name in ['dados','cache_usuario','logs','webview2_whatsapp_profile','CANAL_ATUALIZACAO_EXEMPLO']:
    p=build/name
    if p.exists():
        if p.is_dir(): shutil.rmtree(p,ignore_errors=True)
        else: p.unlink(missing_ok=True)

for p in build.glob('NOVIDADES_ALIYVO_v*.txt'):
    p.unlink(missing_ok=True)
for pattern in ['LEIA-ME_*.txt','ATUALIZADOR_AUTOMATICO.txt','COMO USAR.txt']:
    for p in build.glob(pattern): p.unlink(missing_ok=True)

setup=build/'_app'/'_setup'
if setup.exists():
    for p in setup.glob('*.txt'):
        p.unlink(missing_ok=True)
    for p in setup.glob('*.bat'):
        try:
            s=p.read_text(encoding='utf-8',errors='replace')
            s=s.replace('COPILOTO SOMAFORCE','ALIYVO').replace('SOMAFORCE','ALIYVO')
            p.write_bytes(s.replace('\r\n','\n').replace('\n','\r\n').encode('ascii','replace'))
        except Exception:
            pass

# Remove aviso antigo com nome corrompido/branding legado se existir.
for p in build.glob('*ABRIR*A PASTA*'):
    try: p.unlink()
    except Exception: pass

shutil.copy2(repo/'distribuicao'/'INSTALAR ALIYVO.bat',build/'INSTALAR ALIYVO.bat')
shutil.copy2(repo/'distribuicao'/'LEIA-ME-ALIYVO.txt',build/'LEIA-ME-ALIYVO.txt')

main=(build/'_app'/'main.py').read_text(encoding='utf-8',errors='replace')
assert 'ALIYVO_PLAN = "BETA_FREE"' in main, 'plano Beta nao encontrado'
assert 'class AliyvoFeedbackDialog(QDialog):' in main, 'feedback nao encontrado'
assert 'COPILOTO SOMAFORCE' not in main, 'branding antigo ainda visivel no main.py'
print('distribution prepared cleanly')
