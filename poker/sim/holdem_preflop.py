#!/usr/bin/env python3
"""Hold'em preflop analysis built on the simulated equity data.

Inputs  (from ./preflop):  results/holdem_hu_matrix.csv, results/holdem_preflop_equity.csv
Outputs (markdown):        results/tables/holdem_*.md, results/holdem_ranges.json

1. Exact card-removal combo weights between the 169 classes.
2. Heads-up push/fold Nash equilibrium (SB shove / BB call) for 1.5..25 BB by fictitious play.
3. Re-shove (3-bet all-in) equilibrium vs a 2.5x open for 10..25 BB stacks.
4. Opening charts for 9 seats at 50 BB, and defence charts (3-bet / call / fold) derived from
   equity-vs-range with pot odds and an explicit equity-realisation model.
"""
import csv
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
OUT = os.path.join(RES, "tables")
os.makedirs(OUT, exist_ok=True)
R = "23456789TJQKA"


# ------------------------------------------------------------------ classes
def cname(g):
    i, j = divmod(g, 13)
    if i == j:
        return R[12 - i] * 2
    if i < j:
        return R[12 - i] + R[12 - j] + "s"
    return R[12 - j] + R[12 - i] + "o"


NAMES = [cname(g) for g in range(169)]
IDX = {n: g for g, n in enumerate(NAMES)}


def cls_of(c1, c2):
    r1, r2 = c1 >> 2, c2 >> 2
    if r1 < r2:
        r1, r2, c1, c2 = r2, r1, c2, c1
    i, j = 12 - r1, 12 - r2
    if r1 == r2:
        return i * 13 + i
    if (c1 & 3) == (c2 & 3):
        return i * 13 + j
    return j * 13 + i


COMBOS = [(a, b) for a in range(52) for b in range(a + 1, 52)]
CCLS = np.array([cls_of(a, b) for a, b in COMBOS])
NCOMB = np.bincount(CCLS, minlength=169).astype(float)


def removal_weights():
    """W[i][j] = expected number of class-j combos available given a random class-i hero combo."""
    cards = np.zeros((1326, 52), bool)
    for k, (a, b) in enumerate(COMBOS):
        cards[k, a] = cards[k, b] = True
    ok = ~((cards.astype(np.int32) @ cards.T.astype(np.int32)) > 0)
    W = np.zeros((169, 169))
    for i in range(169):
        rows = ok[CCLS == i]
        W[i] = np.array([rows[:, CCLS == j].sum() for j in range(169)]) / rows.shape[0]
    return W


def load_matrix():
    M = np.loadtxt(os.path.join(RES, "holdem_hu_matrix.csv"), delimiter=",")
    return M


def load_multi():
    E = {}
    for r in csv.DictReader(open(os.path.join(RES, "holdem_preflop_equity.csv"))):
        E[(int(r["class"]), int(r["players"]))] = float(r["equity"])
    return E


# ------------------------------------------------------------- range parsing
def parse_range(text):
    """'77+, ATs+, A5s-A2s, KTs+, AJo+, KQo, T9s' -> weight vector (169)."""
    w = np.zeros(169)
    for tok in [t.strip() for t in text.replace(" ", "").split(",") if t.strip()]:
        if "-" in tok:
            a, b = tok.split("-")
            hi, lo = sorted([a, b], key=lambda x: (R.index(x[0]), R.index(x[1])), reverse=True)
            if hi[0] == hi[1]:
                for r in range(R.index(lo[0]), R.index(hi[0]) + 1):
                    w[IDX[R[r] * 2]] = 1
            else:
                suf = hi[2]
                for r in range(R.index(lo[1]), R.index(hi[1]) + 1):
                    w[IDX[hi[0] + R[r] + suf]] = 1
        elif tok.endswith("+"):
            t = tok[:-1]
            if t[0] == t[1]:
                for r in range(R.index(t[0]), 13):
                    w[IDX[R[r] * 2]] = 1
            else:
                suf = t[2]
                for r in range(R.index(t[1]), R.index(t[0])):
                    w[IDX[t[0] + R[r] + suf]] = 1
        else:
            w[IDX[tok]] = 1
    return w


def range_pct(w):
    return 100 * (w * NCOMB).sum() / 1326


