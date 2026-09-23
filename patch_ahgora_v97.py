from pathlib import Path
import json
import shutil
import sys

root=Path(sys.argv[1])
main=root/"_app"/"main.py"
src=Path(__file__).resolve().parent/"ponto_module_v97.py"
dst=root/"_app"/"aliyvo_ponto.py"

text=main.read_text(encoding="utf-8")
if text.count('ALIYVO_VERSION = "0.22.96"') != 1:
    raise SystemExit("Versao base 0.22.96 nao encontrada")
text=text.replace('ALIYVO_VERSION = "0.22.96"','ALIYVO_VERSION = "0.22.97"',1)
main.write_text(text,encoding="utf-8")
shutil.copy2(src,dst)

ext=root/"EXTENSAO_PONTO_SANKHYA"
manifest_path=ext/"manifest.json"
manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"]="2.3.1"
manifest["description"]="Protege o Sankhya usando o Controle de Ponto com sessao oficial Ahgora e leitura direta do espelho."
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

bg=ext/"background.js"
bgt=bg.read_text(encoding="utf-8")
for old in ("aliyvo-ponto-02296","aliyvo-ponto-02295"):
    if old in bgt:
        bgt=bgt.replace(old,"aliyvo-ponto-02297")
bg.write_text(bgt,encoding="utf-8")

(root/"LEIA-ME-PONTO-02297.txt").write_text(
"""ALIYVO 0.22.97 - CORRECAO DA SINCRONIZACAO AHGORA

Problema observado na 0.22.96:
O login dentro do ALIYVO funcionava, mas a consulta do espelho por fetch() era
bloqueada pelo navegador (erro HTTP None).

Correcao:
- mantem a sessao oficial do portal Ahgora;
- remove a consulta via fetch() dentro da pagina;
- navega diretamente para a API do espelho com a mesma sessao/cookies;
- le o JSON renderizado pela pagina;
- navega para o detalhe mensal e extrai as batidas reais do dia;
- nao registra nenhuma batida durante sincronizacao.

Fluxo:
Ponto > Vincular / Reabrir Ahgora > entrar no portal > JA ENTREI - SINCRONIZAR.

A batida pelo ALIYVO continua exigindo clique e confirmacao explicita.
""",encoding="utf-8")

print("PATCH_AHGORA_V97=OK")
