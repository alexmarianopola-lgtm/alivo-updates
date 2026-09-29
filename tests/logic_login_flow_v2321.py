from pathlib import Path
import ast,sys,re
root=Path(sys.argv[1])
main=(root/'main.py').read_text(encoding='utf-8')
s=(root/'aliyvo_ponto.py').read_text(encoding='utf-8')
ast.parse(main); ast.parse(s)

assert 'ALIYVO_VERSION = "0.23.21"' in main
assert 'POINT_MODULE_VERSION = "0.23.21"' in s
assert 'maybe_auto_sync_after_login' not in s

m=re.search(r'def start_sync\(\):(.{0,2200})',s,re.S)
assert m
blk=m.group(1)
assert 'self._ahgora_sync_view' in blk
assert 'self._sync_using_view(' in blk
assert 'reason="browser_link"' in blk
assert '_sync_from_visible_ahgora_portal' not in blk

m=re.search(r'def sync_ahgora_async\(self, reason: str = "manual"\) -> None:(.{0,1800})',s,re.S)
assert m
blk=m.group(1)
assert 'self._sync_via_persistent_browser(reason=reason)' in blk
assert 'findChildren(QWebEngineView)' not in blk
assert '_sync_from_visible_ahgora_portal' not in blk

print('LOGIN_FLOW_V2321=OK')
