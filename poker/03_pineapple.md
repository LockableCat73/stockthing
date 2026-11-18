# 03 · Pineapple (3 hole cards, discard 1 before the flop, then Hold'em)

**Your format:** everyone posts 10, there's no preflop betting, and everyone discards one card before the flop. Everybody sees every flop. Discarded cards are dead (never dealt to the board).

> **How the discard rule was found.** I simulated **every one of the 22,100 possible 3-card hands**, grouped into the 1,755 suit-equivalent classes. For each class I played 100,000 deals to showdown, testing **all three discards on the same deals** (which cancels most of the noise), at every table size from 2 to 9 players. Opponents also hold 3 cards and discard. I iterated three times: opponents first discard at random, then use the best strategy from the previous round, until the strategy stopped changing. It converged: by the third round only near-ties (a few hundredths of a percent apart) were still flipping. Post-flop tables come from 1 million full deals per table size with everyone discarding optimally.

---

## 1. The discard rule (memorise this)

### Step 1: Trips? Keep two of them.

### Step 2: A pair plus an odd card? Keep the pair, with one exception.

**Exception:** with **22-55** (22-44 heads-up), if the odd card is an **ace of the same suit as one of your pair cards**, break the pair and keep **A-x suited**.
Example: 4♠ 4♦ A♠ → keep **A♠ 4♠**, discard 4♦.

<!--T:pineapple_pair_rule-->
| Players | 22 | 33 | 44 | 55 | 66 | 77 |
|---|---|---|---|---|---|---|
| 2 | A A(off) | A | A | keep pair | keep pair | keep pair |
| 3 | A K A(off) | A | A | A | keep pair | keep pair |
| 4 | A K | A K | A | A | keep pair | keep pair |
| 5 | A K | A | A | A | keep pair | keep pair |
| 6 | A | A | A | A | keep pair | keep pair |
| 7 | A | A | A | A | keep pair | keep pair |
| 8 | A | A | A | A | keep pair | keep pair |
| 9 | A | A | A | A | keep pair | keep pair |

Cells list the odd cards (suited to one of the pair cards) for which you should break the pair and keep that suited two-card hand instead. 66 and above: always keep the pair at every table size.
<!--/T-->

So:
* **Low pair vs high cards**: keep the pair. 2♣2♦ + A♥ (offsuit) → keep **22**. K-suited is never worth breaking a pair for, except 22-33 at 3-5 players, which is a coin flip.
* **66+**: always keep the pair, even with a suited ace (6♣6♦A♣ → 66).
* Heads-up only: 22 + an offsuit ace → keep A2o (barely).

### Step 3: Three different ranks? Score the three possible hands and keep the highest

**Card values:** 2-9 = face value, T = 10, J = 11, Q = 12, K = 13, **A = 16**.

**Score** = value of the higher card + (fraction × value of the lower card) + suited bonus + connectedness bonus:

| Players | Lower card counts | Suited | Connected (e.g. 87) | One gap (86) | Two gaps (85) |
|---|---|---|---|---|---|
| 2-3 | ¾ | +3 | +3 | +3 | +2 |
| **4-6** | **½** | **+5** | **+6** | **+4** | **+3** |
| 7-9 | ½ | +8 | +8 | +6 | +3 |

Example at 6 players, A♣ 7♦ 6♦:
* A7o = 16 + 3.5 = **19.5**
* A6o = 16 + 3 = **19**
* 76s = 7 + 3 + 5 (suited) + 6 (connected) = **21** → keep **7♦6♦**. The simulation agrees: 76s 15.6% vs A7o 13.6%.

Example at 6 players, A♣ K♦ Q♦:
* AKo = 16 + 6.5 + 6 = **28.5**
* KQs = 13 + 6 + 5 + 6 = **30** → keep **K♦Q♦**. Simulation: 24.1% vs 22.9%. Heads-up the answer flips to AKo.

**How good is the rule?**

