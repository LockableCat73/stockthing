#!/usr/bin/env python3
"""Markdown tables for: Tic-tac-toe preflop strength, Omaha starting hands, Pineapple discards,
and the bet-sizing / SPR tables for the 5/10 game with 500 stacks.  Writes results/tables/*.md"""
import collections
import csv
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
OUT = os.path.join(RES, "tables")
R = "23456789TJQKA"


def write(name, text):
    with open(os.path.join(OUT, name + ".md"), "w") as f:
        f.write(text)


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def cname(g):
    i, j = divmod(g, 13)
    if i == j:
        return R[12 - i] * 2
    return (R[12 - i] + R[12 - j] + "s") if i < j else (R[12 - j] + R[12 - i] + "o")


def grid(cell):
    hdr = "| |" + "|".join(R[12 - j] for j in range(13)) + "|\n|" + "---|" * 14 + "\n"
    rows = ["|**" + R[12 - i] + "**|" + "|".join(cell(i * 13 + j) for j in range(13)) + "|" for i in range(13)]
    return hdr + "\n".join(rows) + "\n"


# ---------------------------------------------------------------- 2-card preflop
def two_card(variant):
    E = collections.defaultdict(dict)
    for r in csv.DictReader(open(os.path.join(RES, f"{variant}_preflop_equity.csv"))):
        E[int(r["players"])][int(r["class"])] = float(r["equity"])
    return E


