import os,sys,tempfile
from pathlib import Path

os.environ["QT_QPA_PLATFORM"]="offscreen"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"]="--disable-gpu --no-sandbox"
os.environ["LOCALAPPDATA"]=str(Path(tempfile.gettempdir())/"aliyvo-v98-test")
appdir=Path(sys.argv[1]); sys.path.insert(0,str(appdir))
import aliyvo_ponto as p

assert p.POINT_MODULE_VERSION=="0.22.98"
source=(appdir/"aliyvo_ponto.py").read_text(encoding="utf-8")
assert "BATER PONTO AGORA  •" in source
assert "próximo:" in source
assert "Isso pode criar uma nova batida mesmo antes do horário previsto." in source
assert "Batidas já encontradas hoje:" in source
assert "always_punch.clicked.connect(self.punch_ahgora)" in source
assert source.count('QPushButton("🟢  BATER PONTO AGORA NO AHGORA")')==0

# O botao deve estar fora do bloco "if pending:".
pos_button=source.index("always_punch = QPushButton")
pos_pending=source.index("        if pending:", pos_button)
assert pos_button < pos_pending

print("PONTO_V98_ALWAYS_VISIBLE=OK")
print("PONTO_V98_CONFIRMATION_GUARD=OK")
print("ALIYVO_V98_PUNCH_UI=OK")