<!--T:pineapple_rule_accuracy-->
| Players | Rule picks a discard within 0.2% of the best | Avg equity lost by the rule (% pts) | Avg equity lost by 'keep the two highest cards' (% pts) | Avg equity with perfect discards |
|---|---|---|---|---|
| 2 | 96.6% | 0.048 | 0.19 | 50.00% (fair 50.0%) |
| 3 | 94.4% | 0.071 | 0.34 | 33.33% (fair 33.3%) |
| 4 | 95.3% | 0.047 | 0.46 | 25.00% (fair 25.0%) |
| 5 | 94.7% | 0.045 | 0.53 | 20.00% (fair 20.0%) |
| 6 | 93.2% | 0.057 | 0.59 | 16.68% (fair 16.7%) |
| 7 | 95.3% | 0.033 | 0.63 | 14.29% (fair 14.3%) |
| 8 | 95.4% | 0.031 | 0.64 | 12.51% (fair 12.5%) |
| 9 | 94.4% | 0.033 | 0.65 | 11.12% (fair 11.1%) |
<!--/T-->

The rule picks a discard within 0.2% of the best for 93-97% of hands. On average it gives up 0.03-0.07 equity points, which is nothing. The naive "keep your two highest cards" costs about 10× more at a full table.

### The general principles behind it

1. **The bigger the table, the more suitedness and connectedness matter.** In a 7-9 way pot you need straights and flushes to win (see §3), so the suited and connected bonuses grow.
2. **Pairs are kept** because they're already made hands. Big pairs dominate everything, and small pairs flop sets (12%). The only thing that beats a small pair is the **suited ace** (nut-flush potential).
3. **Aces are extra valuable** (worth 16 points, not 14): top pair top kicker and nut flushes.
4. **Card removal:** the card you discard is dead. Discarding a card that matches your kept hand (e.g. keeping K♣5♣ and throwing 5♦) kills one of your own outs. The rule already accounts for this when it says to keep the pair.

### Worked examples straight from the simulation

