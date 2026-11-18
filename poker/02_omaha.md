# 02 · Omaha (4 hole cards, use exactly 2 + exactly 3 from the board)

**Your format:** everyone posts 10, there's **no preflop betting**, so **every player sees every flop with a random 4-card hand**. Stacks are 500. The flop pot is 10 × players (60 at 6-handed) and the SPR is about 8 at 6-handed (see [Fundamentals §3](00_fundamentals.md)).

> All numbers below come from my own simulation: 300,000 full deals for each table size from 2 to 9 players, with every seat classified on the flop and turn and played to showdown. That's 0.6-2.7 million hand-samples per table. Starting-hand values come from 3 million deals per table size, plus 400,000 deals for each named hand. Because nobody folds preflop, the opponents' hands on the flop are exactly what the simulation assumes: random.

---

## 1. The single most important fact: hands are huge

**What wins at showdown** (everyone to the river, no folding):

<!--T:omaha_winners-->
| Players | High card | Pair | Two pair | Trips | Straight | Flush | Full house | Quads | Str. flush | Straight+ | Median winner |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.2% | 10.5% | 34.7% | 11.8% | 18.1% | 11.7% | 11.9% | 1.0% | 0.2% | 42.9% | Trips |
| 3 | 0.0% | 4.2% | 26.9% | 12.9% | 22.2% | 15.5% | 16.6% | 1.4% | 0.3% | 55.9% | Straight |
| 4 | 0.0% | 1.7% | 20.0% | 12.9% | 24.6% | 17.9% | 20.6% | 1.9% | 0.4% | 65.4% | Straight |
| 5 | 0.0% | 0.6% | 14.5% | 12.2% | 25.9% | 19.9% | 24.1% | 2.3% | 0.5% | 72.7% | Straight |
| 6 | 0.0% | 0.2% | 10.3% | 11.3% | 26.6% | 20.9% | 27.4% | 2.9% | 0.5% | 78.2% | Flush |
| 7 | 0.0% | 0.1% | 7.4% | 10.2% | 26.6% | 21.9% | 29.9% | 3.4% | 0.6% | 82.4% | Flush |
| 8 | 0.0% | 0.0% | 5.2% | 9.1% | 26.7% | 22.2% | 32.3% | 3.8% | 0.7% | 85.6% | Flush |
| 9 | 0.0% | 0.0% | 3.8% | 8.0% | 26.6% | 22.3% | 34.2% | 4.3% | 0.8% | 88.2% | Flush |
<!--/T-->

* **6-handed, 78% of pots are won by a straight or better.** The *median* winning hand is a **flush**.
* Two pair wins 10% of 6-way pots. One pair essentially never wins.
* So **non-nut hands are traps**. The second-best flush or the low end of a straight loses big pots to the hands that beat it. Most of the money you lose in this game will come from second-best hands.

## 2. Starting hands (no decisions, but know where you stand)

Starting strength only tells you how lucky you got. You still see every flop.