def ttt_tables():
    E = two_card("ttt")
    H = two_card("holdem")
    for n in (2, 4, 6, 8):
        fair = 1.0 / n
        write(f"ttt_preflop_grid_N{n}", f"Equity (%) vs {n - 1} random hands, everyone to showdown. Fair share = {100 * fair:.1f}%. "
              "Bold = at least 1.5x fair share.\n\n" +
              grid(lambda g: (f"**{100 * E[n][g]:.0f}**" if E[n][g] >= 1.5 * fair else f"{100 * E[n][g]:.0f}")))
    rows = []
    for t, f in (("pocket pairs", lambda g: g // 13 == g % 13), ("suited", lambda g: g // 13 < g % 13),
                 ("offsuit", lambda g: g // 13 > g % 13)):
        gs = [g for g in range(169) if f(g)]
        rows.append([t] + [f"{100 * np.mean([E[n][g] for g in gs]):.1f}% / {100 * np.mean([H[n][g] for g in gs]):.1f}%"
                           for n in (2, 4, 6, 8)])
    write("ttt_vs_holdem_types", md_table(["Hand type", "2 players", "4 players", "6 players", "8 players"], rows) +
          "\n(Tic-tac-toe / Hold'em average equity)\n")
    order = sorted(range(169), key=lambda g: -E[6][g])
    rows = [[k + 1, cname(g)] + [f"{100 * E[n][g]:.1f}" for n in (2, 3, 4, 5, 6, 7, 8, 9)] for k, g in enumerate(order)]
    write("ttt_preflop_all", md_table(["Rank (6p)", "Hand"] + [f"{n}p" for n in range(2, 10)], rows))


# ---------------------------------------------------------------- Omaha
SUITN = ["double-suited", "single-suited", "rainbow", "three of one suit", "four of one suit"]
PAIRN = ["no pair", "one pair", "two pair", "trips", "quads"]
CONNN = ["rundown (4 ranks within 4, e.g. 9876)", "one-gap rundown (within 5, e.g. 9865)",
         "within 6 (e.g. 9864)", "3 cards within a 5-window", "disconnected"]


def omaha_tables():
    named = {}
    for n in (2, 4, 6):
        p = os.path.join(RES, f"omaha_named_N{n}.csv")
        if os.path.exists(p):
            for r in csv.DictReader(open(p)):
                named.setdefault(r["hand"], {})[n] = float(r["equity"])

    def pretty(h):
        cards = [h[i:i + 2] for i in range(0, 8, 2)]
        suits = collections.Counter(c[1] for c in cards)
        sc = sorted(suits.values(), reverse=True)
        tag = "ds" if sc == [2, 2] else "ss" if sc[:2] == [2, 1] else "rainbow" if sc == [1, 1, 1, 1] else \
            "3-suited" if sc[0] == 3 else "mono"
        return f"{''.join(c[0] for c in cards)} {tag} ({h})"
    rows = []
    for h, d in sorted(named.items(), key=lambda kv: -kv[1].get(6, 0)):
        rows.append([pretty(h)] + [f"{100 * d[n]:.1f}%" if n in d else "" for n in (2, 4, 6)] +
                    [f"{d.get(6, 0) * 6:.2f}x" if 6 in d else ""])
    write("omaha_named", md_table(["Hand", "Heads-up", "4 players", "6 players", "6p vs fair share"], rows))

    for n in (4, 6, 8):
        p = os.path.join(RES, f"omaha_features_N{n}.csv")
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            continue
        rows = list(csv.DictReader(open(p)))
        fair = 1.0 / n

        def agg(key):
            g = collections.defaultdict(lambda: [0.0, 0.0])
            for r in rows:
                k = key(r)
                if k is None:
                    continue
                g[k][0] += float(r["count"])
                g[k][1] += float(r["share"])
            return g
        tot = sum(float(r["count"]) for r in rows)
        out = [f"Fair share with {n} players = {100 * fair:.1f}%. Index = equity / fair share.\n"]
        for title, key, names in (("By suits", lambda r: int(r["suit"]), SUITN),
                                  ("By pairs", lambda r: int(r["pair"]), PAIRN),
                                  ("By connectedness (unpaired hands)", lambda r: int(r["conn"]) if r["pair"] == "0" else None, CONNN),
                                  ("Ace suited to another card?", lambda r: int(r["acesuited"]), ["no", "yes"]),
                                  ("Number of T-A cards", lambda r: int(r["broadway"]), ["0", "1", "2", "3", "4"])):
            g = agg(key)
            out.append(f"\n**{title}**\n")
            out.append(md_table(["Feature", "Frequency", "Equity", "Index"],
                                [[names[k], f"{100 * v[0] / tot:.1f}%", f"{100 * v[1] / v[0]:.1f}%", f"{v[1] / v[0] / fair:.2f}"]
                                 for k, v in sorted(g.items())]))
        # combined: suits x connectedness for unpaired, suits x pair
        g = agg(lambda r: (int(r["suit"]), int(r["conn"])) if r["pair"] == "0" else None)
        out.append("\n**Unpaired hands: suits x connectedness (index vs fair share)**\n")
        hdr = ["Connectedness"] + SUITN[:3]
        rws = [[CONNN[c]] + [f"{g[(s, c)][1] / g[(s, c)][0] / fair:.2f}" if g[(s, c)][0] > 0 else "" for s in range(3)] for c in range(5)]
        out.append(md_table(hdr, rws))
        g = agg(lambda r: (int(r["suit"]), int(r["pair"])))
        out.append("\n**Pairs x suits (index vs fair share)**\n")
        rws = [[PAIRN[p]] + [f"{g[(s, p)][1] / g[(s, p)][0] / fair:.2f}" if g[(s, p)][0] > 1000 else "" for s in range(3)] for p in range(3)]
        out.append(md_table(["Pairs"] + SUITN[:3], rws))
        write(f"omaha_features_N{n}", "\n".join(out))


# ---------------------------------------------------------------- Pineapple
def parse3(s):
    return [(R.index(s[i]), s[i + 1]) for i in (0, 2, 4)]


def kname(a, b):
    (r1, s1), (r2, s2) = sorted([a, b], reverse=True)
    if r1 == r2:
        return R[r1] * 2
    return R[r1] + R[r2] + ("s" if s1 == s2 else "o")


def load_pine(n):
    out = []
    for r in csv.DictReader(open(os.path.join(RES, f"pineapple_discard_N{n}.csv"))):
        cs = parse3(r["cards"])
        eq = [float(r[f"eq_drop{k}"]) for k in range(3)]
        out.append((r["cards"], cs, int(r["combos"]), eq))
    return out


def pval(r):
    return r + 2 + (2 if r == 12 else 0)     # 2..9 face, T=10 J=11 Q=12 K=13, A=16


def point_score(k, p):
    (a, sa), (b, sb) = sorted(k, reverse=True)
    g = a - b
    return pval(a) + p["lo"] * pval(b) + (p["su"] if sa == sb else 0) + {1: p["g1"], 2: p["g2"], 3: p["g3"]}.get(g, 0)


BANDS = {"2-3 players": dict(lo=0.75, su=3, g1=3, g2=3, g3=2),
         "4-6 players": dict(lo=0.5, su=5, g1=6, g2=4, g3=3),
         "7-9 players": dict(lo=0.5, su=8, g1=8, g2=6, g3=3)}


def full_rule(cs, n):
    """The complete recommended discard rule; returns index of card to drop."""
    ranks = [c[0] for c in cs]
    if len(set(ranks)) == 1:
        return 0
    if len(set(ranks)) == 2:
        P = max(set(ranks), key=ranks.count)
        ki = [i for i in range(3) if ranks[i] != P][0]
        pis = [i for i in range(3) if i != ki]
        su = [i for i in pis if cs[i][1] == cs[ki][1]]
        small = P <= 3          # 22-55
        if su and cs[ki][0] == 12 and small:
            return [i for i in pis if i != su[0]][0]          # keep A-x suited
        if su and cs[ki][0] == 11 and P <= 1 and 3 <= n <= 5:
            return [i for i in pis if i != su[0]][0]          # 22/33 + suited K at 3-5 players: coin flip
        return ki
    band = "2-3 players" if n <= 3 else "4-6 players" if n <= 6 else "7-9 players"
    p = BANDS[band]
    return max(range(3), key=lambda d: point_score([c for i, c in enumerate(cs) if i != d], p))


def pineapple_tables():
    # 1. pair + odd card
    rows = []
    for n in range(2, 10):
        data = load_pine(n)
        cells = []
        for P in range(0, 6):
            sbeat, obeat = [], []
            for _, cs, w, eq in data:
                rk = [c[0] for c in cs]
                if len(set(rk)) != 2 or rk.count(P) != 2:
                    continue
                ki = [i for i in range(3) if rk[i] != P][0]
                pis = [i for i in range(3) if i != ki]
                su = [i for i in pis if cs[i][1] == cs[ki][1]]
                if su:
                    other = [i for i in pis if i != su[0]][0]
                    if eq[other] > eq[ki] + 0.001:
                        sbeat.append(R[cs[ki][0]])
                elif max(eq[pis[0]], eq[pis[1]]) > eq[ki] + 0.001:
                    obeat.append(R[cs[ki][0]] + "(off)")
            cells.append(" ".join(sorted(set(sbeat), key=R.index, reverse=True) + sorted(set(obeat))) or "keep pair")
        rows.append([n] + cells)
    write("pineapple_pair_rule", md_table(["Players"] + [R[P] * 2 for P in range(0, 6)], rows) +
          "\nCells list the odd cards (suited to one of the pair cards) for which you should break the pair and keep "
          "that suited two-card hand instead. 66 and above: always keep the pair at every table size.\n")

    # 2. accuracy of the rules
    rows = []
    for n in range(2, 10):
        data = load_pine(n)
        tot = loss = ok = 0.0
        loss2 = 0.0
        for _, cs, w, eq in data:
            d = full_rule(cs, n)
            l = max(eq) - eq[d]
            tot += w
            loss += w * l
            ok += w * (l <= 0.002)
            # naive "keep the two highest cards" rule for comparison
            rk = [c[0] for c in cs]
            if len(set(rk)) == 2:
                P = max(set(rk), key=rk.count)
                dn = [i for i in range(3) if rk[i] != P][0]
            else:
                dn = min(range(3), key=lambda i: rk[i])
            loss2 += w * (max(eq) - eq[dn])
        avg_best = sum(w * max(eq) for _, _, w, eq in data) / tot
        rows.append([n, f"{100 * ok / tot:.1f}%", f"{100 * loss / tot:.3f}", f"{100 * loss2 / tot:.2f}",
                     f"{100 * avg_best:.2f}% (fair {100 / n:.1f}%)"])
    write("pineapple_rule_accuracy", md_table(
        ["Players", "Rule picks a discard within 0.2% of the best", "Avg equity lost by the rule (% pts)",
         "Avg equity lost by 'keep the two highest cards' (% pts)", "Avg equity with perfect discards"], rows))

    # 3. keep-priority charts (average equity of each kept 2-card hand across all contexts)
    for n in (2, 4, 6, 9):
        data = load_pine(n)
        acc = collections.defaultdict(lambda: [0.0, 0.0])
        for _, cs, w, eq in data:
            keeps = [kname(cs[1], cs[2]), kname(cs[0], cs[2]), kname(cs[0], cs[1])]
            for e, k in zip(eq, keeps):
                acc[k][0] += w * e
                acc[k][1] += w
        score = {k: a / b for k, (a, b) in acc.items()}
        order = sorted(score, key=lambda k: -score[k])
        rank = {k: i + 1 for i, k in enumerate(order)}
        write(f"pineapple_keep_rank_N{n}",
              f"Rank of every kept two-card hand at {n} players (1 = best), by average equity when kept. "
              "Equity of the hand in brackets.\n\n" +
              grid(lambda g: f"{rank[cname(g)]}"))

    # 4. worked examples
    examples = ["2c2dAc", "2c2dAh", "5c5dAc", "5c5dKc", "6c6dAc", "7c7dAc", "3c3dKc", "AcKdQd", "AcKd7c", "AcKd7h",
                "Kc9c8d", "QcJd9d", "Ac7c6d", "Ac7d6d", "8c7c2d", "8c7d2c", "Tc9d4h", "AcAdKc", "KcQd5c", "JcTc4h",
                "Ac5d4d", "9c8d7h", "Ac2c9d", "Kc7d6d"]
    D = {n: {cards: (cs, eq) for cards, cs, w, eq in load_pine(n)} for n in (2, 4, 6, 9)}

    def canon(s):
        # find class whose canonical cards equal the example under suit relabelling
        cs = parse3(s)
        perms = []
        import itertools
        for p in itertools.permutations("cdhs"):
            m = dict(zip("cdhs", p))
            cand = sorted([(r, m[su]) for r, su in cs], key=lambda x: (x[0], "cdhs".index(x[1])), reverse=True)
            perms.append(cand)
        return perms
    rows = []
    for ex in examples:
        line = [ex]
        for n in (2, 4, 6, 9):
            hit = None
            for cards, (cs, eq) in D[n].items():
                if sorted(cs) in [sorted(p) for p in canon(ex)]:
                    hit = (cs, eq)
                    break
            if not hit:
                line.append("?")
                continue
            cs, eq = hit
            # map back to example cards by rank/suit pattern: describe kept hands by name
            keeps = [kname(cs[1], cs[2]), kname(cs[0], cs[2]), kname(cs[0], cs[1])]
            o = sorted(zip(eq, keeps), reverse=True)
            line.append(f"**{o[0][1]}** {100 * o[0][0]:.1f} · {o[1][1]} {100 * o[1][0]:.1f} · {o[2][1]} {100 * o[2][0]:.1f}")
        rows.append(line)
    write("pineapple_examples", md_table(["Your 3 cards", "2 players", "4 players", "6 players", "9 players"], rows) +
          "\nEach cell: the three possible kept hands, best first, with showdown equity (%) vs the field. "
          "(The suits shown in kept-hand names are relative: 's' = the two kept cards share a suit.)\n")


# ---------------------------------------------------------------- sizing / SPR for 5/10, 500 stacks
def sizing_tables():
    rows = []
    for n in range(2, 10):
        pot = 10 * n
        stack = 490
        spr = stack / pot
        # geometric bet fraction to get all-in over k streets heads-up after the flop:
        g = [((1 + 2 * spr) ** (1 / k) - 1) / 2 for k in (3, 2, 1)]
        rows.append([n, f"${pot}", f"${stack}", f"{spr:.1f}", f"{100 * g[0]:.0f}%", f"{100 * g[1]:.0f}%", f"{100 * g[2]:.0f}%"])
    write("variant_spr", md_table(["Players (all post 10)", "Pot on the flop", "Behind", "SPR",
                                   "Pot-fraction to get all-in over 3 streets", "over 2 streets", "1 street (shove)"], rows) +
          "\nGeometric sizing assumes one caller per street; with more callers the pot grows faster, so the same fraction gets the money in sooner.\n")
    rows = []
    for f in (0.25, 0.33, 0.5, 0.66, 0.75, 1.0, 1.5, 2.0):
        need = f / (1 + 2 * f)
        mdf = 1 / (1 + f)
        bluff = f / (1 + 2 * f)
        rows.append([f"{int(round(100 * f))}% pot", f"{100 * need:.0f}%", f"{100 * mdf:.0f}%", f"{100 * bluff:.0f}%",
                     f"{(1 - bluff) / bluff:.1f} : 1", f"{100 * (1 - (1 - mdf) ** 0.5):.0f}% each", f"{100 * (1 - (1 - mdf) ** (1 / 3)):.0f}% each"])
    write("bet_math", md_table(["Bet size", "Caller needs equity", "MDF (heads-up)", "River bluff share of betting range",
                                "Value : bluff", "MDF per player, 2 opponents", "MDF per player, 3 opponents"], rows))


if __name__ == "__main__":
    ttt_tables()
    omaha_tables()
    pineapple_tables()
    sizing_tables()
    print("ok")