<!--T:pineapple_examples-->
| Your 3 cards | 2 players | 4 players | 6 players | 9 players |
|---|---|---|---|---|
| 2c2dAc | **A2s** 48.8 · A2o 45.4 · 22 44.3 | **A2s** 23.0 · 22 18.7 · A2o 18.3 | **A2s** 15.9 · 22 13.4 · A2o 10.9 | **A2s** 11.1 · 22 10.1 · A2o 6.2 |
| 2c2dAh | **A2o** 45.3 · A2o 45.3 · 22 44.6 | **22** 19.2 · A2o 18.6 · A2o 18.6 | **22** 13.6 · A2o 11.3 · A2o 11.3 | **22** 10.3 · A2o 6.6 · A2o 6.6 |
| 5c5dAc | **55** 52.0 · A5s 51.1 · A5o 47.9 | **A5s** 25.2 · 55 23.1 · A5o 20.5 | **A5s** 17.0 · 55 15.3 · A5o 12.3 | **A5s** 11.9 · 55 11.0 · A5o 7.1 |
| 5c5dKc | **55** 52.2 · K5s 46.1 · K5o 42.6 | **55** 23.2 · K5s 21.3 · K5o 16.8 | **55** 15.6 · K5s 14.2 · K5o 9.8 | **55** 11.0 · K5s 9.7 · K5o 5.5 |
| 6c6dAc | **66** 54.8 · A6s 51.2 · A6o 48.0 | **66** 25.3 · A6s 24.2 · A6o 19.6 | **66** 16.6 · A6s 16.1 · A6o 11.3 | **66** 11.6 · A6s 11.1 · A6o 6.3 |
| 7c7dAc | **77** 58.1 · A7s 52.4 · A7o 49.3 | **77** 27.6 · A7s 24.8 · A7o 20.3 | **77** 17.5 · A7s 16.6 · A7o 11.8 | **77** 12.3 · A7s 11.2 · A7o 6.5 |
| 3c3dKc | **33** 46.8 · K3s 44.6 · K3o 41.0 | **K3s** 20.4 · 33 20.2 · K3o 15.8 | **33** 14.0 · K3s 13.7 · K3o 9.1 | **33** 10.5 · K3s 9.5 · K3o 5.1 |
| AcKdQd | **AKo** 62.5 · AQo 61.0 · KQs 60.3 | **KQs** 34.0 · AKo 33.9 · AQo 32.0 | **KQs** 24.1 · AKo 22.9 · AQo 21.1 | **KQs** 16.7 · AKo 14.5 · AQo 13.4 |
| AcKd7c | **AKo** 62.6 · A7s 55.0 · K7o 48.2 | **AKo** 34.4 · A7s 27.4 · K7o 21.2 | **AKo** 23.2 · A7s 18.5 · K7o 13.0 | **AKo** 14.5 · A7s 12.7 · K7o 7.7 |
| AcKd7h | **AKo** 62.7 · A7o 52.2 · K7o 48.3 | **AKo** 34.5 · A7o 23.1 · K7o 21.2 | **AKo** 23.5 · A7o 14.0 · K7o 12.9 | **AKo** 14.9 · A7o 8.4 · K7o 7.6 |
| Kc9c8d | **K9s** 53.7 · K8o 48.7 · 98o 42.0 | **K9s** 26.9 · K8o 20.8 · 98o 20.6 | **K9s** 18.1 · 98o 13.4 · K8o 12.4 | **K9s** 12.3 · 98o 8.8 · K8o 7.4 |
| QcJd9d | **QJo** 51.5 · J9s 49.5 · Q9o 47.8 | **J9s** 25.6 · QJo 25.5 · Q9o 21.8 | **J9s** 17.9 · QJo 16.5 · Q9o 13.6 | **J9s** 12.3 · QJo 10.5 · Q9o 8.2 |
| Ac7c6d | **A7s** 54.0 · A6o 50.2 · 76o 37.1 | **A7s** 26.9 · A6o 21.8 · 76o 18.3 | **A7s** 18.3 · A6o 13.1 · 76o 12.2 | **A7s** 12.6 · 76o 8.2 · A6o 7.7 |
| Ac7d6d | **A7o** 51.2 · A6o 50.3 · 76s 40.9 | **A7o** 22.4 · 76s 22.1 · A6o 21.8 | **76s** 15.6 · A7o 13.6 · A6o 13.4 | **76s** 10.9 · A7o 8.0 · A6o 7.9 |
| 8c7c2d | **87s** 41.6 · 82o 30.8 · 72o 29.8 | **87s** 22.4 · 82o 12.5 · 72o 12.4 | **87s** 15.9 · 82o 7.6 · 72o 7.5 | **87s** 11.1 · 82o 4.7 · 72o 4.7 |
| 8c7d2c | **87o** 38.1 · 82s 35.2 · 72o 30.1 | **87o** 18.6 · 82s 16.8 · 72o 12.1 | **87o** 12.3 · 82s 11.6 · 72o 7.6 | **87o** 8.0 · 82s 7.8 · 72o 4.7 |
| Tc9d4h | **T9o** 44.1 · T4o 36.0 · 94o 34.4 | **T9o** 21.5 · T4o 14.7 · 94o 14.2 | **T9o** 14.2 · T4o 9.0 · 94o 8.5 | **T9o** 9.4 · T4o 5.5 · 94o 5.2 |
| AcAdKc | **AA** 83.8 · AKs 61.7 · AKo 59.5 | **AA** 59.9 · AKs 34.7 · AKo 31.0 | **AA** 44.0 · AKs 24.8 · AKo 20.9 | **AA** 29.5 · AKs 17.0 · AKo 13.1 |
| KcQd5c | **KQo** 56.6 · K5s 48.8 · Q5o 42.5 | **KQo** 29.1 · K5s 23.1 · Q5o 18.2 | **KQo** 19.1 · K5s 15.9 · Q5o 10.9 | **KQo** 12.0 · K5s 11.1 · Q5o 6.5 |
| JcTc4h | **JTs** 51.4 · J4o 38.2 · T4o 36.6 | **JTs** 28.2 · J4o 15.7 · T4o 15.3 | **JTs** 19.7 · J4o 9.2 · T4o 9.2 | **JTs** 14.0 · T4o 5.5 · J4o 5.5 |
| Ac5d4d | **A5o** 49.7 · A4o 49.1 · 54s 38.0 | **A5o** 22.0 · A4o 21.7 · 54s 20.4 | **54s** 14.5 · A5o 13.5 · A4o 13.3 | **54s** 10.3 · A5o 8.1 · A4o 8.0 |
| 9c8d7h | **98o** 39.5 · 97o 38.3 · 87o 38.0 | **98o** 18.9 · 87o 18.7 · 97o 17.7 | **98o** 12.0 · 87o 12.0 · 97o 11.4 | **87o** 7.8 · 98o 7.8 · 97o 7.3 |
| Ac2c9d | **A9o** 53.6 · A2s 51.3 · 92o 32.7 | **A2s** 25.1 · A9o 24.3 · 92o 13.4 | **A2s** 17.1 · A9o 14.5 · 92o 8.0 | **A2s** 12.1 · A9o 8.5 · 92o 5.0 |
| Kc7d6d | **K7o** 46.8 · K6o 46.4 · 76s 41.0 | **76s** 22.1 · K7o 19.7 · K6o 19.5 | **76s** 15.6 · K7o 11.9 · K6o 11.8 | **76s** 10.9 · K7o 6.9 · K6o 6.9 |