<!--T:omaha_named-->
| Hand | Heads-up | 4 players | 6 players | 6p vs fair share |
|---|---|---|---|---|
| AAKK ds (AsAhKsKh) | 70.7% | 45.3% | 35.0% | 2.10x |
| KKQQ ds (KsKhQsQh) | 68.4% | 42.9% | 32.7% | 1.96x |
| AAJT ds (AsAhJsTh) | 70.7% | 43.4% | 32.1% | 1.93x |
| QQJJ ds (QsQhJsJh) | 66.7% | 41.1% | 31.2% | 1.87x |
| AA98 ds (AsAh9s8h) | 70.1% | 41.9% | 30.0% | 1.80x |
| KKJT ds (KsKhJsTh) | 67.5% | 40.4% | 29.8% | 1.79x |
| QQJT ds (QsQhJsTh) | 65.1% | 38.3% | 28.0% | 1.68x |
| AKQJ ds (AsKhQsJh) | 61.2% | 37.3% | 27.7% | 1.66x |
| AKQJ ds (AsKsQhJh) | 61.0% | 37.0% | 27.2% | 1.63x |
| KQJT ds (KsQhJsTh) | 59.3% | 36.1% | 27.1% | 1.63x |
| KQJT ds (KsQsJhTh) | 58.9% | 35.8% | 26.5% | 1.59x |
| JJT9 ds (JsJhTs9h) | 63.4% | 36.3% | 26.4% | 1.58x |
| AAKQ ss (AsAhKsQd) | 66.2% | 37.5% | 26.3% | 1.58x |
| AAKK rainbow (AsAhKdKc) | 65.1% | 36.5% | 26.0% | 1.56x |
| 9988 ds (9s9h8s8h) | 60.5% | 35.2% | 25.5% | 1.53x |
| QJT9 ds (QsJsTh9h) | 57.4% | 34.6% | 25.3% | 1.52x |
| AKQJ ss (AsKsQdJc) | 58.0% | 33.3% | 23.9% | 1.43x |
| JT98 ds (JsTh9s8h) | 55.9% | 33.0% | 23.8% | 1.43x |
| TT98 ds (TsTh9s8h) | 60.7% | 33.7% | 23.8% | 1.43x |
| JT98 ds (JsTs9h8h) | 55.6% | 32.7% | 23.6% | 1.42x |
| AAJT rainbow (AsAhJdTc) | 65.5% | 35.0% | 23.3% | 1.40x |
| KKQJ rainbow (KsKhQdJc) | 61.0% | 31.7% | 21.5% | 1.29x |
| T987 ds (Ts9s8h7h) | 53.1% | 30.4% | 21.4% | 1.28x |
| 9876 ds (9s8h7s6h) | 50.8% | 28.7% | 20.0% | 1.20x |
| 9876 ds (9s8s7h6h) | 50.9% | 28.5% | 19.9% | 1.19x |
| AKT2 ss (AsKsTh2d) | 53.5% | 28.6% | 19.5% | 1.17x |
| AKQJ rainbow (AsKdQhJc) | 54.9% | 28.9% | 19.3% | 1.16x |
| A543 ds (As5s4h3h) | 50.0% | 27.5% | 19.2% | 1.15x |
| 8765 ds (8s7s6h5h) | 48.7% | 27.6% | 19.1% | 1.14x |
| JT98 rainbow (JsTd9c8h) | 49.6% | 26.4% | 18.5% | 1.11x |
| 7654 ds (7s6s5h4h) | 47.1% | 26.7% | 18.5% | 1.11x |
| AAAK ss (AsAhAdKs) | 60.3% | 28.8% | 17.8% | 1.07x |
| 2233 ds (2s2h3s3h) | 46.3% | 26.7% | 17.8% | 1.07x |
| AA72 rainbow (AsAh7c2d) | 61.2% | 29.1% | 17.8% | 1.07x |
| KJ85 ss (KsJs8h5d) | 51.9% | 26.1% | 17.5% | 1.05x |
| A234 ds (As2s3h4h) | 47.0% | 25.0% | 17.2% | 1.03x |
| 6543 ds (6s5s4h3h) | 44.4% | 25.1% | 17.0% | 1.02x |
| A872 ss (As8s7h2c) | 49.2% | 24.3% | 16.2% | 0.98x |
| AQ62 ss (AsQs6h2d) | 48.9% | 24.3% | 16.2% | 0.97x |
| 9876 rainbow (9s8d7c6h) | 44.5% | 22.8% | 15.6% | 0.93x |
| KK72 rainbow (KsKh7c2d) | 56.7% | 25.0% | 15.3% | 0.92x |
| Q963 ss (Qs9s6h3d) | 48.1% | 23.3% | 15.2% | 0.92x |
| 2345 ds (2s3s4h5h) | 40.8% | 22.5% | 14.8% | 0.89x |
| 5432 ds (5s4s3h2h) | 41.0% | 22.4% | 14.8% | 0.89x |
| AJ94 rainbow (AsJh9d4c) | 49.0% | 22.0% | 13.2% | 0.79x |
| 8542 rainbow (8s5d4c2h) | 37.2% | 17.4% | 11.3% | 0.68x |
| J852 rainbow (Js8h5d2c) | 41.4% | 17.8% | 10.8% | 0.65x |
| T742 rainbow (Ts7d4c2h) | 38.0% | 15.8% | 9.7% | 0.58x |
| 9632 rainbow (9s6h3d2c) | 36.4% | 15.5% | 9.4% | 0.57x |
| 7432 rainbow (7s4h3d2c) | 33.1% | 14.8% | 9.3% | 0.56x |
| 2223 rainbow (2s2h2d3c) | 21.7% | 8.7% | 5.3% | 0.32x |
| 2222 rainbow (2s2h2d2c) | 9.3% | 0.5% | 0.1% | 0.01x |
<!--/T-->

