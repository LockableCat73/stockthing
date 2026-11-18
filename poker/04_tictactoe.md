# 04 · Tic-Tac-Toe Poker (2 hole cards + any 3-in-a-row on a 3×3 board)

**Rules as played:** 2 hole cards each, and a 3×3 grid of community cards. Your hand is **both hole cards + the three cards of any one line**: 3 rows, 3 columns or 2 diagonals (8 lines). Flop = the 4 corners, turn = the 4 sides, river = the center. Everyone posts 10 and there's no preflop betting, so **everybody sees every flop**.

> This variant has no published theory, so everything here is my own simulation: 100,000 deals for each of the 169 starting hands at every table size from 2 to 9 players, and 1 million full deals per table size for the flop / turn / river tables (every seat classified on every street). The evaluator scores each player as the best of their 8 lines, each line being exactly the 2 hole cards + 3 line cards.

---

## 1. The geometry: understand this and you're ahead of the table

```
   TL ── T ── TR        flop  = TL, TR, BL, BR (corners)
   │  ╲   │   ╱ │        turn  = T, L, R, B (sides)
   L ──── X ──── R       river = X (center)
   │  ╱   │   ╲ │
   BL ── B ── BR
```

| Line | Cards | Complete after |
|---|---|---|
| Top row | TL · T · TR | **turn** |
| Bottom row | BL · B · BR | **turn** |
| Left column | TL · L · BL | **turn** |
| Right column | TR · R · BR | **turn** |
| Middle row | L · X · R | river |
| Middle column | T · X · B | river |
| Diagonal ↘ | TL · X · BR | river |
| Diagonal ↙ | TR · X · BL | river |

Facts that drive all the strategy:
1. **Every pair of corners shares exactly one line.** On the flop, your hand is effectively your 2 hole cards + any 2 of the 4 corners, with 1 card to come in that line. That's 6 possible 4-card hands.
2. **The turn completes the four edge lines**, so after the turn you hold a real 5-card hand.
3. **All four remaining lines run through the center.** The river is a single card that changes four lines at once, for everybody. On the turn, look at the four pairs (L,R), (T,B), (TL,BR), (TR,BL) to see what the center card can make.
4. **You must use both hole cards.** There's no playing the board. A flush needs both hole cards suited plus a 3-card suited line. A straight needs both hole cards to fit into it.
5. **Each line has only 3 board cards**, so straights, flushes and full houses are much rarer than in Hold'em. **Trips is the median winning hand 6-handed.**

---

## 2. What wins

<!--T:ttt_winners-->
| Players | High card | Pair | Two pair | Trips | Straight | Flush | Full house | Quads | Str. flush | Straight+ | Median winner |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.5% | 37.1% | 31.3% | 20.0% | 5.6% | 2.9% | 2.2% | 0.4% | 0.0% | 11.0% | Two pair |
| 3 | 0.1% | 23.4% | 34.5% | 26.1% | 8.0% | 4.2% | 3.2% | 0.6% | 0.0% | 15.9% | Two pair |
| 4 | 0.0% | 14.6% | 34.1% | 30.8% | 10.2% | 5.3% | 4.2% | 0.8% | 0.0% | 20.6% | Trips |
| 5 | 0.0% | 9.2% | 31.6% | 34.1% | 12.2% | 6.6% | 5.3% | 1.0% | 0.1% | 25.0% | Trips |
| 6 | 0.0% | 5.8% | 28.7% | 36.5% | 14.0% | 7.6% | 6.2% | 1.1% | 0.1% | 29.0% | Trips |
| 7 | 0.0% | 3.7% | 25.4% | 38.0% | 15.6% | 8.7% | 7.2% | 1.3% | 0.1% | 32.9% | Trips |
| 8 | 0.0% | 2.4% | 22.3% | 39.0% | 17.0% | 9.6% | 8.1% | 1.5% | 0.1% | 36.3% | Trips |
| 9 | 0.0% | 1.6% | 19.3% | 39.4% | 18.3% | 10.5% | 9.0% | 1.7% | 0.1% | 39.7% | Trips |
<!--/T-->

