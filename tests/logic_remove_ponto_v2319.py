from pathlib import Path
import ast,sys
root=Path(sys.argv[1])
s=(root/'main.py').read_text(encoding='utf-8')
ast.parse(s)
assert 'ALIYVO_VERSION = "0.23.19"' in s
assert 'self.ponto_toggle.hide()' in s
assert 'self.ponto_toggle.clicked.connect(lambda: None)' in s
assert 'self._ponto_controller=None' in s
assert 'self._ponto_controller=AliyvoPontoController' not in s
assert 'QTimer.singleShot(900,self._ponto_controller.start)' not in s
print('LOGIC_REMOVE_PONTO_V2319=OK')