What makes a hand good, at 6-handed:

<!--T:omaha_features_N6-->
Fair share with 6 players = 16.7%. Index = equity / fair share.


**By suits**

| Feature | Frequency | Equity | Index |
|---|---|---|---|
| double-suited | 13.5% | 19.9% | 1.19 |
| single-suited | 58.4% | 16.7% | 1.00 |
| rainbow | 10.5% | 13.6% | 0.81 |
| three of one suit | 16.5% | 16.0% | 0.96 |
| four of one suit | 1.1% | 14.9% | 0.90 |


**By pairs**

| Feature | Frequency | Equity | Index |
|---|---|---|---|
| no pair | 67.6% | 16.1% | 0.96 |
| one pair | 30.4% | 18.0% | 1.08 |
| two pair | 1.0% | 22.3% | 1.34 |
| trips | 0.9% | 10.0% | 0.60 |
| quads | 0.0% | 1.1% | 0.06 |


**By connectedness (unpaired hands)**

| Feature | Frequency | Equity | Index |
|---|---|---|---|
| rundown (4 ranks within 4, e.g. 9876) | 1.0% | 18.5% | 1.11 |
| one-gap rundown (within 5, e.g. 9865) | 2.8% | 18.0% | 1.08 |
| within 6 (e.g. 9864) | 5.1% | 16.9% | 1.01 |
| 3 cards within a 5-window | 31.9% | 16.3% | 0.98 |
| disconnected | 26.8% | 15.4% | 0.92 |


**Ace suited to another card?**

| Feature | Frequency | Equity | Index |
|---|---|---|---|
| no | 83.0% | 16.1% | 0.96 |
| yes | 17.0% | 19.6% | 1.18 |


**Number of T-A cards**

| Feature | Frequency | Equity | Index |
|---|---|---|---|
| 0 | 13.3% | 14.6% | 0.87 |
| 1 | 36.6% | 14.8% | 0.89 |
| 2 | 34.8% | 17.5% | 1.05 |
| 3 | 13.5% | 20.6% | 1.24 |
| 4 | 1.8% | 24.1% | 1.45 |


**Unpaired hands: suits x connectedness (index vs fair share)**

| Connectedness | double-suited | single-suited | rainbow |
|---|---|---|---|
| rundown (4 ranks within 4, e.g. 9876) | 1.25 | 1.12 | 0.95 |
| one-gap rundown (within 5, e.g. 9865) | 1.23 | 1.08 | 0.89 |
| within 6 (e.g. 9864) | 1.18 | 1.01 | 0.84 |
| 3 cards within a 5-window | 1.16 | 0.98 | 0.78 |
| disconnected | 1.12 | 0.92 | 0.72 |


**Pairs x suits (index vs fair share)**

| Pairs | double-suited | single-suited | rainbow |
|---|---|---|---|
| no pair | 1.15 | 0.96 | 0.77 |
| one pair | 1.27 | 1.08 | 0.90 |
| two pair | 1.51 | 1.34 | 1.14 |
<!--/T-->

Takeaways:
* **Double-suited** is worth +19% over average; **rainbow** −19%. **An ace suited to another card** (nut-flush potential) +18%.
* **High, connected cards** (3-4 cards T-A) add 24-45%. Connectedness matters much more with suits: a rainbow rundown is only average.
* **Trips in your hand are terrible** (index 0.60): you've killed your own set outs. Quads (2222) are nearly dead.
* **Single high pairs need help.** KK72 rainbow is below average 6-handed (0.92×).
* Use this to **set expectations on the flop**. With a junk rainbow hand you should be ready to check-fold most flops. With AAKKds, the flop will often give you a nut draw.