Compare 6-handed: Hold'em with random hands, straight+ wins 39.5% and the median winner is trips. Omaha, 78% and a flush. **Tic-tac-toe, 29%: hands are smaller than in Hold'em, despite the 8 lines.**

## 3. Starting hands (no decisions, but know your strength)

**Pocket pairs are the kings of this game.** A pocket pair is a pair in *every one of the 8 lines*, and any matching card in any line gives you trips.

<!--T:ttt_vs_holdem_types-->
| Hand type | 2 players | 4 players | 6 players | 8 players |
|---|---|---|---|---|
| pocket pairs | 74.6% / 68.6% | 47.1% / 39.7% | 33.3% / 27.2% | 25.5% / 20.8% |
| suited | 51.1% / 50.9% | 27.1% / 26.9% | 19.3% / 19.0% | 15.2% / 15.0% |
| offsuit | 47.6% / 48.1% | 22.4% / 23.1% | 14.4% / 15.0% | 10.5% / 11.0% |

(Tic-tac-toe / Hold'em average equity)
<!--/T-->

Equity vs 5 random hands (6-handed):

<!--T:ttt_preflop_grid_N6-->
Equity (%) vs 5 random hands, everyone to showdown. Fair share = 16.7%. Bold = at least 1.5x fair share.

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|**48**|**29**|**27**|**26**|**26**|24|23|22|21|22|22|21|21|
|**K**|24|**43**|**27**|**26**|**25**|23|20|20|20|19|19|18|18|
|**Q**|23|22|**40**|**26**|25|22|21|18|18|18|17|17|17|
|**J**|22|21|21|**38**|**25**|23|21|19|17|16|16|16|15|
|**T**|21|20|20|21|**35**|24|22|19|17|15|15|15|15|
|**9**|18|18|18|18|19|**34**|23|20|19|16|14|14|14|
|**8**|18|16|16|16|17|18|**32**|21|20|18|16|14|13|
|**7**|17|15|13|14|15|16|17|**30**|21|19|17|15|13|
|**6**|16|14|13|12|13|14|15|16|**29**|20|18|16|14|
|**5**|17|14|12|11|10|12|13|14|15|**28**|19|18|16|
|**4**|17|14|12|11|10|9|11|12|14|15|**27**|17|15|
|**3**|16|13|12|11|10|9|9|10|12|13|13|**25**|15|
|**2**|16|13|11|10|10|9|8|8|10|11|11|10|24|
<!--/T-->

* **22 (24%) is as strong as A9s / KTs**, and **66 (29.1%) beats AKs (28.5%)** at 6-handed. In Hold'em, 22 is far behind both.
* Big offsuit cards are weaker than in Hold'em. They can only pair up within a line. AKo is 24% at 6-handed, about 1.45× fair share.
* Suited and connected cards gain a little, because you get 8 shots at a 3-card line that fits.

Other table sizes: [2](results/tables/ttt_preflop_grid_N2.md) · [4](results/tables/ttt_preflop_grid_N4.md) · [8](results/tables/ttt_preflop_grid_N8.md) · [full ranked list](results/tables/ttt_preflop_all.md).

## 4. Flop (the 4 corners)

What you have: the best "4-card hand" using your 2 cards + any 2 corners.

<!--T:ttt_flop_made-->
| Hand | How often (6p) | 3 players | 4 players | 5 players | 6 players | 7 players | 8 players | 9 players |
|---|---|---|---|---|---|---|---|---|
| nothing | 34.53% | 21.8% | 15.2% | 12.0% | 9.9% | 8.7% | 7.7% | 7.1% |
| pair with a corner card | 53.42% | 33.4% | 24.4% | 18.9% | 15.4% | 12.8% | 10.9% | 9.5% |
| pocket pair | 3.24% | 51.5% | 39.5% | 31.0% | 25.3% | 20.9% | 17.7% | 15.2% |
| two pair | 5.21% | 63.7% | 52.1% | 43.6% | 37.0% | 31.8% | 28.0% | 24.7% |
| trips / set | 3.57% | 82.8% | 75.4% | 69.2% | 63.4% | 58.6% | 54.2% | 50.3% |
| quads | 0.03% | 100.0% | 99.6% | 99.8% | 99.6% | 99.7% | 99.7% | 99.7% |
<!--/T-->

Draws for hands with at most a corner pair (a 4-flush = both hole cards suited + 2 corners of that suit; a 4-straight = your 2 cards + 2 corners are four cards within a 5-rank window):

<!--T:ttt_flop_draws-->
_Flop draws for hands with at most a corner pair_

| Draw | How often (6p) | 3 players | 4 players | 5 players | 6 players | 7 players | 8 players | 9 players |
|---|---|---|---|---|---|---|---|---|
| no draw | 68.46% | 27.0% | 18.6% | 13.8% | 10.8% | 8.7% | 7.2% | 6.1% |
| 4 to a straight | 14.71% | 33.1% | 26.3% | 22.2% | 19.4% | 17.5% | 15.8% | 14.6% |
| 4 to a flush | 3.88% | 41.7% | 34.5% | 30.7% | 27.9% | 26.0% | 24.3% | 23.1% |
| 4 to a straight AND 4 to a flush | 0.91% | 46.5% | 41.4% | 38.1% | 35.4% | 33.7% | 31.6% | 30.1% |
<!--/T-->

Combined, 6-handed:

<!--T:ttt_flop_grid6-->
| Made hand \ draw | no draw | 4 to a straight | 4 to a flush | 4 to a straight AND 4 to a flush |
|---|---|---|---|---|
| nothing | 6% | 16% | 27% | 34% |
| pair with a corner card | 13% | 23% | 29% | 38% |
| pocket pair | 25% |  |  |  |
| two pair | 37% | 43% |  |  |
| trips / set | 63% | 62% |  |  |
<!--/T-->

Heads-up, flop category vs category:

<!--T:ttt_hu_flop-->
| Hero \ villain | nothing | pair with a corner card | pocket pair | two pair | trips / set |
|---|---|---|---|---|---|
| nothing | 50% | 30% | 18% | 12% | 6% |
| pair with a corner card | 70% | 50% | 38% | 19% | 7% |
| pocket pair | 82% | 62% | 50% | 35% | 10% |
| two pair | 88% | 81% | 65% | 50% | 14% |
| trips / set | 94% | 93% | 90% | 86% | 50% |
<!--/T-->

## 5. Turn (the 4 sides: edge lines are complete)

Your made hand (best of the 4 edge lines):

<!--T:ttt_turn_made-->
| Hand | How often (6p) | 3 players | 4 players | 5 players | 6 players | 7 players | 8 players | 9 players |
|---|---|---|---|---|---|---|---|---|
| High card | 11.68% | 12.0% | 7.2% | 5.1% | 4.0% | 3.4% | 2.9% | 2.6% |
| Pair | 63.67% | 24.7% | 16.6% | 12.2% | 9.5% | 7.8% | 6.6% | 5.8% |
| Two pair | 14.54% | 56.1% | 43.0% | 33.4% | 26.4% | 21.2% | 17.3% | 14.3% |
| Trips | 7.15% | 73.8% | 65.8% | 58.8% | 52.8% | 47.7% | 43.1% | 39.2% |
| Straight | 1.53% | 91.0% | 87.2% | 82.9% | 79.4% | 75.8% | 72.5% | 69.5% |
| Flush | 0.77% | 94.8% | 91.9% | 89.5% | 86.8% | 84.8% | 82.1% | 79.8% |
| Full house | 0.56% | 97.5% | 96.5% | 95.4% | 94.4% | 93.4% | 92.3% | 91.3% |
| Quads | 0.09% | 99.8% | 99.8% | 99.7% | 99.6% | 99.6% | 99.5% | 99.5% |
| Str. flush | 0.01% |  | 100.0% | 100.0% | 99.7% | 100.0% | 100.0% | 100.0% |
<!--/T-->

Draws to a straight or better via the center card:

<!--T:ttt_turn_draws-->
_Turn: hands of trips or worse, by number of center cards that give a straight+_

| Draw | How often (6p) | 3 players | 4 players | 5 players | 6 players | 7 players | 8 players | 9 players |
|---|---|---|---|---|---|---|---|---|
| no center outs to straight+ | 74.67% | 27.8% | 19.1% | 14.0% | 10.9% | 8.6% | 7.0% | 5.8% |
| 1-3 center outs | 5.27% | 47.3% | 39.5% | 33.9% | 29.8% | 26.4% | 23.8% | 21.4% |
| 4-7 center outs | 12.36% | 43.0% | 35.0% | 29.7% | 25.7% | 22.8% | 20.4% | 18.6% |
| 8-11 center outs | 4.28% | 40.3% | 33.5% | 29.1% | 26.1% | 23.9% | 22.0% | 20.5% |
| 12+ center outs | 0.46% | 56.6% | 49.8% | 44.9% | 41.2% | 39.1% | 36.2% | 34.3% |
<!--/T-->

Combined, 6-handed:

<!--T:ttt_turn_grid6-->
| Made hand \ draw | no center outs to straight+ | 1-3 center outs | 4-7 center outs | 8-11 center outs | 12+ center outs |
|---|---|---|---|---|---|
| High card | 2% | 7% | 11% | 19% |  |
| Pair | 6% | 14% | 21% | 24% | 38% |
| Two pair | 24% | 41% | 30% | 37% | 48% |
| Trips | 48% | 61% | 59% | 50% |  |
| Straight | 79% |  |  |  |  |
| Flush | 87% |  |  |  |  |
| Full house | 94% | 95% |  |  |  |
| Quads | 100% |  |  |  |  |
<!--/T-->

Heads-up, made hand vs made hand on the turn:

<!--T:ttt_hu_turn-->
| Hero \ villain | High card | Pair | Two pair | Trips | Straight | Flush | Full house |
|---|---|---|---|---|---|---|---|
| High card | 50% | 21% | 4% | 3% | 2% | 0% |  |
| Pair | 79% | 50% | 11% | 4% | 2% | 1% | 0% |
| Two pair | 96% | 89% | 50% | 7% | 2% | 1% | 0% |
| Trips | 97% | 96% | 93% | 50% | 4% | 4% | 1% |
| Straight | 98% | 98% | 98% | 96% | 50% | 0% | 0% |
| Flush | 100% | 99% | 99% | 96% | 100% | 50% | 0% |
| Full house |  | 100% | 100% | 99% | 100% | 100% | 50% |
<!--/T-->

## 6. River (the center): how often each hand is best vs random hands, 6-handed

<!--T:ttt_river_N6-->
| River hand | Avg | A | K | Q | J | T | 9 | 8 | 7 | 6 | 5 | 4 | 3 | 2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| High card | 0.0% | 0% | 0% | 0% | 0% |  |  |  |  |  |  |  |  |  |
| Pair | 1.7% | 4% | 3% | 2% | 2% | 1% | 1% | 1% | 0% | 0% | 0% | 0% | 0% | 0% |
| Two pair | 22.2% | 33% | 28% | 24% | 21% | 19% | 17% | 15% | 14% | 13% | 12% | 12% | 12% |  |
| Trips | 50.3% | 62% | 60% | 58% | 55% | 53% | 51% | 49% | 48% | 46% | 45% | 43% | 42% | 42% |
| Straight | 79.5% | 85% | 83% | 80% | 80% | 79% | 78% | 78% | 79% | 77% | 76% |  |  |  |
| Flush | 86.9% | 90% | 87% | 85% | 83% | 82% | 81% | 81% |  |  |  |  |  |  |
| Full house | 94.4% | 95% | 96% | 95% | 95% | 95% | 95% | 95% | 94% | 94% | 94% | 93% | 93% | 93% |
| Quads | 99.7% | 100% | 100% | 99% | 100% | 100% | 100% | 100% | 100% | 99% | 100% | 99% | 100% | 99% |
| Str. flush | 99.9% |  |  |  |  |  |  |  |  |  |  |  |  |  |
<!--/T-->

Other table sizes: [4 players](results/tables/ttt_river_N4.md) · [8 players](results/tables/ttt_river_N8.md).

---

## 7. Strategy

### Flop (corners out, SPR ≈ 8 at 6-handed)

| Your flop hand | Equity 6-handed | × fair share | Play |
|---|---|---|---|
| Trips / set (pocket pair + matching corner, or a card + corner pair) | 63% | 3.8× | Bet big (2/3 to full pot), raise. Build the pot |
| Two pair | 37% | 2.2× | Bet for value and protection |
| 4-flush + 4-straight | 35% | 2.1× | Bet or raise as a semi-bluff |
| 4-flush (both cards suited + 2 suited corners) | 28% | 1.7× | Bet in position, otherwise call |
| Pocket pair (no match) | 25% | 1.5× | Bet small or check-call. Big pairs are stronger |
| 4-straight | 19% | 1.2× | Call small bets |
| Pair with a corner (53% of all hands!) | 15% | 0.9× | Check. Fold to big bets |
| Nothing | 10% | 0.6× | Check-fold |

* **The flop is a "1 card to come per line" street.** Each corner pair is waiting on one side card, or on the center for diagonals. Flush and straight draws are one specific card per line, and that's why they're weaker than Hold'em draws.
* **Pairs with a corner are the trap hand.** Over half the table holds one, and they're under fair share.

### Turn (sides out)

* **A made straight or better is nearly the nuts**: 79-94% against 5 random hands. Bet big. You can get it in at SPR ≤ 3.
* **Trips: 53% at 6-handed.** Bet for value, but beware of raises when the center lines show straight or flush potential.
* **Two pair: 26%, still only 1.6× fair share.** Bet small or check-call. Two pair with center outs to a straight or better is better (30-48%).
* **Pair / high card: check-fold**, unless you hold 8+ center outs to a straight or better (24%+), which is a calling hand at a good price.
* **Count your center outs.** For each of your 4 center lines, look at its two known cards plus your hole cards: which center cards would complete a straight, flush, full house or trips? The same card can hit several of your lines at once.
* **Count everyone else's center outs too.** If L-R are 9-8 suited and T-B are 9-9, the center card will make a lot of strong hands. Bet your made hand big *now* to charge those draws.

### River (center out)

* **Value-bet trips and better** against 1-2 opponents. Trips is best 50% of the time against 5 random hands, and much more often against a single caller who checked to you.
* **A straight or better (80%+): bet big.** At 6-handed, a straight wins 80% against random hands and a flush 87%. Pot-sized bets and shoves are fine.
* **Two pair: check.** It's best only 22% of the time 6-handed.
* **Bluffing:** the center card changes four lines for everyone, so when it makes an obvious straight or flush you can represent it heads-up. Multiway, don't bluff.

### Pocket pairs: the core of the game

* **Before the flop:** you're 1.5-3× fair share with any pocket pair. Expect to play a big pot if any line gives you a matching card.
* **Flop:** a matching corner means you already hold trips in all three lines through that corner. One more matching card in any of those lines makes quads, and a corner pair in a line with you makes a full house.
* **Turn / river:** with no match by the turn, a pocket pair is just one pair. Any pair on the turn has 9.5% equity at 6-handed. Let it go to aggression.

### Bet sizing

Same SPR as the other compulsory-blind variants (see [Fundamentals §3](00_fundamentals.md)). Default flop bet 2/3 pot with value and strong draws. Turn: pot-sized with straights+, smaller with trips. River: polarised.
