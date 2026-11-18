#!/usr/bin/env python3
"""Run ./texture for the main single-raised-pot matchups and write results/tables/holdem_texture.md"""
import csv, json, os, subprocess, collections
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
import holdem_preflop as hp

ranges = json.load(open(os.path.join(RES, "holdem_ranges.json")))
MATCHUPS = [("BTN", "BB vs BTN"), ("CO", "BTN vs CO"), ("UTG", "BB vs UTG"), ("SB", "BB vs SB")]
HI = ["A-high", "K-high", "Q-high", "J/T-high", "9-high or lower"]
SU = ["rainbow", "two-tone", "monotone"]
CO = ["dry", "connected", "very connected"]
os.makedirs(os.path.join(RES, "texture"), exist_ok=True)

def wfile(name, hands):
    p = os.path.join(RES, "texture", name + ".txt")
    s = set(hands)
    with open(p, "w") as f:
        for g in range(169):
            f.write("1\n" if hp.NAMES[g] in s else "0\n")
    return p

out = ["Preflop raiser (PFR) vs caller, single-raised pot. Equity = PFR's all-in equity on that flop; "
       "Nut% = share of the range holding two pair or better on the flop; TP+% = top pair or better; "
       "Air% = no pair and no draw. Freq = how often this texture comes up.\n"]
for opener, key in MATCHUPS:
    a = wfile(f"{opener}_open", ranges[opener]["open"])
    b = wfile(key.replace(" ", "_"), ranges[key]["call"])
    res = subprocess.run([os.path.join(HERE, "texture"), a, b, "3000000"], capture_output=True, text=True, check=True).stdout
    rows = list(csv.DictReader(res.splitlines()))
    with open(os.path.join(RES, "texture", f"{opener}_vs_{key.split()[0]}.csv"), "w") as f:
        f.write(res)
    def agg(fn):
        g = collections.defaultdict(lambda: [0.0] * 8)
        for r in rows:
            k = int(r["key"]); lab = fn(k)
            if lab is None: continue
            v = [float(r[c]) for c in ("count", "eqA", "A_strong", "B_strong", "A_toppair", "B_toppair", "A_air", "B_air")]
            for i in range(8): g[lab][i] += v[i]
        return g
    tot = sum(float(r["count"]) for r in rows)
    caller = key.split()[0]
    out.append(f"\n### {opener} open vs {caller} call\n")
    out.append(f"| Texture | Freq | PFR equity | PFR nut% | {caller} nut% | PFR TP+% | {caller} TP+% | PFR air% | {caller} air% |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    def emit(label, v):
        n = v[0]
        out.append(f"| {label} | {100*n/tot:.0f}% | **{100*v[1]/n:.0f}%** | {100*v[2]/n:.0f}% | {100*v[3]/n:.0f}% | {100*v[4]/n:.0f}% | {100*v[5]/n:.0f}% | {100*v[6]/n:.0f}% | {100*v[7]/n:.0f}% |")
    allv = [0.0] * 8
    for r in rows:
        for i, c in enumerate(("count", "eqA", "A_strong", "B_strong", "A_toppair", "B_toppair", "A_air", "B_air")):
            allv[i] += float(r[c])
    emit("**All flops**", allv)
    for lab, v in sorted(agg(lambda k: HI[k // 24] + (" paired" if (k // 12) % 2 else " unpaired")).items(), key=lambda x: -x[1][1] / x[1][0]):
        emit(lab, v)
    for lab, v in agg(lambda k: SU[(k % 12) // 4]).items():
        emit(lab, v)
    for lab, v in agg(lambda k: None if (k // 12) % 2 else CO[k % 4]).items():
        emit("unpaired, " + lab, v)
    for lab, v in agg(lambda k: None if (k // 12) % 2 else (("high (A/K/Q)" if k // 24 <= 2 else "middle/low (J and below)") + ", " + CO[k % 4] + ", " + SU[(k % 12) // 4])).items():
        emit(lab, v)
open(os.path.join(RES, "tables", "holdem_texture.md"), "w").write("\n".join(out) + "\n")
print("ok")