## 3. Flop: equity of each made hand vs the field

<!--T:omaha_flop_made-->
| Hand | How often (6p) | 3 players | 4 players | 5 players | 6 players | 7 players | 8 players | 9 players |
|---|---|---|---|---|---|---|---|---|
| nothing | 26.69% | 21.0% | 15.4% | 12.2% | 10.0% | 8.6% | 7.4% | 6.5% |
| pair (not top pair) | 35.94% | 26.9% | 19.1% | 14.7% | 11.8% | 9.9% | 8.4% | 7.3% |
| top pair | 12.14% | 37.7% | 26.5% | 19.9% | 15.8% | 13.0% | 10.9% | 9.5% |
| overpair | 7.12% | 35.4% | 24.9% | 18.7% | 15.0% | 12.4% | 10.8% | 9.5% |
| two pair (not top two) | 5.44% | 45.9% | 34.4% | 27.4% | 22.9% | 19.9% | 17.5% | 15.8% |
| top two pair | 3.14% | 53.7% | 42.4% | 35.0% | 30.4% | 26.3% | 24.1% | 22.0% |
| trips (board pair) | 2.11% | 70.5% | 60.3% | 52.7% | 46.8% | 41.7% | 37.7% | 34.1% |
| bottom set | 1.22% | 64.0% | 51.7% | 42.9% | 36.7% | 31.0% | 26.9% | 23.7% |
| middle set | 1.22% | 67.3% | 58.0% | 49.5% | 44.0% | 39.1% | 35.1% | 31.5% |
| top set | 1.24% | 71.8% | 63.9% | 57.0% | 52.4% | 48.0% | 44.7% | 42.6% |
| straight (non-nut) | 0.61% | 57.0% | 43.8% | 34.4% | 27.5% | 22.2% | 18.6% | 15.2% |
| nut straight | 1.30% | 69.6% | 58.7% | 50.9% | 44.3% | 38.8% | 34.4% | 30.2% |
| flush (non-nut) | 0.73% | 75.5% | 64.1% | 57.3% | 48.8% | 43.5% | 37.5% | 33.0% |
| nut flush | 0.20% | 90.0% | 85.2% | 81.1% | 76.4% | 74.1% | 70.8% | 69.0% |
| full house or better | 0.88% | 88.9% | 84.4% | 81.0% | 77.2% | 73.6% | 70.5% | 67.2% |
<!--/T-->

**Draws** (with no better than a non-top pair):

<!--T:omaha_flop_draws-->
_Draws with at most a non-top pair_

| Draw | How often (6p) | 3 players | 4 players | 5 players | 6 players | 7 players | 8 players | 9 players |
|---|---|---|---|---|---|---|---|---|
| no draw | 33.01% | 18.1% | 11.6% | 8.3% | 6.3% | 5.1% | 4.2% | 3.6% |
| small straight draw (1-7 outs) | 14.24% | 24.4% | 17.6% | 13.6% | 11.0% | 9.1% | 7.9% | 6.9% |
| open-ender type (8-12 outs) | 5.70% | 31.7% | 24.4% | 19.7% | 16.3% | 13.9% | 11.9% | 10.4% |
| wrap (13+ outs) | 1.51% | 39.6% | 32.9% | 26.9% | 23.3% | 20.0% | 17.5% | 15.0% |
| flush draw (non-nut) | 3.98% | 38.2% | 29.6% | 24.2% | 19.9% | 16.8% | 14.3% | 12.2% |
| flush draw (non-nut) + small straight draw (1-7 outs) | 2.51% | 44.0% | 36.1% | 30.3% | 26.1% | 22.4% | 19.6% | 17.1% |
| flush draw (non-nut) + open-ender type (8-12 outs) | 0.17% | 51.1% | 43.5% | 37.6% | 32.5% | 29.2% | 24.8% | 22.7% |
| flush draw (non-nut) + wrap (13+ outs) | 0.09% | 58.0% | 49.8% | 41.5% | 37.3% | 33.6% | 30.5% | 25.2% |
| nut flush draw | 0.87% | 44.9% | 37.8% | 33.5% | 29.5% | 28.2% | 26.0% | 23.9% |
| nut flush draw + small straight draw (1-7 outs) | 0.52% | 50.6% | 44.2% | 38.8% | 35.2% | 33.5% | 31.4% | 30.6% |
| nut flush draw + open-ender type (8-12 outs) | 0.04% | 53.9% | 56.2% | 51.9% | 44.1% | 44.1% | 39.4% | 38.8% |
<!--/T-->

