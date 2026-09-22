from pathlib import Path
import json
import shutil
import sys

root = Path(sys.argv[1])
main = root / "_app" / "main.py"
source_module = Path(__file__).resolve().parent / "ponto_module_v93.py"
target_module = root / "_app" / "aliyvo_ponto.py"

text = main.read_text(encoding="utf-8")

def one(old, new, label):
    global text
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"{label}: esperado 1, encontrado {n}")
    text = text.replace(old, new, 1)

one('ALIYVO_VERSION = "0.22.92"', 'ALIYVO_VERSION = "0.22.93"', "version")
main.write_text(text, encoding="utf-8")
shutil.copy2(source_module, target_module)

ext = root / "EXTENSAO_PONTO_SANKHYA"
if not ext.exists():
    raise SystemExit("Extensao Ponto Guard ausente na base 0.22.92 RC1")

manifest_path = ext / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"] = "2.1.0"
manifest["description"] = (
    "Protege o Sankhya usando o status real do Ahgora sincronizado pelo ALIYVO."
)
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

bg_path = ext / "background.js"
bg = bg_path.read_text(encoding="utf-8")
bg = bg.replace('const API_SECRET = "aliyvo-ponto-02292";',
                'const API_SECRET = "aliyvo-ponto-02293";')
bg_path.write_text(bg, encoding="utf-8")

popup_path = ext / "popup.js"
popup = popup_path.read_text(encoding="utf-8")
popup = popup.replace(
    'status.innerHTML=\'<span class="ok">PONTO OK</span><br>Próxima: \'+result.data.next.time+\' • \'+result.data.next.label;',
    'status.innerHTML=\'<span class="ok">PONTO OK</span><br>Próxima: \'+result.data.next.time+\' • \'+result.data.next.label'
    '+((result.data.ahgora_punches_today||[]).length?\'<br>Ahgora hoje: \'+result.data.ahgora_punches_today.join(\' • \'):\'\');'
)
popup_path.write_text(popup, encoding="utf-8")

(root / "LEIA-ME-PONTO-02293.txt").write_text(
    """ALIYVO 0.22.93 RC2 - AHGORA SINCRONIZADO

O que mudou:
- O ALIYVO pode consultar o espelho real do Ahgora.
- As batidas reais substituem confirmações locais.
- Se hoje já existem 2 batidas no Ahgora, Entrada e Saída almoço ficam verdes automaticamente.
- O Sankhya usa esse mesmo estado real.
- Há um botão "BATER PONTO AGORA NO AHGORA" dentro do ALIYVO.
- A batida NÃO é automática: exige clique e confirmação a cada registro.

Configuração:
1. Abra ALIYVO > Ponto > Ahgora.
2. Informe matrícula, senha e código da empresa.
3. Informe o código de ativação da Batida Online; se for igual ao código da empresa,
   pode deixar em branco.
4. Clique em SALVAR E SINCRONIZAR.

Segurança:
- Matrícula/senha não são gravadas nos logs.
- As credenciais ficam criptografadas com Windows DPAPI e vinculadas ao usuário Windows.
- O ALIYVO usa HTTPS para falar com ahgora.com.br.

Importante:
A sincronização e a batida usam endpoints do serviço Ahgora observados em clientes existentes,
mas não constituem uma API pública documentada para integração do colaborador. Por isso esta
é uma versão RC. Se a empresa exigir regras adicionais (localização, dispositivo autorizado,
foto ou outra validação), a batida direta pode ser recusada; nesse caso use o Ahgora oficial.
""",
    encoding="utf-8",
)

print("PATCH_AHGORA_V93=OK")
