from pathlib import Path
import ast,sys
root=Path(sys.argv[1])
s=(root/'main.py').read_text(encoding='utf-8')
ast.parse(s)
assert 'ALIYVO_VERSION = "0.23.20"' in s
assert 'self._ponto_controller=AliyvoPontoController(self,self.ponto_toggle)' in s
assert 'QTimer.singleShot(900,self._ponto_controller.start)' in s
assert 'self.ponto_toggle.clicked.connect(' in s
print('RESTORE_POINT_V2320=OK')
