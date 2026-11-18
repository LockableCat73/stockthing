#!/usr/bin/env python3
"""Turn the raw output of ./cats (results/cats/*.csv) into markdown tables (results/tables/*.md).

Usage: python3 analyze_cats.py
"""
import collections
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
OUT = os.path.join(RES, "tables")
os.makedirs(OUT, exist_ok=True)
NS = [2, 3, 4, 5, 6, 7, 8, 9]
SHOW_NS = [3, 4, 5, 6, 7, 8, 9]
CAT = ["High card", "Pair", "Two pair", "Trips", "Straight", "Flush", "Full house", "Quads", "Str. flush"]
RANKS = "23456789TJQKA"

HM = ["nothing", "weak pair (bottom pair / small pocket pair)", "middle pair (or pocket pair between top & 2nd card)",
      "top pair, kicker below J", "top pair, J+ kicker", "overpair", "two pair (both cards)", "trips (board pair + 1 card)",
      "set", "straight (non-nut)", "nut straight", "flush (non-nut)", "nut flush", "full house or better"]
HD = ["no draw", "gutshot", "open-ender / double gutter", "flush draw (non-nut)", "nut flush draw",
      "flush draw + straight draw"]
OM = ["nothing", "pair (not top pair)", "top pair", "overpair", "two pair (not top two)", "top two pair",
      "trips (board pair)", "bottom set", "middle set", "top set", "straight (non-nut)", "nut straight",
      "flush (non-nut)", "nut flush", "full house or better"]
OM_SD = ["", "small straight draw (1-7 outs)", "open-ender type (8-12 outs)", "wrap (13+ outs)"]
OM_FD = ["", "flush draw (non-nut)", "nut flush draw"]
TF = ["nothing", "pair with a corner card", "pocket pair", "two pair", "trips / set", "quads"]
TFD = ["no draw", "4 to a straight", "4 to a flush", "4 to a straight AND 4 to a flush"]
TT = CAT
TTD = ["no center outs to straight+", "1-3 center outs", "4-7 center outs", "8-11 center outs", "12+ center outs"]


def om_draw_name(d):
    fb, sb = divmod(d, 4)
    parts = [p for p in (OM_FD[fb], OM_SD[sb]) if p]
    return " + ".join(parts) if parts else "no draw"


NAMES = {
    "holdem": dict(fm=HM, fd=HD, tm=HM, td=HD),
    "pineapple": dict(fm=HM, fd=HD, tm=HM, td=HD),
    "omaha": dict(fm=OM, fd=None, tm=OM, td=None),
    "ttt": dict(fm=TF, fd=TFD, tm=TT, td=TTD),
}


def dname(variant, street, d):
    n = NAMES[variant]["fd" if street == "flop" else "td"]
    return om_draw_name(d) if n is None else n[d]


def load(variant, n):
    path = os.path.join(RES, "cats", f"{variant}_N{n}.csv")
    D = {k: collections.defaultdict(lambda: [0.0, 0.0]) for k in ("flop", "turn", "river", "win", "huflop", "huturn")}
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    for line in open(path):
        p = line.strip().split(",")
        t = p[0]
        if t in ("flop", "turn", "river", "huflop", "huturn"):
            D[t][(int(p[1]), int(p[2]))][0] += float(p[3])
            D[t][(int(p[1]), int(p[2]))][1] += float(p[4])
        elif t == "win":
            D[t][(int(p[1]), int(p[2]))][0] += float(p[3])
    return D


def pct(x, d=1):
    return f"{100 * x:.{d}f}%"


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def write(name, text):
    with open(os.path.join(OUT, name + ".md"), "w") as f:
        f.write(text)


def table_winners(variant, data):
    rows = []
    for n in NS:
        D = data.get(n)
        if not D:
            continue
        tot = sum(v[0] for v in D["win"].values())
        bycat = [sum(v[0] for (c, r), v in D["win"].items() if c == k) / tot for k in range(9)]
        cum = 0
        median = None
        for k in range(9):
            cum += bycat[k]
            if median is None and cum >= 0.5:
                median = CAT[k]
        strong = sum(bycat[4:])
        rows.append([n] + [pct(x) for x in bycat] + [pct(strong), median])
    return md_table(["Players"] + CAT + ["Straight+", "Median winner"], rows)


