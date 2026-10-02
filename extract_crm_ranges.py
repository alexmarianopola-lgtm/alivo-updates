from pathlib import Path
import sys
p=Path(sys.argv[1])
lines=p.read_text(encoding='utf-8',errors='replace').splitlines()
ranges=[(9060,9320),(10380,10740),(6215,6305)]
out=[]
for a,b in ranges:
    out.append(f"===== L{a}-L{b} =====")
    for i in range(a,b+1):
        if 1<=i<=len(lines):
            out.append(f"{i:06d}: {lines[i-1]}")
Path(sys.argv[2]).write_text("\n".join(out),encoding='utf-8')