Each cell: the three possible kept hands, best first, with showdown equity (%) vs the field. (The suits shown in kept-hand names are relative: 's' = the two kept cards share a suit.)
<!--/T-->

### Full keep-priority charts

As a rough lookup, the rank of each two-card hand when kept (1 = best), 6 players. Note it can only be used to compare hands that could come from the **same** three cards:

<!--T:pineapple_keep_rank_N6-->
Rank of every kept two-card hand at 6 players (1 = best), by average equity when kept. Equity of the hand in brackets.

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|1|4|6|9|11|20|23|26|31|24|27|34|37|
|**K**|7|2|10|12|16|25|39|43|48|50|53|57|62|
|**Q**|13|19|3|14|17|32|47|58|63|66|71|78|85|
|**J**|21|28|36|5|18|33|46|60|80|84|88|93|98|
|**T**|29|38|44|45|8|30|40|55|74|95|99|105|108|
|**9**|56|72|79|76|70|15|42|52|69|91|112|114|118|
|**8**|68|101|109|106|96|97|22|49|61|81|103|123|126|
|**7**|82|110|132|129|121|115|107|35|54|67|89|113|130|
|**6**|90|117|133|143|139|135|125|116|41|59|77|100|120|
|**5**|75|124|138|147|152|148|141|131|122|51|65|83|104|
|**4**|86|128|142|150|156|162|155|146|136|127|64|94|111|
|**3**|92|134|145|153|159|164|167|160|151|140|144|73|119|
|**2**|102|137|149|157|161|166|168|169|165|154|158|163|87|
<!--/T-->

Other table sizes: [`2 players`](results/tables/pineapple_keep_rank_N2.md) · [`4`](results/tables/pineapple_keep_rank_N4.md) · [`9`](results/tables/pineapple_keep_rank_N9.md).
Raw per-class results (every 3-card hand, all three discards, 2-9 players): `results/pineapple_discard_N*.csv`.

---

## 2. After the discard: hands are stronger than in Hold'em

Everyone picked their best 2 of 3, so the field holds more pairs, more suited hands and more big cards. **Your post-flop hands are worth less than the same hand in Hold'em.**

Flop equity at 6 players, all-random Hold'em vs Pineapple (everyone discarded well):

| Your flop hand | Hold'em (random hands) | Pineapple | Drop |
|---|---|---|---|
| Top pair, J+ kicker | 37.8% | 31.6% | −16% |
| Overpair | 36.3% | 30.8% | −15% |
| Two pair | 54.0% | 45.9% | −15% |
| Set | 72.6% | 66.0% | −9% |
| Nut straight | 73.1% | 65.6% | −10% |
| Non-nut flush | 74.7% | 63.5% | −15% |
| Nut flush | 92.7% | 89.5% | −3% |

**What wins at showdown in Pineapple:**