**Combined made hand × draw at 6-handed** (equity vs 5 random hands):

<!--T:omaha_flop_grid6-->
| Made hand \ draw | no draw | small straight draw (1-7 outs) | open-ender type (8-12 outs) | wrap (13+ outs) | flush draw (non-nut) | flush draw (non-nut) + small straight draw (1-7 outs) | nut flush draw | nut flush draw + small straight draw (1-7 outs) |
|---|---|---|---|---|---|---|---|---|
| nothing | 4% | 9% | 15% | 22% | 17% | 25% | 25% | 32% |
| pair (not top pair) | 8% | 12% | 18% | 26% | 22% | 28% | 34% | 40% |
| top pair | 12% | 16% | 20% | 28% | 27% | 32% | 40% | 44% |
| overpair | 12% | 15% | 21% |  | 25% | 30% | 35% | 39% |
| two pair (not top two) | 21% | 24% | 27% |  | 36% | 40% | 49% |  |
| top two pair | 29% | 30% | 31% |  | 42% |  |  |  |
| trips (board pair) | 46% | 48% | 51% |  | 50% |  |  |  |
| bottom set | 36% | 36% |  |  | 47% |  |  |  |
| middle set | 43% | 45% |  |  | 55% |  |  |  |
| top set | 51% | 51% |  |  | 65% |  |  |  |
| straight (non-nut) | 26% |  |  |  | 39% |  |  |  |
| nut straight | 43% |  |  |  | 53% |  |  |  |
| flush (non-nut) | 49% |  |  |  |  |  |  |  |
| nut flush | 76% |  |  |  |  |  |  |  |
| full house or better | 77% |  |  |  |  |  |  |  |
<!--/T-->

### Heads-up matchups on the flop (after the action narrows to two players)

<!--T:omaha_hu_archetypes_flop-->
| Hero \ villain | A | B | C | D | E | F | G | H | I | J |
|---|---|---|---|---|---|---|---|---|---|---|
| top set, no draw |  | 92% | 91% | 37% | 36% | 57% | 71% | 49% | 95% | 33% |
| bottom set, no draw | 8% |  | 73% | 35% | 34% | 57% | 70% | 49% | 91% | 34% |
| top two pair | 9% | 27% | 50% | 26% | 30% | 53% | 60% | 43% | 79% | 19% |
| nut straight, no redraw | 63% | 65% | 74% | 50% | 88% | 76% | 62% |  | 94% | 3% |
| non-nut straight | 64% | 66% | 70% | 12% | 50% | 74% | 66% |  | 94% | 2% |
| wrap 13+ outs (no pair) | 43% | 43% | 47% | 24% | 26% | 50% | 38% | 31% | 57% | 0% |
| nut flush draw only | 29% | 30% | 40% | 38% | 34% | 62% |  |  | 52% |  |
| NFD + 8+ straight outs | 51% | 51% | 57% |  |  | 69% |  |  | 69% |  |
| top pair, no draw | 5% | 9% | 21% | 6% | 6% | 43% | 48% | 31% | 50% | 3% |
| nut flush | 67% | 66% | 81% | 97% | 98% | 100% |  |  | 97% |  |