# --------------------------------------------------------------- equity calcs
def eq_vs_range(M, W, rng):
    """equity of every class vs a weighted range, with card removal."""
    num = (M * W * rng[None, :]).sum(1)
    den = (W * rng[None, :]).sum(1)
    return np.where(den > 0, num / np.maximum(den, 1e-12), 0.5)


# --------------------------------------------------------------- push / fold
def pushfold(M, W, S, iters=3000):
    """HU: SB (posted 0.5) shoves S bb or folds; BB (posted 1) calls or folds. Fictitious play."""
    prior = NCOMB / NCOMB.sum()
    push = np.ones(169)
    call = np.ones(169)
    avg_p = np.zeros(169)
    avg_c = np.zeros(169)
    for t in range(1, iters + 1):
        # BB best response to push
        wp = W * push[None, :]                       # weights of SB hands given BB hand i
        fp = wp.sum(1)
        eq_bb = np.where(fp > 0, (M * wp).sum(1) / np.maximum(fp, 1e-12), 0.5)
        # eq_bb[i] = equity of BB class i vs SB pushing range: M[i][j] is i's equity vs j
        ev_call = eq_bb * 2 * S - S                  # relative to posting nothing more: lose S or win S
        ev_fold = -1.0
        call_br = (ev_call > ev_fold).astype(float)
        # SB best response to call
        wc = W * call[None, :]
        fc = wc.sum(1)                               # number of BB combos that call
        tot = W.sum(1)
        eq_sb = np.where(fc > 0, (M * wc).sum(1) / np.maximum(fc, 1e-12), 0.5)
        pc = fc / tot
        ev_push = (1 - pc) * 1.0 + pc * (eq_sb * 2 * S - S)
        push_br = (ev_push > -0.5).astype(float)
        a = 1.0 / t
        avg_p = (1 - a) * avg_p + a * push_br
        avg_c = (1 - a) * avg_c + a * call_br
        push, call = avg_p, avg_c
    # final pure best responses against the converged (averaged) opponent strategies
    return push_br, call_br


def reshove(M, W, open_rng, S, opener_risk=2.5, dead=1.5, iters=2000):
    """Opener raised to 2.5bb with open_rng; hero (stack S) jams or folds; opener calls or folds.
    dead = blinds already in the pot that belong to neither player (1.5 if hero is not a blind)."""
    jam = np.ones(169)
    call = np.ones(169)
    aj = np.zeros(169)
    ac = np.zeros(169)
    for t in range(1, iters + 1):
        # opener best response: call S total (adds S-2.5) or fold (loses 2.5)
        wj = W * jam[None, :]
        fj = wj.sum(1)
        eq_o = np.where(fj > 0, (M * wj).sum(1) / np.maximum(fj, 1e-12), 0.5)
        pot = 2 * S + dead
        ev_call = eq_o * pot - S
        call_br = (ev_call > -opener_risk).astype(float) * (open_rng > 0)
        # hero best response
        wc = W * (call * open_rng)[None, :]
        wo = W * open_rng[None, :]
        fc = wc.sum(1)
        fo = wo.sum(1)
        pc = np.where(fo > 0, fc / np.maximum(fo, 1e-12), 0)
        eq_h = np.where(fc > 0, (M * wc).sum(1) / np.maximum(fc, 1e-12), 0.5)
        ev_jam = (1 - pc) * (opener_risk + dead) + pc * (eq_h * pot - S)
        jam_br = (ev_jam > 0).astype(float)
        a = 1.0 / t
        aj = (1 - a) * aj + a * jam_br
        ac = (1 - a) * ac + a * call_br
        jam, call = aj, ac
    return jam_br, call_br