<!--T:pineapple_winners-->
| Players | High card | Pair | Two pair | Trips | Straight | Flush | Full house | Quads | Str. flush | Straight+ | Median winner |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 4.5% | 34.3% | 31.9% | 8.7% | 7.9% | 6.0% | 6.0% | 0.5% | 0.1% | 20.5% | Two pair |
| 3 | 1.3% | 26.6% | 32.5% | 11.1% | 10.7% | 8.6% | 8.4% | 0.7% | 0.1% | 28.5% | Two pair |
| 4 | 0.4% | 20.8% | 30.6% | 12.9% | 12.9% | 10.8% | 10.4% | 1.0% | 0.2% | 35.3% | Two pair |
| 5 | 0.1% | 16.2% | 27.9% | 14.3% | 14.8% | 13.0% | 12.3% | 1.2% | 0.2% | 41.5% | Trips |
| 6 | 0.0% | 12.8% | 25.0% | 15.3% | 16.3% | 14.9% | 13.9% | 1.4% | 0.3% | 46.8% | Trips |
| 7 | 0.0% | 10.2% | 22.2% | 16.0% | 17.5% | 16.5% | 15.6% | 1.6% | 0.3% | 51.5% | Straight |
| 8 | 0.0% | 8.2% | 19.7% | 16.4% | 18.4% | 17.9% | 17.0% | 1.9% | 0.4% | 55.6% | Straight |
| 9 | 0.0% | 6.6% | 17.3% | 16.8% | 19.1% | 19.2% | 18.4% | 2.1% | 0.4% | 59.3% | Straight |
<!--/T-->

Compare with Hold'em with random hands at 6 players: straight+ wins 39.5% (Pineapple 46.8%), and one pair wins 16.1% (Pineapple 12.8%).

## 3. Flop

<!--T:pineapple_flop_made-->
| Hand | How often (6p) | 3 players | 4 players | 5 players | 6 players | 7 players | 8 players | 9 players |
|---|---|---|---|---|---|---|---|---|
| nothing | 54.82% | 21.0% | 15.0% | 11.9% | 10.0% | 8.6% | 7.6% | 6.9% |
| weak pair (bottom pair / small pocket pair) | 12.46% | 27.1% | 17.7% | 13.2% | 10.6% | 8.9% | 7.8% | 6.9% |
| middle pair (or pocket pair between top & 2nd card) | 12.12% | 41.6% | 29.2% | 21.5% | 16.7% | 13.4% | 11.2% | 9.6% |
| top pair, kicker below J | 5.37% | 54.3% | 41.4% | 32.2% | 25.6% | 20.9% | 17.3% | 14.5% |
| top pair, J+ kicker | 5.33% | 59.8% | 47.8% | 38.6% | 31.6% | 26.3% | 22.2% | 18.8% |
| overpair | 4.01% | 59.9% | 47.5% | 38.0% | 30.8% | 25.4% | 20.9% | 17.7% |
| two pair (both cards) | 1.74% | 70.3% | 59.8% | 52.0% | 45.9% | 40.7% | 36.4% | 33.0% |
| trips (board pair + 1 card) | 1.16% | 83.5% | 77.0% | 70.7% | 65.8% | 60.7% | 56.3% | 52.4% |
| set | 1.84% | 83.1% | 76.8% | 71.1% | 66.0% | 61.9% | 58.1% | 55.0% |
| straight (non-nut) | 0.13% | 72.8% | 65.3% | 58.2% | 50.6% | 45.7% | 41.7% | 38.1% |
| nut straight | 0.36% | 83.4% | 76.7% | 70.6% | 65.6% | 60.7% | 56.6% | 52.3% |
| flush (non-nut) | 0.27% | 83.4% | 76.1% | 69.3% | 63.5% | 59.4% | 54.6% | 50.3% |
| nut flush | 0.08% | 94.9% | 93.5% | 90.9% | 89.5% | 87.3% | 85.8% | 84.3% |
| full house or better | 0.30% | 90.6% | 87.5% | 84.5% | 82.4% | 80.0% | 79.1% | 77.0% |
<!--/T-->

Draws (no pair):

<!--T:pineapple_flop_draws-->
_Draws with no pair (equity to the river vs the whole field)_

| Draw | How often (6p) | 3 players | 4 players | 5 players | 6 players | 7 players | 8 players | 9 players |
|---|---|---|---|---|---|---|---|---|
| no draw | 39.60% | 17.3% | 11.1% | 8.0% | 6.2% | 4.9% | 4.1% | 3.5% |
| gutshot | 7.83% | 25.2% | 19.2% | 15.9% | 13.6% | 12.1% | 10.8% | 9.8% |
| open-ender / double gutter | 2.81% | 33.2% | 27.5% | 24.0% | 21.7% | 19.7% | 18.0% | 16.6% |
| flush draw (non-nut) | 2.84% | 38.4% | 32.6% | 28.9% | 25.8% | 23.8% | 21.6% | 19.8% |
| nut flush draw | 0.77% | 49.0% | 42.1% | 38.4% | 36.1% | 33.8% | 32.9% | 31.4% |
| flush draw + straight draw | 0.96% | 47.4% | 40.8% | 37.3% | 34.0% | 31.5% | 29.2% | 27.2% |
<!--/T-->