**A** = top set, no draw  **B** = bottom set, no draw  **C** = top two pair  **D** = nut straight, no redraw  **E** = non-nut straight  **F** = wrap 13+ outs (no pair)  **G** = nut flush draw only  **H** = NFD + 8+ straight outs  **I** = top pair, no draw  **J** = nut flush
<!--/T-->

Full made-vs-made heads-up matrix: [`results/tables/omaha_hu_flop.md`](results/tables/omaha_hu_flop.md).

Reading these:
* **Top set vs a 13+ out wrap is only 57/43.** Bottom set vs a wrap is the same coin flip. Big wraps are almost never in bad shape.
* **Nut straight with no redraw vs a 13+ out wrap: 76%.** Vs a set: 63-65%. Vs top two: 74%.
* **A non-nut straight vs the nut straight: 12%.** This is the "second-best hand" disaster.
* **A naked nut flush draw is a dog to everything made** (29-40%). It's a strong *multiway* hand because of the pot odds, but it's weak heads-up against a made hand.
* **Top pair (no draw) is drawing thin against any two pair or set** (5-21%). Don't put money in with it.

## 4. Turn: equity with one card to come

<!--T:omaha_turn_made-->
| Hand | How often (6p) | 3 players | 4 players | 5 players | 6 players | 7 players | 8 players | 9 players |
|---|---|---|---|---|---|---|---|---|
| nothing | 17.66% | 13.2% | 9.5% | 7.6% | 6.2% | 5.3% | 4.6% | 4.1% |
| pair (not top pair) | 35.11% | 19.9% | 12.8% | 9.3% | 7.2% | 5.9% | 5.0% | 4.2% |
| top pair | 9.13% | 31.9% | 20.3% | 13.9% | 10.1% | 7.8% | 6.1% | 5.1% |
| overpair | 5.06% | 31.6% | 20.6% | 14.3% | 10.6% | 8.3% | 6.8% | 5.8% |
| two pair (not top two) | 10.63% | 40.2% | 28.0% | 20.7% | 16.2% | 13.3% | 11.3% | 9.8% |
| top two pair | 2.89% | 50.6% | 38.6% | 30.5% | 25.0% | 20.8% | 18.3% | 16.2% |
| trips (board pair) | 3.28% | 64.4% | 53.1% | 44.2% | 37.3% | 31.8% | 27.3% | 23.7% |
| bottom set | 1.99% | 60.3% | 48.2% | 39.1% | 32.5% | 27.1% | 23.2% | 19.9% |
| middle set | 1.01% | 64.5% | 54.7% | 45.0% | 39.8% | 34.5% | 30.9% | 28.5% |
| top set | 1.01% | 67.4% | 59.2% | 50.6% | 45.4% | 41.0% | 37.5% | 35.2% |
| straight (non-nut) | 2.51% | 57.5% | 44.4% | 35.0% | 27.9% | 22.5% | 18.3% | 14.8% |
| nut straight | 3.42% | 72.5% | 62.2% | 54.4% | 48.2% | 42.4% | 38.1% | 34.2% |
| flush (non-nut) | 2.51% | 74.3% | 63.5% | 55.4% | 47.4% | 41.4% | 35.7% | 30.8% |
| nut flush | 0.69% | 88.9% | 84.3% | 80.3% | 76.2% | 73.3% | 70.6% | 68.5% |
| full house or better | 3.12% | 88.3% | 83.2% | 79.2% | 75.3% | 71.6% | 68.1% | 64.9% |
<!--/T-->

<!--T:omaha_turn_draws-->
_Draws with at most a non-top pair (one card to come)_