def jam_vs_3bet(M, W, tb_rng, S=50.0, hero_in=2.5, vill_in=9.0, dead=1.5, iters=2000):
    """Hero opened (hero_in), villain 3-bet to vill_in with range tb_rng. Hero jams S or folds;
    villain calls or folds. EVs measured from the current decision (money already in is sunk)."""
    jam = np.ones(169)
    call = np.ones(169)
    aj = np.zeros(169)
    ac = np.zeros(169)
    pot = 2 * S + dead
    for t in range(1, iters + 1):
        wj = W * jam[None, :]
        fj = wj.sum(1)
        eq_v = np.where(fj > 0, (M * wj).sum(1) / np.maximum(fj, 1e-12), 0.5)
        call_br = ((eq_v * pot - (S - vill_in)) > 0).astype(float) * (tb_rng > 0)
        wc = W * (call * tb_rng)[None, :]
        wo = W * tb_rng[None, :]
        fc = wc.sum(1)
        fo = wo.sum(1)
        pc = np.where(fo > 0, fc / np.maximum(fo, 1e-12), 0)
        eq_h = np.where(fc > 0, (M * wc).sum(1) / np.maximum(fc, 1e-12), 0.5)
        ev = (1 - pc) * (hero_in + vill_in + dead) + pc * (eq_h * pot - (S - hero_in))
        jam_br = (ev > 0).astype(float)
        a = 1.0 / t
        aj = (1 - a) * aj + a * jam_br
        ac = (1 - a) * ac + a * call_br
        jam, call = aj, ac
    return jam_br, call_br


# ------------------------------------------------------------------- charts
OPEN_50BB = {
    # 9-handed seat names. With fewer players, drop seats from the FRONT (6-handed = LJ,HJ,CO,BTN,SB,BB).
    "UTG": "77+, ATs+, A5s, KTs+, QTs+, JTs, AJo+, KQo",
    "UTG+1": "66+, A9s+, A5s-A4s, KTs+, QTs+, JTs, T9s, AJo+, KQo",
    "MP": "55+, A8s+, A5s-A3s, K9s+, Q9s+, J9s+, T9s, 98s, ATo+, KJo+",
    "LJ": "44+, A2s+, K9s+, Q9s+, J9s+, T8s+, 98s, 87s, ATo+, KJo+, QJo",
    "HJ": "33+, A2s+, K7s+, Q8s+, J8s+, T8s+, 97s+, 87s, 76s, 65s, A9o+, KTo+, QTo+, JTo",
    "CO": "22+, A2s+, K6s+, Q8s+, J8s+, T8s+, 97s+, 86s+, 75s+, 65s, 54s, A8o+, A5o, KTo+, QTo+, JTo",
    "BTN": "22+, A2s+, K2s+, Q5s+, J7s+, T7s+, 96s+, 85s+, 75s+, 64s+, 53s+, 43s, A2o+, K8o+, Q9o+, J9o+, T8o+, 98o",
    "SB": "22+, A2s+, K2s+, Q5s+, J7s+, T7s+, 96s+, 86s+, 75s+, 64s+, 54s, A2o+, K9o+, Q9o+, J9o+, T9o",
}
SEATS = ["UTG", "UTG+1", "MP", "LJ", "HJ", "CO", "BTN", "SB", "BB"]


def realisation(g, ip):
    """Assumed share of raw equity a hand realises post-flop (explicit MODEL ASSUMPTION, not simulated).
    ip=2: big blind closing the action out of position; ip=1: cold-calling in position with players
    still to act behind (squeeze risk, multiway pots)."""
    n = NAMES[g]
    hi, lo = R.index(n[0]), R.index(n[1])
    gap = hi - lo
    if hi == lo:
        r = 0.80
    elif n.endswith("s"):
        r = 0.86 + (0.04 if gap <= 2 else 0.0)
    elif lo >= 8:                      # offsuit broadway
        r = 0.80
    elif hi == 12:                     # offsuit ace
        r = 0.74
    elif gap <= 1:
        r = 0.72
    else:
        r = 0.64
    if ip == 1:
        r = min(1.0, r + 0.06)
    if ip == 3:                        # big blind vs small-blind open: in position, closes the action
        r = min(1.05, r + 0.14)
    return r


BLUFF_PREF = ["A5s", "A4s", "A3s", "A2s", "K9s", "K8s", "K7s", "K6s", "K5s", "Q9s", "J9s", "T8s", "97s",
              "86s", "75s", "65s", "54s", "A9s", "A8s", "A7s", "A6s", "QTs", "JTs", "T9s", "98s", "87s", "76s"]


