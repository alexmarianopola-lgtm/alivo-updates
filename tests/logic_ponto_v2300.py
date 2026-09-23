import os,sys,tempfile
from pathlib import Path

os.environ["QT_QPA_PLATFORM"]="offscreen"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"]="--disable-gpu --no-sandbox"
os.environ["LOCALAPPDATA"]=str(Path(tempfile.gettempdir())/"aliyvo-v2300-test")
appdir=Path(sys.argv[1]); sys.path.insert(0,str(appdir))
import aliyvo_ponto as p

assert p.POINT_MODULE_VERSION=="0.23.00"
source=(appdir/"aliyvo_ponto.py").read_text(encoding="utf-8")

assert "Ctrl+Shift+9" in source
assert "_find_chrome_window" in source
assert "_send_ahgora_chrome_hotkey" in source
assert "Chrome_WidgetWin_" in source
assert "SetForegroundWindow" in source
assert "VK_CONTROL = 0x11" in source
assert "VK_SHIFT = 0x10" in source
assert "VK_9 = 0x39" in source
assert "_verify_after_chrome_punch" in source
assert "timer_12s" in source and "timer_28s" in source
assert "O ALIYVO não preencherá sua senha" in source

start=source.index("    def punch_ahgora(self) -> None:")
end=source.index("    def _verify_after_chrome_punch",start)
block=source[start:end]

# O caminho ativo nunca envia batida pela API e nunca preenche credenciais.
assert "_modern_punch(" not in block
assert "_legacy_modern_punch_unused(" not in block
assert "verifyIdentification" not in block
assert "activateDeviceOnLineByLoginAndPassword" not in block
assert "password" not in block.lower()
assert "senha" in block.lower()  # apenas texto explicativo
assert "keybd_event" not in block  # envio do atalho fica isolado no helper
assert "_send_ahgora_chrome_hotkey()" in block

# A verificacao posterior somente chama sincronizacao do espelho.
vstart=source.index("    def _verify_after_chrome_punch")
vend=source.index("    def _on_punch_finished",vstart)
verify=source[vstart:vend]
assert "sync_ahgora_async" in verify
assert "verifyIdentification" not in verify
assert "_modern_punch(" not in verify

print("PONTO_02300_CHROME_SHORTCUT=OK")
print("PONTO_02300_NO_AUTOMATIC_PUNCH=OK")
print("PONTO_02300_AUTO_VERIFY=OK")
print("ALIYVO_02300_PUNCH_BRIDGE=OK")
