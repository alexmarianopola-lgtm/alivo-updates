from pathlib import Path
import json
import shutil
import sys

root=Path(sys.argv[1])
main=root/"_app"/"main.py"
src=Path(__file__).resolve().parent/"ponto_module_v2301.py"
dst=root/"_app"/"aliyvo_ponto.py"

text=main.read_text(encoding="utf-8")
if text.count('ALIYVO_VERSION = "0.23.00"') != 1:
    raise SystemExit("Versao base 0.23.00 nao encontrada")
text=text.replace('ALIYVO_VERSION = "0.23.00"','ALIYVO_VERSION = "0.23.01"',1)
main.write_text(text,encoding="utf-8")
shutil.copy2(src,dst)

ext=root/"EXTENSAO_PONTO_SANKHYA"
manifest_path=ext/"manifest.json"
manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"]="2.5.1"
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

bg=ext/"background.js"
bgt=bg.read_text(encoding="utf-8")
for old in ("aliyvo-ponto-02300","aliyvo-ponto-02299"):
    if old in bgt:
        bgt=bgt.replace(old,"aliyvo-ponto-02301")
bg.write_text(bgt,encoding="utf-8")

(root/"LEIA-ME-PONTO-02301.txt").write_text(
"""ALIYVO 0.23.01 - CORRECAO DO ATALHO AHGORA

Problema:
O Chrome era trazido para frente, mas Ctrl+Shift+9 nem sempre era entregue ao navegador.

Correcao:
- confirma que a janela do Chrome realmente ficou em primeiro plano;
- aguarda a troca de foco estabilizar;
- envia Ctrl+Shift+9 com a API SendInput do Windows em vez do metodo antigo;
- registra diagnostico com quantidade de eventos de teclado enviados.

Fluxo continua o mesmo:
BATER PONTO AGORA -> abre extensao Ahgora Ponto Online -> usuario bate o ponto ->
ALIYVO sincroniza para conferir.
""",encoding="utf-8")

print("PATCH_PONTO_02301=OK")
