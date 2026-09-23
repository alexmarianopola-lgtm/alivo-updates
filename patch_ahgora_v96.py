from pathlib import Path
import json
import shutil
import sys

root=Path(sys.argv[1])
main=root/"_app"/"main.py"
src=Path(__file__).resolve().parent/"ponto_module_v96.py"
dst=root/"_app"/"aliyvo_ponto.py"

text=main.read_text(encoding="utf-8")
if text.count('ALIYVO_VERSION = "0.22.95"') != 1:
    raise SystemExit("Versao base 0.22.95 nao encontrada")
text=text.replace('ALIYVO_VERSION = "0.22.95"','ALIYVO_VERSION = "0.22.96"',1)
main.write_text(text,encoding="utf-8")
shutil.copy2(src,dst)

ext=root/"EXTENSAO_PONTO_SANKHYA"
manifest_path=ext/"manifest.json"
manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"]="2.3.0"
manifest["description"]="Protege o Sankhya usando o Controle de Ponto vinculado a uma sessao oficial do Ahgora."
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

bg=ext/"background.js"
bgt=bg.read_text(encoding="utf-8")
for old in ("aliyvo-ponto-02295","aliyvo-ponto-02294","aliyvo-ponto-02293"):
    if old in bgt:
        bgt=bgt.replace(old,"aliyvo-ponto-02296")
bg.write_text(bgt,encoding="utf-8")

(root/"LEIA-ME-PONTO-02296.txt").write_text(
"""ALIYVO 0.22.96 - VINCULO OFICIAL DO AHGORA

Motivo da mudanca:
A tentativa de reproduzir o login do espelho via requisicao HTTP foi recusada pelo
Ahgora mesmo com credenciais corretas. Nesta versao o ALIYVO nao imita mais o login.

Como funciona:
1. Abra Ponto.
2. Clique VINCULAR / REABRIR AHGORA.
3. O portal oficial do Ahgora abre dentro do ALIYVO.
4. Entre normalmente no proprio site Ahgora.
5. Clique JA ENTREI - SINCRONIZAR.
6. O ALIYVO reutiliza somente a sessao/cookies oficiais e consulta
   https://app.ahgora.com.br/api-espelho/apuracao/
7. A sessao fica em LOCALAPPDATA/ALIYVO/ahgora_browser_profile e sobrevive a atualizacoes.

Seguranca:
- o ALIYVO nao le os campos digitados na janela oficial de login;
- a senha digitada no portal fica sob o motor Chromium/QtWebEngine;
- nenhuma batida ocorre ao sincronizar;
- BATER PONTO continua exigindo clique e confirmacao;
- WhatsApp e demais perfis permanecem separados.

Se a sessao expirar, basta usar VINCULAR / REABRIR AHGORA e entrar novamente.
""",encoding="utf-8")

print("PATCH_AHGORA_V96=OK")
