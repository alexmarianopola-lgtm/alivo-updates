from pathlib import Path
import json
import shutil
import sys

root=Path(sys.argv[1])
main=root/"_app"/"main.py"
src=Path(__file__).resolve().parent/"ponto_module_v2300.py"
dst=root/"_app"/"aliyvo_ponto.py"

text=main.read_text(encoding="utf-8")
if text.count('ALIYVO_VERSION = "0.22.99"') != 1:
    raise SystemExit("Versao base 0.22.99 nao encontrada")
text=text.replace('ALIYVO_VERSION = "0.22.99"','ALIYVO_VERSION = "0.23.00"',1)
main.write_text(text,encoding="utf-8")
shutil.copy2(src,dst)

ext=root/"EXTENSAO_PONTO_SANKHYA"
manifest_path=ext/"manifest.json"
manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"]="2.5.0"
manifest["description"]="Protege o Sankhya e usa o atalho da extensao oficial Ahgora Ponto Online no Chrome."
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

bg=ext/"background.js"
bgt=bg.read_text(encoding="utf-8")
for old in ("aliyvo-ponto-02299","aliyvo-ponto-02298"):
    if old in bgt:
        bgt=bgt.replace(old,"aliyvo-ponto-02300")
bg.write_text(bgt,encoding="utf-8")

(root/"LEIA-ME-PONTO-02300.txt").write_text(
"""ALIYVO 0.23.00 - EXTENSAO OFICIAL AHGORA NO CHROME

Requisito:
No Chrome, em chrome://extensions/shortcuts, a extensao Ahgora Ponto Online deve
estar configurada com Ctrl+Shift+9.

Fluxo:
1. Clique BATER PONTO AGORA no ALIYVO.
2. O ALIYVO ativa uma janela existente do Google Chrome.
3. Envia Ctrl+Shift+9.
4. A extensao oficial/licenciada Ahgora Ponto Online abre.
5. Voce informa matricula/senha e clica Bater Ponto na propria extensao.
6. O ALIYVO verifica o espelho automaticamente depois e tambem quando voce volta ao app.

Seguranca:
- o ALIYVO nao le nem preenche sua senha na extensao;
- nao clica em Bater Ponto automaticamente;
- nao cria dispositivo alternativo;
- nao registra ponto em segundo plano;
- sincronizacao posterior e somente leitura.
""",encoding="utf-8")

print("PATCH_PONTO_02300=OK")
