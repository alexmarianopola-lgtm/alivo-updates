from pathlib import Path
import json
import shutil
import sys

root=Path(sys.argv[1])
main=root/"_app"/"main.py"
src=Path(__file__).resolve().parent/"ponto_module_v98.py"
dst=root/"_app"/"aliyvo_ponto.py"

text=main.read_text(encoding="utf-8")
if text.count('ALIYVO_VERSION = "0.22.97"') != 1:
    raise SystemExit("Versao base 0.22.97 nao encontrada")
text=text.replace('ALIYVO_VERSION = "0.22.97"','ALIYVO_VERSION = "0.22.98"',1)
main.write_text(text,encoding="utf-8")
shutil.copy2(src,dst)

ext=root/"EXTENSAO_PONTO_SANKHYA"
manifest_path=ext/"manifest.json"
manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"]="2.3.2"
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

bg=ext/"background.js"
bgt=bg.read_text(encoding="utf-8")
for old in ("aliyvo-ponto-02297","aliyvo-ponto-02296"):
    if old in bgt:
        bgt=bgt.replace(old,"aliyvo-ponto-02298")
bg.write_text(bgt,encoding="utf-8")

(root/"LEIA-ME-PONTO-02298.txt").write_text(
"""ALIYVO 0.22.98 - BOTAO DE PONTO SEMPRE DISPONIVEL

Mudanca solicitada:
O botao BATER PONTO AGORA fica visivel sempre que o Ahgora estiver conectado e
a ultima sincronizacao for valida, mesmo antes do horario previsto.

Exemplo:
12:03 -> botao mostra BATER PONTO AGORA | proximo: Volta do almoco 13:30

Seguranca:
- a batida nunca e automatica;
- ao clicar, o ALIYVO mostra horario atual, proximo evento esperado e batidas ja
  encontradas hoje;
- exige confirmacao antes de enviar;
- depois sincroniza novamente para conferir a batida real;
- continua possivel bater adiantado ou atrasado quando necessario.
""",encoding="utf-8")

print("PATCH_PONTO_V98=OK")