Made hand × draw at 6 players:

<!--T:pineapple_flop_grid6-->
| Made hand \ draw | no draw | gutshot | open-ender / double gutter | flush draw (non-nut) | nut flush draw | flush draw + straight draw |
|---|---|---|---|---|---|---|
| nothing | 6% | 14% | 22% | 26% | 36% | 34% |
| weak pair (bottom pair / small pocket pair) | 10% | 14% | 19% | 24% |  |  |
| middle pair (or pocket pair between top & 2nd card) | 16% | 19% | 23% | 32% | 46% |  |
| top pair, kicker below J | 25% | 22% | 24% | 40% |  |  |
| top pair, J+ kicker | 31% | 28% |  | 45% | 56% |  |
| overpair | 31% | 26% |  | 31% |  |  |
| two pair (both cards) | 46% |  |  |  |  |  |
| trips (board pair + 1 card) | 66% |  |  |  |  |  |
| set | 66% |  |  |  |  |  |
| straight (non-nut) | 51% |  |  |  |  |  |
| nut straight | 66% |  |  |  |  |  |
| flush (non-nut) | 64% |  |  |  |  |  |
| nut flush | 89% |  |  |  |  |  |
| full house or better | 82% |  |  |  |  |  |
<!--/T-->

Heads-up equity, flop category vs category: [`results/tables/pineapple_hu_flop.md`](results/tables/pineapple_hu_flop.md).

## 4. Turn

<!--T:pineapple_turn_made-->
| Hand | How often (6p) | 3 players | 4 players | 5 players | 6 players | 7 players | 8 players | 9 players |
|---|---|---|---|---|---|---|---|---|
| nothing | 45.56% | 15.1% | 9.9% | 7.6% | 6.3% | 5.5% | 4.8% | 4.4% |
| weak pair (bottom pair / small pocket pair) | 18.07% | 25.1% | 15.1% | 10.3% | 7.7% | 6.1% | 5.2% | 4.4% |
| middle pair (or pocket pair between top & 2nd card) | 11.09% | 42.0% | 28.5% | 20.1% | 14.7% | 11.1% | 8.8% | 7.1% |
| top pair, kicker below J | 4.92% | 54.5% | 41.1% | 31.2% | 24.0% | 18.9% | 15.1% | 12.1% |
| top pair, J+ kicker | 5.22% | 60.2% | 47.8% | 37.8% | 30.5% | 24.6% | 20.3% | 16.6% |
| overpair | 3.11% | 61.4% | 49.0% | 39.0% | 31.3% | 25.4% | 20.6% | 16.9% |
| two pair (both cards) | 3.17% | 67.5% | 56.5% | 48.0% | 41.4% | 35.8% | 31.5% | 27.8% |
| trips (board pair + 1 card) | 1.97% | 82.1% | 74.8% | 68.3% | 62.6% | 57.3% | 52.4% | 48.3% |
| set | 2.09% | 81.1% | 74.0% | 67.6% | 62.1% | 57.5% | 53.3% | 50.0% |
| straight (non-nut) | 0.92% | 72.3% | 63.3% | 55.8% | 49.8% | 44.6% | 39.8% | 35.9% |
| nut straight | 1.05% | 84.8% | 78.9% | 73.5% | 68.3% | 64.1% | 60.1% | 56.1% |
| flush (non-nut) | 1.17% | 80.6% | 72.6% | 66.6% | 60.8% | 56.4% | 51.6% | 47.5% |
| nut flush | 0.32% | 95.1% | 93.0% | 91.1% | 89.2% | 87.0% | 85.7% | 84.0% |
| full house or better | 1.32% | 87.3% | 83.1% | 79.4% | 76.5% | 73.6% | 71.4% | 69.4% |
<!--/T-->

<!--T:pineapple_turn_draws-->
_Draws with no pair (one card to come)_

