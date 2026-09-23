from pathlib import Path
import json
import shutil
import sys

root=Path(sys.argv[1])
main=root/"_app"/"main.py"
src=Path(__file__).resolve().parent/"ponto_module_v94.py"
dst=root/"_app"/"aliyvo_ponto.py"

text=main.read_text(encoding="utf-8")
if text.count('ALIYVO_VERSION = "0.22.93"') != 1:
    raise SystemExit("Versao base 0.22.93 nao encontrada")
text=text.replace('ALIYVO_VERSION = "0.22.93"','ALIYVO_VERSION = "0.22.94"',1)
main.write_text(text,encoding="utf-8")
shutil.copy2(src,dst)

ext=root/"EXTENSAO_PONTO_SANKHYA"
manifest_path=ext/"manifest.json"
manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"]="2.1.1"
manifest["description"]="Protege o Sankhya usando a sincronizacao validada do Ahgora pelo ALIYVO."
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

bg=ext/"background.js"
bgt=bg.read_text(encoding="utf-8")
if 'aliyvo-ponto-02293' not in bgt:
    raise SystemExit("Bridge 0.22.93 nao encontrado")
bgt=bgt.replace('aliyvo-ponto-02293','aliyvo-ponto-02294')
bg.write_text(bgt,encoding="utf-8")

(root/"LEIA-ME-PONTO-02294.txt").write_text(
"""ALIYVO 0.22.94 RC3 - CORRECAO DA SINCRONIZACAO AHGORA

Esta versao corrige um problema da RC2:
uma resposta HTTP valida do Ahgora podia aparecer como "conectado" mesmo quando
o espelho retornava erro ou nenhuma batida valida.

Agora:
- respostas error/not_found deixam de aparecer como sincronizacao bem-sucedida;
- matricula e empresa retornadas sao validadas;
- o dia de hoje precisa existir no espelho;
- o painel mostra quantas batidas reais foram encontradas;
- estados locais antigos "precisa de ajuste" sao limpos quando o espelho real
  e sincronizado com sucesso;
- existe o botao DIAGNOSTICO DA SINCRONIZACAO sem exibir senha;
- a batida direta so e liberada depois de uma sincronizacao valida.

Nao clique em "BATER PONTO" para testar se voce ja registrou no Ahgora, pois isso
pode criar uma batida duplicada. Primeiro use SINCRONIZAR AGORA.
""",encoding="utf-8")
print("PATCH_AHGORA_V94=OK")