def defend(M, W, open_rng, ip, call_price, pot_after_call, value_frac=0.25, bluff_ratio=0.7,
           allow_call=True, value_eq=0.50):
    """Return (threebet, call) vectors for a hand facing an open.
    value 3-bets: best hands by equity vs the range that continues vs a 3-bet (top `value_frac` of open range)
    calls:       remaining hands with realised equity vs the whole open range above the price
    bluff 3-bets: hands just below the calling threshold with an ace or king blocker + suitedness."""
    eq_open = eq_vs_range(M, W, open_rng)
    # opener continues vs 3-bet with its strongest hands by heads-up equity vs that open range
    strength = eq_vs_range(M, W, open_rng)
    order = np.argsort(-strength)
    cum = 0
    cont = np.zeros(169)
    total = (open_rng * NCOMB).sum()
    for g in order:
        if open_rng[g] == 0:
            continue
        if cum / total >= value_frac:
            break
        cont[g] = 1
        cum += NCOMB[g]
    eq_cont = eq_vs_range(M, W, cont)
    need = call_price / pot_after_call
    real = np.array([realisation(g, ip) for g in range(169)])
    tb = (eq_cont > value_eq).astype(float)
    call = np.zeros(169)
    if allow_call:
        call = ((eq_open * real > need) & (tb == 0)).astype(float)
    # bluffs: blocker / playable suited hands in a fixed preference order (taken from the calling
    # range when calling is allowed, otherwise from hands that would fold)
    nval = (tb * NCOMB).sum()
    want = nval * bluff_ratio
    got = 0
    for n in BLUFF_PREF:
        g = IDX[n]
        if got >= want:
            break
        if tb[g] or eq_open[g] < 0.30:
            continue
        tb[g] = 2      # 2 = bluff 3-bet
        call[g] = 0
        got += NCOMB[g]
    return tb, call, eq_open


def linear3bet(M, W, open_rng, value_pct, bluff_ratio=0.4):
    """3-bet-or-fold seat: 3-bet the top `value_pct`% of hands by equity vs the open (suited bonus),
    plus blocker bluffs from BLUFF_PREF worth `bluff_ratio` of the value combos."""
    eq_open = eq_vs_range(M, W, open_rng)
    def bonus(n):
        b = 0.02 if n.endswith("s") else 0.0
        if n[0] != n[1] and R.index(n[1]) >= 8:      # two broadway cards play well
            b += 0.02
        return b
    score = eq_open + np.array([bonus(NAMES[g]) for g in range(169)])
    tb = np.zeros(169)
    cum = 0
    for g in np.argsort(-score):
        if cum >= value_pct / 100 * 1326:
            break
        tb[g] = 1
        cum += NCOMB[g]
    got = 0
    for n in BLUFF_PREF:
        g = IDX[n]
        if got >= cum * bluff_ratio:
            break
        if tb[g]:
            continue
        tb[g] = 2
        got += NCOMB[g]
    return tb, np.zeros(169), eq_open


# ---------------------------------------------------------------- rendering
def grid_md(cell):
    """cell(g) -> short string. 13x13 grid, rows = first card A..2."""
    hdr = "| |" + "|".join(R[12 - j] for j in range(13)) + "|\n|" + "---|" * 14 + "\n"
    rows = []
    for i in range(13):
        rows.append("|**" + R[12 - i] + "**|" + "|".join(cell(i * 13 + j) for j in range(13)) + "|")
    return hdr + "\n".join(rows) + "\n"


def write(name, text):
    with open(os.path.join(OUT, name + ".md"), "w") as f:
        f.write(text)