def table_made(variant, data, street):
    names = NAMES[variant]["fm" if street == "flop" else "tm"]
    rows = []
    D6 = data[6]
    tot6 = sum(v[0] for v in D6[street].values())
    for m, nm in enumerate(names):
        freq = sum(v[0] for (a, b), v in D6[street].items() if a == m) / tot6
        if freq == 0:
            continue
        cells = []
        for n in SHOW_NS:
            D = data.get(n)
            if not D:
                cells.append("")
                continue
            c = sum(v[0] for (a, b), v in D[street].items() if a == m)
            s = sum(v[1] for (a, b), v in D[street].items() if a == m)
            cells.append(pct(s / c) if c > 200 else "")
        rows.append([nm, pct(freq, 2)] + cells)
    return md_table(["Hand", "How often (6p)"] + [f"{n} players" for n in SHOW_NS], rows)


def table_draws(variant, data, street, made_set, label):
    rows = []
    D6 = data[6]
    tot6 = sum(v[0] for v in D6[street].values())
    draws = sorted({b for (a, b) in D6[street] if a in made_set})
    for d in draws:
        c6 = sum(v[0] for (a, b), v in D6[street].items() if a in made_set and b == d)
        if c6 / tot6 < 0.0003:
            continue
        cells = []
        for n in SHOW_NS:
            D = data.get(n)
            if not D:
                cells.append("")
                continue
            c = sum(v[0] for (a, b), v in D[street].items() if a in made_set and b == d)
            s = sum(v[1] for (a, b), v in D[street].items() if a in made_set and b == d)
            cells.append(pct(s / c) if c > 200 else "")
        rows.append([dname(variant, street, d), pct(c6 / tot6, 2)] + cells)
    return f"_{label}_\n\n" + md_table(["Draw", "How often (6p)"] + [f"{n} players" for n in SHOW_NS], rows)


def table_grid(variant, data, street, n=6, minfreq=0.0005):
    """made x draw equity grid at n players (cells with enough frequency)."""
    D = data[n]
    names = NAMES[variant]["fm" if street == "flop" else "tm"]
    tot = sum(v[0] for v in D[street].values())
    draws = sorted({b for (a, b) in D[street]})
    useful = [d for d in draws if sum(v[0] for (a, b), v in D[street].items() if b == d) / tot > 0.002]
    rows = []
    for m, nm in enumerate(names):
        cells = []
        any_ = False
        for d in useful:
            c, s = D[street].get((m, d), [0, 0])
            if c / tot >= minfreq:
                cells.append(pct(s / c, 0))
                any_ = True
            else:
                cells.append("")
        if any_:
            rows.append([nm] + cells)
    return md_table(["Made hand \\ draw"] + [dname(variant, street, d) for d in useful], rows)


def table_river(variant, data, n):
    D = data[n]
    rows = []
    for c in range(9):
        cells = []
        tot_c = sum(v[0] for (a, r), v in D["river"].items() if a == c)
        if tot_c < 500:
            continue
        for r in range(12, -1, -1):
            cnt, s = D["river"].get((c, r), [0, 0])
            cells.append(pct(s / cnt, 0) if cnt >= 300 else "")
        s_all = sum(v[1] for (a, r), v in D["river"].items() if a == c)
        rows.append([CAT[c], pct(s_all / tot_c)] + cells)
    hdr = ["River hand", "Avg"] + [RANKS[r] for r in range(12, -1, -1)]
    return md_table(hdr, rows)