| Draw | How often (6p) | 3 players | 4 players | 5 players | 6 players | 7 players | 8 players | 9 players |
|---|---|---|---|---|---|---|---|---|
| no draw | 24.38% | 11.1% | 5.7% | 3.4% | 2.2% | 1.5% | 1.0% | 0.8% |
| gutshot | 10.01% | 15.4% | 10.4% | 8.1% | 6.8% | 5.9% | 5.2% | 4.8% |
| open-ender / double gutter | 4.17% | 19.8% | 15.5% | 13.6% | 12.1% | 11.0% | 10.1% | 9.4% |
| flush draw (non-nut) | 3.46% | 22.6% | 17.8% | 14.9% | 13.2% | 11.9% | 10.7% | 9.8% |
| nut flush draw | 0.96% | 33.1% | 25.5% | 22.3% | 19.9% | 18.5% | 17.6% | 16.6% |
| flush draw + straight draw | 2.60% | 29.7% | 24.6% | 22.0% | 19.7% | 18.2% | 16.8% | 15.7% |
<!--/T-->

## 5. River: how often each hand is best vs N−1 random (discarded) hands, 6 players

<!--T:pineapple_river_N6-->
| River hand | Avg | A | K | Q | J | T | 9 | 8 | 7 | 6 | 5 | 4 | 3 | 2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| High card | 0.0% | 0% | 0% | 0% | 0% | 0% | 0% |  |  |  |  |  |  |  |
| Pair | 5.1% | 17% | 13% | 9% | 6% | 4% | 3% | 2% | 1% | 1% | 1% | 0% | 0% | 0% |
| Two pair | 16.4% | 26% | 22% | 17% | 14% | 12% | 10% | 9% | 9% | 9% | 10% | 9% | 9% |  |
| Trips | 44.9% | 48% | 49% | 47% | 45% | 43% | 44% | 44% | 44% | 44% | 43% | 44% | 44% | 42% |
| Straight | 56.6% | 63% | 56% | 54% | 53% | 53% | 54% | 56% | 58% | 60% | 54% |  |  |  |
| Flush | 63.2% | 71% | 62% | 57% | 53% | 51% | 50% | 52% | 52% |  |  |  |  |  |
| Full house | 69.2% | 76% | 76% | 75% | 72% | 71% | 69% | 69% | 66% | 66% | 65% | 63% | 62% | 61% |
| Quads | 91.6% | 94% | 94% | 93% | 91% | 92% | 92% | 91% | 90% | 91% | 91% | 93% | 89% | 89% |
| Str. flush | 95.8% | 100% | 92% |  |  |  |  |  |  |  |  |  |  |  |
<!--/T-->

(Full houses and quads show under 100% because many of them are on the board and get split.)

---

## 6. Strategy

**Flop** (SPR ≈ 8 at 6-handed):
* **Value-bet / raise:** sets, trips, two pair (46% at 6-handed, 2.8× fair share), straights, flushes, and **top pair + flush draw** (40-56%).
* **Bet or call, but stay cautious:** top pair good kicker / overpair (31%, 1.9×). Bet for protection on wet boards, keep the pot smaller on dry ones. **Don't stack off with one pair in a multiway Pineapple pot.** Two pair or better wins 87% of 6-handed showdowns.
* **Draws:** the **nut flush draw is a monster** (36% with nothing else). Non-nut flush draws (26%) and open-enders (22%) are calls at reasonable prices. Gutshots (14%) are folds unless the bet is small.
* **Check-fold:** weak and middle pairs (11-17%), and nothing (6-10%).

**Turn:** bet 2/3 to full pot with two pair+ and nut draws. Check-fold one-pair hands to aggression in multiway pots.

**River:**
* At 6 players, **trips is best only 45% of the time** against random hands, and a straight 57%.
* Value-bet straights, flushes and full houses. Check trips and two pair against multiple opponents.
* Bluff only heads-up, with blockers.

**Bet sizing:** same as Hold'em multiway. Use 2/3 pot as the default flop size, because the field has more draws than in Hold'em.

**Exploit:** most home players discard badly. They keep AKo over suited connectors at full tables, or break small pairs for offsuit high cards. So their kept hands are slightly weaker than the simulated optimal field, and your hands are worth a little more than these tables say.
