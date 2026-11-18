#!/usr/bin/env python3
"""Fill every <!--T:name--> ... <!--/T--> block in poker/*.md with results/tables/name.md (idempotent)."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
TAB = os.path.join(ROOT, "results", "tables")
pat = re.compile(r"<!--T:([\w\-]+)-->.*?<!--/T-->", re.S)
missing = []
def fill(m):
    name = m.group(1)
    p = os.path.join(TAB, name + ".md")
    if not os.path.exists(p):
        missing.append(name); return m.group(0)
    return f"<!--T:{name}-->\n" + open(p).read().strip() + "\n<!--/T-->"
for fn in sorted(os.listdir(ROOT)):
    if fn.endswith(".md"):
        p = os.path.join(ROOT, fn)
        s = open(p).read()
        s2 = pat.sub(fill, s)
        if s2 != s:
            open(p, "w").write(s2)
            print("filled", fn)
if missing:
    print("MISSING tables:", ", ".join(sorted(set(missing)))); sys.exit(1)