def main():
    M = load_matrix()
    E = load_multi()
    W = removal_weights()
    ranges = {}

    # ---- equity tables
    rows = []
    order = sorted(range(169), key=lambda g: -E[(g, 2)])
    hdr = "| Rank | Hand | " + " | ".join(f"{n}p" for n in range(2, 10)) + " |\n|" + "---|" * 10 + "\n"
    for k, g in enumerate(order):
        rows.append(f"| {k + 1} | {NAMES[g]} | " + " | ".join(f"{100 * E[(g, n)]:.1f}" for n in range(2, 10)) + " |")
    write("holdem_equity_all", "Equity (%) vs N-1 random hands, all-in preflop (200k deals per cell)\n\n" + hdr + "\n".join(rows) + "\n")

    # ---- push/fold
    stacks = [1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 22, 25]
    push_max = np.zeros(169)
    call_max = np.zeros(169)
    pf = {}
    for S in stacks:
        p, c = pushfold(M, W, S)
        pf[S] = (p, c)
    for g in range(169):
        # largest S such that the hand is a push (freq>0.5) at every stack <= S
        pm = 0
        for S in stacks:
            if pf[S][0][g] > 0.5:
                pm = S
            else:
                break
        cm = 0
        for S in stacks:
            if pf[S][1][g] > 0.5:
                cm = S
            else:
                break
        push_max[g], call_max[g] = pm, cm

    def fmt(x):
        return "25+" if x >= 25 else ("-" if x == 0 else (f"{x:g}"))
    txt = ("**SB shove** (heads-up or blind-vs-blind, no ante): shove if your effective stack in big blinds is at or "
           "below the number shown.\n\n" + grid_md(lambda g: fmt(push_max[g])) +
           "\n**BB call vs a SB shove**: call if the effective stack is at or below the number shown.\n\n" +
           grid_md(lambda g: fmt(call_max[g])))
    pct_rows = "| Stack (BB) | SB shoves | BB calls |\n|---|---|---|\n" + "\n".join(
        f"| {S:g} | {range_pct(pf[S][0] > 0.5):.0f}% | {range_pct(pf[S][1] > 0.5):.0f}% |" for S in stacks)
    write("holdem_pushfold", txt + "\n" + pct_rows + "\n")

    # ---- re-shove vs an open
    resh = {}
    for seat in ["UTG", "MP", "HJ", "CO", "BTN"]:
        o = parse_range(OPEN_50BB[seat])
        res_s = {}
        for S in [10, 12, 15, 18, 20, 25]:
            j, c = reshove(M, W, o, S)
            res_s[S] = (fill_pairs(j > 0.5), c > 0.5)
        resh[seat] = res_s
    lines = []
    for seat, d in resh.items():
        lines.append(f"\n**vs {seat} open (2.5x)** - jam range / opener's correct calling range\n")
        lines.append("| Your stack | You jam | Opener calls |\n|---|---|---|")
        for S, (j, c) in d.items():
            lines.append(f"| {S} BB | {range_pct(j):.0f}%: {compress(j)} | {compress(c)} |")
    write("holdem_reshove", "\n".join(lines) + "\n")

    # ---- opening charts
    seat_rng = {s: parse_range(t) for s, t in OPEN_50BB.items()}
    for s, w in seat_rng.items():
        ranges[s] = {"open": [NAMES[g] for g in range(169) if w[g]], "pct": round(range_pct(w), 1)}

    def open_cell(g):
        for s in SEATS[:-1]:
            if seat_rng[s][g]:
                return s.replace("UTG+1", "U1").replace("UTG", "UT")
        return ""
    summary = "| Seat | Open % | Range |\n|---|---|---|\n" + "\n".join(
        f"| {s} | {range_pct(seat_rng[s]):.1f}% | {OPEN_50BB[s]} |" for s in SEATS[:-1])
    write("holdem_open_chart", "Each cell shows the EARLIEST seat that opens the hand (it is also opened from every later seat).\n"
          "UT = UTG, U1 = UTG+1.\n\n" + grid_md(open_cell) + "\n" + summary + "\n")

    # ---- defence charts (2.5x open; BB closes; SB 3-bets or folds; IP seats 3-bet or call)
    out = []
    for opener in ["UTG", "MP", "HJ", "CO", "BTN", "SB"]:
        o = seat_rng[opener]
        defenders = SEATS[SEATS.index(opener) + 1:]
        for d in defenders:
            if d not in ("BTN", "SB", "BB") and opener in ("UTG", "MP"):
                continue
            ip = 3 if (opener == "SB" and d == "BB") else (2 if d in ("SB", "BB") else 1)
            size = 3.0 if opener == "SB" else 2.5
            if d == "BB":
                dead = 0.5 if opener != "SB" else 0.0
                price = size - 1.0
                pot_after = size * 2 + dead
                allow_call = True
            elif d == "SB":
                price, pot_after, allow_call = size - 0.5, size * 2 + 1, False
            else:
                price, pot_after, allow_call = size, size * 2 + 1.5, d == "BTN"
            if allow_call:
                tb, call, eqo = defend(M, W, o, ip, price, pot_after, allow_call=True)
            else:   # 3-bet-or-fold seats: linear (merged) value range + blocker bluffs
                cap = {"UTG": 3.5, "MP": 4.5, "HJ": 6.0, "CO": 8.0, "BTN": 10.0}[opener]
                tb, call, eqo = linear3bet(M, W, o, cap)
            key = f"{d} vs {opener}"
            ranges[key] = {"3bet_value": [NAMES[g] for g in range(169) if tb[g] == 1],
                           "3bet_bluff": [NAMES[g] for g in range(169) if tb[g] == 2],
                           "call": [NAMES[g] for g in range(169) if call[g]]}
            v = range_pct(tb == 1)
            b = range_pct(tb == 2)
            c = range_pct(call > 0)
            out.append(f"\n#### {d} vs {opener} open ({size:g}x)\n\n3-bet value {v:.1f}% · 3-bet bluff {b:.1f}% · "
                       f"call {c:.1f}% · fold {100 - v - b - c:.1f}% (price: call {price:g} to win {pot_after - price:g} → "
                       f"{100 * price / pot_after:.0f}% raw equity needed)\n")
            out.append(grid_md(lambda g: "**3B**" if tb[g] == 1 else ("3b" if tb[g] == 2 else ("C" if call[g] else ""))))
    write("holdem_defence", "Legend: **3B** = 3-bet for value · 3b = 3-bet bluff (fold to a 4-bet) · C = call · blank = fold\n" + "\n".join(out))

    # ---- 4-bet jam vs 3-bet at 50bb (jam-or-fold subgame)
    lines = ["| Spot | 3-bettor's range | You 4-bet jam 50bb | They call the jam with |", "|---|---|---|---|"]
    for key, opener, vin in (("BTN vs CO", "CO", 7.5), ("SB vs BTN", "BTN", 10.0), ("BB vs BTN", "BTN", 11.0),
                             ("BB vs CO", "CO", 11.0), ("SB vs CO", "CO", 10.0), ("BB vs SB", "SB", 9.0)):
        tbr = np.zeros(169)
        for n in ranges[key]["3bet_value"] + ranges[key]["3bet_bluff"]:
            tbr[IDX[n]] = 1
        hero_in = 3.0 if opener == "SB" else 2.5
        dead = 0.0 if opener == "SB" else (1.0 if key.startswith("SB") else (0.5 if key.startswith("BB") else 1.5))
        o = seat_rng[opener]
        j, c = jam_vs_3bet(M, W, tbr, hero_in=hero_in, vill_in=vin, dead=dead)
        j = fill_pairs(j * o) * o
        lines.append(f"| {opener} opens {hero_in:g}, {key.split()[0]} 3-bets to {vin:g} | {range_pct(tbr):.1f}% | "
                     f"{range_pct(j):.1f}%: {compress(j)} | {compress(c)} |")
    write("holdem_4betjam", "\n".join(lines) + "\n")

    json.dump(ranges, open(os.path.join(RES, "holdem_ranges.json"), "w"), indent=1)
    print("written holdem tables")


