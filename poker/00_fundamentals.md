# 00 · Fundamentals: the maths every variant uses

This page covers the game-theory ideas behind all four guides, worked out for **your game: 5/10 blinds, 500 buy-in (50 big blinds deep)**.

---

## 1. What "GTO" means here, and what it doesn't

* **GTO (game-theory optimal)** means a strategy that can't be exploited. If you play it, the best an opponent can do is break even against you. You get there by making each bet size and each call threshold balanced: your bets hold the right mix of strong hands and bluffs, and you call often enough that bluffs against you don't print money.
* **Heads-up pots** are well covered by theory. **Multiway pots** (3 or more players) have no unique equilibrium, and nobody, human or solver, can compute one for a 6-way Omaha flop. What does carry over to multiway pots:
  1. **Equity thresholds** (pot odds), which are exact whatever the opponents do.
  2. **Value-heavy betting.** Each extra opponent makes it more likely someone has a strong hand, so bluffs work less often and thin value bets get called by better hands more often.
  3. **The nut principle.** When many hands see the flop, the winning hand at showdown is far stronger. I measured exactly how much stronger in every variant.
* So the variant guides are **equity-driven**. Every number in them comes from my own Monte-Carlo simulations, and the betting rules are derived from those numbers with the formulas on this page.

> In every variant except standard Hold'em, everyone posts 10 and nobody bets preflop. So **every player reaches the flop with a random hand** (in Pineapple, a random hand they then discard from). Your opponents' flop ranges are known exactly: they're random. That makes the "equity vs N random hands" tables in the guides the exact numbers for the first decision on the flop. After that, every bet and call narrows ranges, so lean toward the heads-up tables and the "what wins at showdown" tables.

---

## 2. Pot odds, MDF and bluffing ratios

<!--T:bet_math-->
| Bet size | Caller needs equity | MDF (heads-up) | River bluff share of betting range | Value : bluff | MDF per player, 2 opponents | MDF per player, 3 opponents |
|---|---|---|---|---|---|---|
| 25% pot | 17% | 80% | 17% | 5.0 : 1 | 55% each | 42% each |
| 33% pot | 20% | 75% | 20% | 4.0 : 1 | 50% each | 37% each |
| 50% pot | 25% | 67% | 25% | 3.0 : 1 | 42% each | 31% each |
| 66% pot | 28% | 60% | 28% | 2.5 : 1 | 37% each | 26% each |
| 75% pot | 30% | 57% | 30% | 2.3 : 1 | 35% each | 25% each |
| 100% pot | 33% | 50% | 33% | 2.0 : 1 | 29% each | 21% each |
| 150% pot | 38% | 40% | 38% | 1.7 : 1 | 23% each | 16% each |
| 200% pot | 40% | 33% | 40% | 1.5 : 1 | 18% each | 13% each |
<!--/T-->

How to read it:

