from pathlib import Path
import json
import shutil
import sys

root=Path(sys.argv[1])
main=root/"_app"/"main.py"
src=Path(__file__).resolve().parent/"ponto_module_v95.py"
dst=root/"_app"/"aliyvo_ponto.py"

text=main.read_text(encoding="utf-8")
if text.count('ALIYVO_VERSION = "0.22.94"') != 1:
    raise SystemExit("Versao base 0.22.94 nao encontrada")
text=text.replace('ALIYVO_VERSION = "0.22.94"','ALIYVO_VERSION = "0.22.95"',1)
main.write_text(text,encoding="utf-8")
shutil.copy2(src,dst)

ext=root/"EXTENSAO_PONTO_SANKHYA"
manifest_path=ext/"manifest.json"
manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"]="2.2.0"
manifest["description"]="Protege o Sankhya usando o Controle de Ponto sincronizado com o espelho atual do Ahgora."
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

bg=ext/"background.js"
bgt=bg.read_text(encoding="utf-8")
for old in ("aliyvo-ponto-02294","aliyvo-ponto-02293"):
    if old in bgt:
        bgt=bgt.replace(old,"aliyvo-ponto-02295")
bg.write_text(bgt,encoding="utf-8")

(root/"LEIA-ME-PONTO-02295.txt").write_text(
"""ALIYVO 0.22.95 - AHGORA ATUAL

Correcao principal:
O endpoint antigo /externo/getApuracao passou a responder "deprecated".
Esta versao deixa de usa-lo.

Sincronizacao:
1. Faz login web no Ahgora usando empresa, matricula e senha salvas com DPAPI.
2. Inicializa a sessao atual app.ahgora.com.br.
3. Consulta /api-espelho/apuracao/.
4. Consulta a referencia mensal retornada pela propria API.
5. Le as batidas reais do dia e atualiza o Controle de Ponto.

Batida Online:
- Usa o fluxo atual de dispositivo do Ahgora.
- Ativa/reutiliza identidade de dispositivo.
- Obtem token e chave publica.
- Criptografa a senha em RSA PKCS#1 v1.5 antes do envio.
- A batida somente ocorre apos clique + confirmacao do usuario.
- Nunca existe batida automatica por horario.

Seguranca:
- senha permanece protegida por Windows DPAPI;
- senha nunca e gravada no diagnostico;
- nenhum ponto e criado durante a sincronizacao;
- o botao de bater ponto exige confirmacao explicita.

Se a empresa tiver regra adicional de localizacao, foto ou dispositivo, o Ahgora
pode recusar a batida direta; nesse caso o erro e mostrado e nenhuma batida e
considerada confirmada.
""",encoding="utf-8")

print("PATCH_AHGORA_V95=OK")