| Draw | How often (6p) | 3 players | 4 players | 5 players | 6 players | 7 players | 8 players | 9 players |
|---|---|---|---|---|---|---|---|---|
| no draw | 17.82% | 11.1% | 5.6% | 3.3% | 2.1% | 1.5% | 1.1% | 0.8% |
| small straight draw (1-7 outs) | 14.41% | 15.1% | 9.5% | 6.6% | 5.0% | 4.0% | 3.3% | 2.8% |
| open-ender type (8-12 outs) | 7.81% | 20.3% | 14.3% | 11.2% | 8.9% | 7.5% | 6.5% | 5.6% |
| wrap (13+ outs) | 1.65% | 24.9% | 19.8% | 16.5% | 14.3% | 12.4% | 10.8% | 9.5% |
| flush draw (non-nut) | 3.85% | 24.1% | 16.8% | 12.8% | 9.9% | 8.3% | 6.9% | 5.6% |
| flush draw (non-nut) + small straight draw (1-7 outs) | 4.78% | 29.5% | 22.4% | 18.4% | 15.4% | 13.0% | 11.2% | 9.8% |
| flush draw (non-nut) + open-ender type (8-12 outs) | 0.37% | 33.6% | 29.0% | 24.6% | 21.7% | 20.2% | 17.1% | 14.7% |
| flush draw (non-nut) + wrap (13+ outs) | 0.18% | 39.9% | 34.7% | 30.4% | 25.7% | 24.3% | 20.6% | 18.5% |
| nut flush draw | 0.83% | 28.8% | 21.4% | 18.5% | 15.6% | 14.1% | 12.7% | 11.5% |
| nut flush draw + small straight draw (1-7 outs) | 0.99% | 33.6% | 27.1% | 23.2% | 21.0% | 19.8% | 18.3% | 16.8% |
| nut flush draw + open-ender type (8-12 outs) | 0.07% | 40.1% | 35.5% | 32.7% | 27.3% | 26.9% | 25.3% | 24.1% |
<!--/T-->

## 5. River: how often each hand is best (vs N−1 random hands that checked down)

6-handed (columns = top card of the hand, e.g. "Flush, K" = king-high flush):

<!--T:omaha_river_N6-->
| River hand | Avg | A | K | Q | J | T | 9 | 8 | 7 | 6 | 5 | 4 | 3 | 2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| High card | 0.0% | 0% | 0% | 0% |  |  |  |  |  |  |  |  |  |  |
| Pair | 0.1% | 1% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| Two pair | 4.7% | 9% | 7% | 5% | 4% | 2% | 2% | 2% | 1% | 1% | 1% | 1% | 1% |  |
| Trips | 21.3% | 27% | 27% | 24% | 22% | 21% | 21% | 20% | 20% | 19% | 17% | 19% | 20% | 20% |
| Straight | 39.3% | 52% | 42% | 38% | 37% | 37% | 37% | 37% | 37% | 37% | 35% |  |  |  |
| Flush | 51.7% | 62% | 51% | 43% | 39% | 35% | 31% | 31% |  |  |  |  |  |  |
| Full house | 71.6% | 84% | 82% | 81% | 78% | 76% | 74% | 71% | 69% | 67% | 66% | 62% | 60% | 59% |
| Quads | 99.5% | 100% | 100% | 100% | 100% | 99% | 99% | 99% | 99% | 99% | 99% | 99% | 99% | 99% |
| Str. flush | 99.8% |  |  |  |  |  |  |  |  |  |  |  |  |  |
<!--/T-->

These are unconditional numbers. When someone bets or raises, their range is far stronger, so discount your hand a lot.

---

## 6. Strategy: how to play each street

### Flop (everyone in, SPR ≈ 8 at 6-handed)

**Bet / raise for value and protection**, ideally 2/3 to full pot. That charges the big wraps and flush draws that make up a large share of every field:
* **Top set** (52% at 6-handed, 3.1× fair share). Raise it. It's vulnerable but well ahead.
* **Nut straight** (44%, 2.7×), **especially with a flush redraw** (53%). On a two-tone board with no redraw, bet and be willing to get it in, but expect a fair amount of coin flips.
* **Nut flush** (76%) / **full house+** (77%). Slow play only when the board is dry *and* you hold blockers.
* **Middle set / bottom set** (44% / 37%). Bet, but don't stack off over heavy action on wet boards; bottom set multiway is often the second-best set.
* **Big combo draws**: NFD + open-ender/wrap (≈44% at 6-handed), NFD + top pair (40%), NFD + two pair (49%). These are *strong* multiway hands: 2.5-3× fair share, plus fold equity. Bet or raise them, especially in position.