def fill_pairs(mask):
    """If a pair is in the range, every higher pair is too (removes Monte-Carlo noise at the margin)."""
    m = np.asarray(mask, float).copy()
    inc = [r for r in range(13) if m[IDX[R[r] * 2]] > 0]
    if inc:
        for r in range(min(inc), 13):
            m[IDX[R[r] * 2]] = 1
    return m


def compress(mask):
    """compact text for a 169 boolean mask: pairs and per-high-card runs."""
    m = np.asarray(mask) > 0
    parts = []
    pairs = [R[r] for r in range(12, -1, -1) if m[IDX[R[r] * 2]]]
    if pairs:
        lo = pairs[-1]
        if all(m[IDX[R[r] * 2]] for r in range(R.index(lo), 13)):
            parts.append(f"{lo}{lo}+")
        else:
            parts.append(",".join(p * 2 for p in pairs))
    for suf in ("s", "o"):
        for hi in range(12, 0, -1):
            ks = [lo for lo in range(hi - 1, -1, -1) if m[IDX[R[hi] + R[lo] + suf]]]
            if not ks:
                continue
            if ks == list(range(hi - 1, ks[-1] - 1, -1)):
                parts.append(f"{R[hi]}{R[ks[-1]]}{suf}+" if len(ks) > 1 else f"{R[hi]}{R[ks[0]]}{suf}")
            else:
                parts.append(",".join(f"{R[hi]}{R[k]}{suf}" for k in ks))
    return ", ".join(parts) if parts else "-"


if __name__ == "__main__":
    main()