* **Caller needs equity** = bet / (pot + 2·bet). If the pot is 60 and someone bets 60, you need 33% equity to call (more out of position, because you won't realise all of it).
* **MDF (minimum defence frequency)** = pot / (pot + bet). This is how often you must continue heads-up so a pure bluff can't profit. **Multiway, the defence is shared.** Against a pot-sized bet with 2 opponents, each one only needs to continue about 29% of the time. This is why you should fold far more in multiway pots.
* **River bluff share.** If your river bet is a pot-sized bet, then for the caller to be indifferent, 1/3 of your betting hands should be bluffs (2 value : 1 bluff). With **two or more opponents, cut bluffs drastically**, because each opponent is a separate chance of getting called. A good rule: halve the bluff share for each extra opponent beyond the first.
* **Earlier streets** can carry more bluffs than the river, because "bluffs" there are really **semi-bluffs**: draws with equity. The best ones are draws to the nuts.

---

## 3. Stack-to-pot ratio (SPR) at your stakes

The SPR on the flop decides how big a hand needs to be to stack off.

**Variants with a compulsory 10 from everyone (Omaha / Pineapple / Tic-tac-toe):**

<!--T:variant_spr-->
| Players (all post 10) | Pot on the flop | Behind | SPR | Pot-fraction to get all-in over 3 streets | over 2 streets | 1 street (shove) |
|---|---|---|---|---|---|---|
| 2 | $20 | $490 | 24.5 | 134% | 304% | 2450% |
| 3 | $30 | $490 | 16.3 | 111% | 240% | 1633% |
| 4 | $40 | $490 | 12.2 | 97% | 202% | 1225% |
| 5 | $50 | $490 | 9.8 | 87% | 177% | 980% |
| 6 | $60 | $490 | 8.2 | 79% | 158% | 817% |
| 7 | $70 | $490 | 7.0 | 73% | 144% | 700% |
| 8 | $80 | $490 | 6.1 | 68% | 132% | 612% |
| 9 | $90 | $490 | 5.4 | 64% | 122% | 544% |

Geometric sizing assumes one caller per street; with more callers the pot grows faster, so the same fraction gets the money in sooner.
<!--/T-->

Rules of thumb:

| SPR | Commit with (heads-up guide) |
|---|---|
| < 3 | Top pair good kicker / overpair in Hold'em-type games; top two or better in Omaha. Get it in. |
| 3 - 6 | Two pair+ in Hold'em-type games; sets / nut straights with redraws in Omaha |
| 6 - 13 | Sets / straights+ in Hold'em-type games; near-nuts with redraws in Omaha |
| > 13 | Only the nuts or near-nuts, plus strong draws to the nuts |

**Hold'em (raised pots, 50 bb deep):**

| Pot type | Typical flop pot | Behind | SPR |
|---|---|---|---|
| Single raised, heads-up (2.5x open, BB calls) | 5.5 bb (55) | 47.5 bb | ≈ 8.6 |
| Single raised, 3-way | 8 bb | 47.5 bb | ≈ 6 |
| 3-bet pot (open 2.5, 3-bet to 9-11) | 19-23 bb | ≈ 40 bb | ≈ 2 |
| 4-bet pot | all-in or SPR < 1 | | |

So at 50bb, **3-bet pots are basically commit-or-fold on the flop**. That's why the Hold'em guide uses 4-bet jams instead of small 4-bets.

---

## 4. Bet sizing principles (all variants)

1. **Size with the nuts in mind (polarisation).** The more your betting range is "very strong or nothing", the bigger you can bet. If your range is mostly medium-strength hands, bet small or check.
2. **Geometric sizing.** To get all-in by the river with a strong hand, bet the same fraction of the pot on every street. That fraction is the "3 streets" column in the SPR table above.
3. **Multiway, bet bigger with made hands on wet boards.** With 4-6 opponents holding random hands, many of them have a draw. A third-pot bet gives every draw the right price, so charge them 2/3 to full pot.
4. **Multiway, almost never bluff the river into 3+ players.**
5. **Position.** Acting last is worth a lot. Check-raising is your main weapon from early position. In these variants the betting order postflop is fixed every hand (whoever acts first after the button), so rotate your aggression with the button.

---

## 5. Equity realisation

Raw equity is only an all-in number. A hand **realises** more or less of it depending on:

* **Position.** In position you realise more of your equity.
* **Playability.** Suited and connected hands realise more of their equity. Weak offsuit hands get bluffed off and are often dominated, so they realise less.
* **Nut potential multiway.** In Omaha a non-nut flush draw often costs you money when it gets there. The guides show this directly: nut draws have much higher equity than non-nut ones.

The Hold'em defence charts use an explicit realisation model (listed in the Hold'em guide) to turn equity into call / fold decisions.

---

## 6. Reading the simulation tables

* **Equity** = average share of the pot won at showdown (ties split), with everybody playing to the river. That's what equity means.
* **"How often (6p)"** = how frequently you'll be dealt that category on that street at a 6-handed table.
* **Fair share** = 1 / number of players. A hand that's at or above **2x fair share** is a strong value-betting hand in that pot. A hand around 1x is a pot-control / check hand. Below 1x it's a check-fold, unless the price is very good.
* **Heads-up tables** pair hand categories against each other. They tell you where you stand once the action has narrowed to you against one bettor.

The sample sizes are big (millions of deals per table). Small cells with fewer than a few hundred samples are blanked out.