**Check / call carefully:**
* **Top two pair** (30% at 6-handed, 1.8×) and **any two pair** (23%). These are pot-control hands multiway. Bet for protection when it's checked to you on dry boards. Fold to a raise on wet boards.
* **Naked big wraps (13+ outs)** (22-23%) and the **naked nut flush draw** (25-29%). Call when the price is right (they need roughly 3:1 to call multiway, which you usually get). Raise them as semi-bluffs only in position.
* **Non-nut straights** (27% at 6-handed). Close to a check-fold against big action. The nut straight crushes them (88%).

**Check / fold:**
* One pair, overpairs (AA without a set is 12-15% at 6-handed!), small draws, non-nut flush draws without other equity.
* Rough rule: **if your flop equity is below about 1.3× fair share (≈22% at 6-handed), you need a big price or a nut draw to continue.**

### Turn

* Equities polarise: made nut hands go up, weak draws collapse (e.g. a naked non-nut flush draw drops to 10% at 6-handed).
* **Bet big (pot or near pot)** with the nuts and nut redraws. Most turns are "bet big or check".
* **Draws on the turn:** heads-up, your equity is about outs / 44 (16 clean outs ≈ 36%). Against 5 random hands, a 13+ out wrap has only 14%, because some of your outs give other players better hands. A half-pot bet needs 25% equity and a pot-sized bet needs 33% (see [Fundamentals §2](00_fundamentals.md)). So call half-pot heads-up with 12+ clean outs to the nuts, and fold weaker or non-nut draws to pot-sized bets.
* **Turn card pairs the board?** Sets and two pair improve to full houses. Straights and flushes shrink. If you're holding the straight and get raised on a paired board, **you're usually beaten.**

### River

* **Value-bet only hands that beat what calls.** At 6-handed, a raw flush is best only 52% of the time against random hands, and much less often against a caller. Value-bet the **nut flush, top full house, nut straight on a board with no flush or pair**. Check-call or check-fold the rest.
* **Bluffs**: almost none multiway. Heads-up, bluff with **nut blockers**: hold the A of the flush suit when the flush comes in, or the card that makes the nut straight.
* **Facing a big river bet multiway**: you need the nuts or near-nuts. Second-best hands lose most of the money in Omaha.

### Position and blockers

* Postflop action order is fixed relative to the button. **Play much tighter from early seats** (you'll face bets and raises behind you) and **steal more in late position** when it's checked to you.
* **Blockers matter more than in Hold'em**: holding the A♠ means nobody else has the nut spade flush. On a three-spade board, a bet from you is far more credible, and it makes a good bluff.

### Bet sizing

* If you play **pot-limit**: pot-sized bets on the flop and turn get the money in by the river at SPR 8.
* If you play **no-limit**: you can shove the turn with the nuts or nut redraws when SPR ≤ 2. **Don't overbet-bluff multiway.** Overbets are for nut-heavy ranges only.

### Quick reference (6-handed, flop)

| Hand | Equity vs 5 randoms | Action |
|---|---|---|
| Nut flush / full house | 76-77% | Bet / raise, build the pot |
| Top set + flush draw | 65% | Raise, get it in |
| Top set (no draw) | 51-52% | Bet / raise; vs heavy action on a wet board, call rather than re-raise |
| Nut straight + flush redraw | 53% | Raise, get it in |
| Nut straight (no redraw) | 43-44% | Bet / raise; careful on flush boards |
| NFD + open-ender/wrap, NFD + top pair | 40-44% | Bet / raise in position, call out of position |
| Middle / bottom set | 36-44% | Bet, don't go broke on wet boards |
| Top two pair | 29-30% | Pot control; bet when checked to on dry boards |
| Naked 13+ wrap | 22% | Call at a good price; semi-bluff in position |
| Naked NFD | 25% | Call at a good price |
| Non-nut straight | 26% | Check-call small, fold to big action |
| Top pair / overpair (no draw) | 12% | Check, fold to a bet |
| Nothing / small draw | 4-9% | Check-fold |
