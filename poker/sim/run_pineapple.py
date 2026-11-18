#!/usr/bin/env python3
"""Iterate the Pineapple discard simulation to a self-consistent strategy for N = 2..9 players.

iteration 0: opponents discard at random (i.e. they hold random 2-card hands)
iteration k: opponents discard using the best-response strategy from iteration k-1
Writes results/pineapple_discard_N{n}.csv (final iteration) and prints convergence info.
"""
import csv, subprocess, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
TRIALS = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
ITERS = 3

def run(n, strat=None):
    cmd = [os.path.join(HERE, "pineapple"), "discard", str(n), str(TRIALS)] + ([strat] if strat else [])
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return list(csv.DictReader(out.splitlines()))

for n in range(2, 10):
    strat_file, prev = None, None
    for it in range(ITERS):
        rows = run(n, strat_file)
        best = {int(r["class"]): max(range(3), key=lambda k: float(r[f"eq_drop{k}"])) for r in rows}
        if prev is not None:
            changed = sum(int(r["combos"]) for r in rows if best[int(r["class"])] != prev[int(r["class"])])
            print(f"N={n} iter {it}: combos whose discard changed = {changed}/22100", flush=True)
        prev = best
        strat_file = os.path.join(RES, f"pineapple_strategy_N{n}.csv")
        with open(strat_file, "w") as f:
            for c, d in sorted(best.items()):
                f.write(f"{c},{d}\n")
    with open(os.path.join(RES, f"pineapple_discard_N{n}.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