def hu_made_matrix(variant, data, street):
    D = data["hu"]
    names = NAMES[variant]["fm" if street == "flop" else "tm"]
    key = "hu" + street
    agg = collections.defaultdict(lambda: [0.0, 0.0])
    for (ka, kb), (c, s) in D[key].items():
        agg[(ka // 16, kb // 16)][0] += c
        agg[(ka // 16, kb // 16)][1] += s
    tot = sum(v[0] for v in agg.values())
    present = [m for m in range(len(names)) if sum(v[0] for (a, b), v in agg.items() if a == m) / tot > 0.001]
    rows = []
    for a in present:
        cells = []
        for b in present:
            c, s = agg[(a, b)]
            cells.append(pct(s / c, 0) if c > 300 else "")
        rows.append([names[a]] + cells)
    short = [names[b].split(" (")[0] for b in present]
    return md_table(["Hero \\ villain"] + short, rows)


def hu_archetypes(variant, data, archetypes, street="flop"):
    """archetypes: list of (label, predicate(made, draw)). Uses heads-up data pooled over table sizes."""
    D = data["hu"]
    key = "hu" + street
    groups = {}
    for (ka, kb), (c, s) in D[key].items():
        for i, (la, fa) in enumerate(archetypes):
            if not fa(ka // 16, ka % 16):
                continue
            for j, (lb, fb) in enumerate(archetypes):
                if fb(kb // 16, kb % 16):
                    g = groups.setdefault((i, j), [0.0, 0.0])
                    g[0] += c
                    g[1] += s
    rows = []
    for i, (la, _) in enumerate(archetypes):
        cells = []
        for j in range(len(archetypes)):
            c, s = groups.get((i, j), (0, 0))
            cells.append(pct(s / c, 0) if c > 200 else "")
        rows.append([la] + cells)
    return md_table(["Hero \\ villain"] + [chr(65 + j) for j in range(len(archetypes))], rows) + \
        "\n" + "  ".join(f"**{chr(65 + j)}** = {la}" for j, (la, _) in enumerate(archetypes)) + "\n"


def main():
    for variant in ("holdem", "pineapple", "omaha", "ttt"):
        data = {n: load(variant, n) for n in NS}
        data = {n: d for n, d in data.items() if d}
        # heads-up equities do not depend on how many other (random, dead) hands were dealt,
        # so pool the heads-up tables of every table size into data["hu"]
        pooled = {k: collections.defaultdict(lambda: [0.0, 0.0]) for k in ("huflop", "huturn")}
        for d in data.values():
            for k in pooled:
                for key, (c, s) in d[k].items():
                    pooled[k][key][0] += c
                    pooled[k][key][1] += s
        data["hu"] = pooled
        write(f"{variant}_winners", table_winners(variant, data))
        write(f"{variant}_flop_made", table_made(variant, data, "flop"))
        write(f"{variant}_turn_made", table_made(variant, data, "turn"))
        write(f"{variant}_flop_grid6", table_grid(variant, data, "flop"))
        write(f"{variant}_turn_grid6", table_grid(variant, data, "turn"))
        for n in (4, 6, 8):
            if n in data and n != "hu":
                write(f"{variant}_river_N{n}", table_river(variant, data, n))
        write(f"{variant}_hu_flop", hu_made_matrix(variant, data, "flop"))
        write(f"{variant}_hu_turn", hu_made_matrix(variant, data, "turn"))
        if variant in ("holdem", "pineapple"):
            write(f"{variant}_flop_draws", table_draws(variant, data, "flop", {0}, "Draws with no pair (equity to the river vs the whole field)"))
            write(f"{variant}_turn_draws", table_draws(variant, data, "turn", {0}, "Draws with no pair (one card to come)"))
        if variant == "omaha":
            write("omaha_flop_draws", table_draws(variant, data, "flop", {0, 1}, "Draws with at most a non-top pair"))
            write("omaha_turn_draws", table_draws(variant, data, "turn", {0, 1}, "Draws with at most a non-top pair (one card to come)"))
            arche = [
                ("top set, no draw", lambda m, d: m == 9 and d == 0),
                ("bottom set, no draw", lambda m, d: m == 7 and d == 0),
                ("top two pair", lambda m, d: m == 5),
                ("nut straight, no redraw", lambda m, d: m == 11 and d == 0),
                ("non-nut straight", lambda m, d: m == 10),
                ("wrap 13+ outs (no pair)", lambda m, d: m <= 1 and d % 4 == 3 and d // 4 == 0),
                ("nut flush draw only", lambda m, d: m <= 1 and d == 8),
                ("NFD + 8+ straight outs", lambda m, d: m <= 1 and d in (10, 11)),
                ("top pair, no draw", lambda m, d: m == 2 and d == 0),
                ("nut flush", lambda m, d: m == 13),
            ]
            write("omaha_hu_archetypes_flop", hu_archetypes(variant, data, arche, "flop"))
        if variant == "ttt":
            write("ttt_flop_draws", table_draws(variant, data, "flop", {0, 1}, "Flop draws for hands with at most a corner pair"))
            write("ttt_turn_draws", table_draws(variant, data, "turn", {0, 1, 2, 3}, "Turn: hands of trips or worse, by number of center cards that give a straight+"))
    print("tables written to", OUT)


if __name__ == "__main__":
    main()
