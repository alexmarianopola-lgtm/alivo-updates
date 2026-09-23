from pathlib import Path
import json
import shutil
import sys

root=Path(sys.argv[1])
main=root/"_app"/"main.py"
src=Path(__file__).resolve().parent/"ponto_module_v99.py"
dst=root/"_app"/"aliyvo_ponto.py"

text=main.read_text(encoding="utf-8")
if text.count('ALIYVO_VERSION = "0.22.98"') != 1:
    raise SystemExit("Versao base 0.22.98 nao encontrada")
text=text.replace('ALIYVO_VERSION = "0.22.98"','ALIYVO_VERSION = "0.22.99"',1)
main.write_text(text,encoding="utf-8")
shutil.copy2(src,dst)

ext=root/"EXTENSAO_PONTO_SANKHYA"
manifest_path=ext/"manifest.json"
manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"]="2.4.0"
manifest["description"]="Protege o Sankhya e integra o Controle de Ponto com o portal oficial Ahgora."
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

bg=ext/"background.js"
bgt=bg.read_text(encoding="utf-8")
for old in ("aliyvo-ponto-02298","aliyvo-ponto-02297"):
    if old in bgt:
        bgt=bgt.replace(old,"aliyvo-ponto-02299")
bg.write_text(bgt,encoding="utf-8")

(root/"LEIA-ME-PONTO-02299.txt").write_text(
"""ALIYVO 0.22.99 - BATIDA PELO PORTAL OFICIAL AHGORA

Motivo:
A empresa recusou o cadastro de dispositivo via API. Portanto o ALIYVO deixa de
tentar criar dispositivo para a Batida Online.

Novo fluxo:
1. Clique BATER PONTO AGORA.
2. O ALIYVO abre a pagina oficial do Ahgora usando a mesma sessao persistente.
3. Faca a batida normalmente no proprio portal Ahgora.
4. Clique JA BATI NO AHGORA - SINCRONIZAR.
5. O ALIYVO consulta novamente o espelho e mostra a nova batida real.

Vantagens:
- respeita a politica da empresa;
- nao cria dispositivo paralelo;
- nao registra ponto automaticamente;
- sincronizacao continua usando a sessao oficial;
- WhatsApp, updater e configuracoes permanecem preservados.
""",encoding="utf-8")

print("PATCH_PONTO_V99=OK")
