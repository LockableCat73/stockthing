# Poker strategy guide: Hold'em, Omaha, Pineapple and Tic-Tac-Toe

A strategy guide for a **5/10 home game with 500 buy-ins (50 big blinds)**. Every number comes from my own simulations: a C hand evaluator, checked exactly against all 133,784,560 seven-card hands, plus Monte-Carlo and equilibrium solvers. None of it is copied from charts found online.

| Guide | What's inside |
|---|---|
| [00 · Fundamentals](00_fundamentals.md) | Pot odds, MDF, value:bluff ratios, multiway adjustments, SPR and bet-sizing tables for your stakes |
| [01 · Texas Hold'em](01_holdem.md) | Opening chart for 9 seats, 3-bet / call / fold charts vs every open, 4-bet-jam equilibrium at 50 bb, **exact push/fold Nash**, re-shove charts, c-bet strategy by board texture from a range-vs-range simulation, home-game exploits |
| [02 · Omaha](02_omaha.md) | What wins (6-handed: a straight or better 78% of the time), starting-hand values, flop / turn / river equity of every made hand and draw vs 2-9 players, heads-up matchups (set vs wrap, etc.), street-by-street strategy |
| [03 · Pineapple](03_pineapple.md) | **The discard rule** (solved for all 22,100 three-card hands at 2-9 players), a point system that is within 0.2% of the best discard for 93-97% of hands, worked examples, post-flop tables |
| [04 · Tic-Tac-Toe](04_tictactoe.md) | Board geometry, why pocket pairs dominate, what wins, flop / turn / river equity tables, center-card outs, strategy |
| [sim/](sim/README.md) | Source code, how to reproduce everything, method details |
| [results/](results/) | Raw simulation output (CSV) and every generated table |

---

## One-page cheat sheet

### Hold'em (50 bb)
* **Open 2.5 bb** (SB 3 bb). Ranges by seat: UTG 77+/ATs+/A5s/KTs+/QTs+/JTs/AJo+/KQo (≈11%) → BTN ≈44% → SB ≈40% ([chart](01_holdem.md#1-opening-raise-first-in)).
* **BB vs BTN**: defend ≈52% (3-bet ≈9%). **SB**: 3-bet or fold.
* **Facing a 3-bet at 50 bb**: 4-bet = all-in. Jam about JJ+/AQs+/AK vs tight 3-bettors, 44+/ATs+ vs a wide SB 3-bet ([table](01_holdem.md#3-facing-a-3-bet-4-bet-jam-50-bb-deep)).
* **≤ 25 bb**: use the [push/fold](01_holdem.md#4-short-stacks-heads-up-pushfold-nash-exact) and [re-shove](01_holdem.md#5-re-shoving-3-bet-all-in-over-an-open-with-10-25-bb) charts.
* **C-bet small (25-33%) and often** in position on A/K/Q-high and paired boards. Check more on low connected boards and when out of position.

### Omaha (everyone sees the flop, random hands)
* **6-handed, a straight or better wins 78% of pots.** The median winning hand is a flush. Play for the nuts.
* Build pots with **top set, nut straights with redraws, nut flushes, NFD + wrap / pair**.
* **Pot control** with two pair and bottom/middle sets. **Check-fold** one pair, overpairs and non-nut draws.
* A non-nut straight vs the nut straight is 12%. Most of your losses will come from second-best hands.

### Pineapple (discard 1 of 3)
1. **Trips** → keep a pair.
2. **Pair + odd card** → keep the pair. *Only exception:* 22-55 with a **suited ace** → keep A-x suited.
3. **Three different ranks** → keep the highest-scoring two cards. At 4-6 players: **high card + ½ low card + 5 if suited + 6 connected / 4 one-gap / 3 two-gap**, with A = 16, K = 13, Q = 12, J = 11, T = 10.
* After the flop, hands are about 15% weaker than the same hand in Hold'em. Don't stack off with one pair multiway.

### Tic-Tac-Toe
* Flop = corners, turn = sides (completes the 4 edge lines), river = center (completes the other 4 lines **at once**).
* **Pocket pairs rule**: a pair in every line. 66 > AKs 6-handed.
* The median 6-handed winner is **trips**. **Straight+ on the turn is near-nuts** (79-94%).
* Flop: bet trips / two pair / combo draws. Check the corner pair (53% of hands, under fair share).

---

## Assumptions

* **No-limit betting**, 5/10 blinds, 500 stacks. In the compulsory-blind variants everyone posts 10 and nobody bets preflop. The tables cover 2-9 players; the prose uses 6-handed as the default.
* **True GTO is solved only where it can be**: Hold'em all-in subgames (push/fold, re-shove, 4-bet jam). Elsewhere, especially in multiway pots, the guides give the exact equities and pot odds and apply equilibrium principles (MDF, polarisation, value:bluff ratios). Nobody can compute a 6-way equilibrium.
* Equity means showdown equity with everyone going to the river. Once betting narrows ranges, lean on the heads-up tables.
