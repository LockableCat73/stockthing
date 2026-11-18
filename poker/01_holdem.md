# 01 · Standard No-Limit Texas Hold'em: 5/10, 500 stacks (50 bb)

Contents: preflop opening chart → facing an open (3-bet / call / fold) → facing a 3-bet (4-bet jam) → short-stack push/fold (exact Nash) → re-shoving → postflop c-bet strategy by board texture (range-vs-range simulation) → turn and river → home-game adjustments.

> **Where the numbers come from.** I built a 169×169 heads-up equity matrix for every starting-hand class (30,000 deals per matchup, exact card-removal weights) and multiway equities vs 1-8 random hands (200,000 deals per cell). On top of that:
> * **Push/fold, re-shove and 4-bet-jam charts** are *solved* equilibria (fictitious play, 2,000-3,000 iterations) of the all-in subgames. These are true GTO answers for those spots.
> * **Opening ranges** follow the standard solver structure for 50 bb with no ante. I can't simulate every post-flop line, so their widths are set by hand. They're ordered by the simulated equity and playability numbers.
> * **Facing-an-open charts** come from equity vs the opener's range plus pot odds, with an explicit equity-realisation model (listed in §3).
> * **Post-flop c-bet guidance** comes from simulating each opening range against each calling range on 3 million flops.

---

## 0. Seats

9-handed seat names: **UTG, UTG+1, MP, LJ (lojack), HJ (hijack), CO (cutoff), BTN, SB, BB**.
With fewer players, **delete seats from the front**: 6-handed = LJ, HJ, CO, BTN, SB, BB; 7-handed starts at MP; 8-handed at UTG+1.

## 1. Opening (raise first in)

**Size:** 2.5 bb (25) from every seat. **SB: 3 bb (30)**. **Isolating limpers: 4 bb + 1 bb per limper** (e.g. 50 over one limper, 60 over two). Never open-limp, except as SB vs BB if you specifically want to (raise-or-fold is simpler and close to optimal).

<!--T:holdem_open_chart-->
Each cell shows the EARLIEST seat that opens the hand (it is also opened from every later seat).
UT = UTG, U1 = UTG+1.

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|UT|UT|UT|UT|UT|U1|MP|LJ|LJ|UT|U1|MP|LJ|
|**K**|UT|UT|UT|UT|UT|MP|HJ|HJ|CO|BTN|BTN|BTN|BTN|
|**Q**|UT|UT|UT|UT|UT|MP|HJ|BTN|BTN|BTN||||
|**J**|UT|MP|LJ|UT|UT|MP|HJ|BTN||||||
|**T**|MP|HJ|HJ|HJ|UT|U1|LJ|BTN||||||
|**9**|HJ|BTN|BTN|BTN|BTN|UT|MP|HJ|BTN|||||
|**8**|CO|BTN|||BTN|BTN|UT|LJ|CO|BTN||||
|**7**|BTN|||||||UT|HJ|CO||||
|**6**|BTN||||||||U1|HJ|BTN|||
|**5**|CO|||||||||MP|CO|BTN||
|**4**|BTN||||||||||LJ|BTN||
|**3**|BTN|||||||||||HJ||
|**2**|BTN||||||||||||CO|

| Seat | Open % | Range |
|---|---|---|
| UTG | 10.6% | 77+, ATs+, A5s, KTs+, QTs+, JTs, AJo+, KQo |
| UTG+1 | 11.9% | 66+, A9s+, A5s-A4s, KTs+, QTs+, JTs, T9s, AJo+, KQo |
| MP | 16.0% | 55+, A8s+, A5s-A3s, K9s+, Q9s+, J9s+, T9s, 98s, ATo+, KJo+ |
| LJ | 18.9% | 44+, A2s+, K9s+, Q9s+, J9s+, T8s+, 98s, 87s, ATo+, KJo+, QJo |
| HJ | 25.0% | 33+, A2s+, K7s+, Q8s+, J8s+, T8s+, 97s+, 87s, 76s, 65s, A9o+, KTo+, QTo+, JTo |
| CO | 28.5% | 22+, A2s+, K6s+, Q8s+, J8s+, T8s+, 97s+, 86s+, 75s+, 65s, 54s, A8o+, A5o, KTo+, QTo+, JTo |
| BTN | 43.6% | 22+, A2s+, K2s+, Q5s+, J7s+, T7s+, 96s+, 85s+, 75s+, 64s+, 53s+, 43s, A2o+, K8o+, Q9o+, J9o+, T8o+, 98o |
| SB | 40.0% | 22+, A2s+, K2s+, Q5s+, J7s+, T7s+, 96s+, 86s+, 75s+, 64s+, 54s, A2o+, K9o+, Q9o+, J9o+, T9o |
<!--/T-->

Why the shape looks like this:
* **Suited aces and suited connectors** open earlier than offsuit broadways of similar equity. They realise more equity (flushes, straights, nut potential) and are much easier to play post-flop.
* **Small pairs** open from MP onward. At 50 bb they set-mine less well than at 100 bb, so they're trimmed from the very earliest seats.
* **Weak offsuit hands** (K8o, Q9o, J9o, T8o, 98o) only open from the button or SB, where only the blinds are left to act.

## 2. Facing an open

The charts below were computed with these rules:
* **Value 3-bet** if the hand has more than 50% equity against the opener's *continuing* range (the top 25% of their opening range).
* **Call** if (equity vs the opening range) × (realisation factor) > the pot odds.
* **Bluff 3-bet** with blocker / playable suited hands (A5s-A2s first, then suited kings, suited connectors). Volume is about 70% of the value 3-bets.
* **SB and early seats play 3-bet-or-fold** (linear, merged ranges). The BTN gets to flat. The BB closes the action.

Realisation model (an assumption, not simulated): BB out of position realises 80% of its equity with pairs, 86-90% with suited hands, 80% with offsuit broadway, 74% with offsuit aces, 64-72% with other offsuit hands. In position, add 6%. BB vs SB (in position, closing the action), add 14%.

**3-bet sizes at 50 bb:** in position 3× the open (7.5). Out of position 4-4.5× (10-11). Over a limper/caller add 1 open-size.

<!--T:holdem_defence-->
Legend: **3B** = 3-bet for value · 3b = 3-bet bluff (fold to a 4-bet) · C = call · blank = fold

#### BTN vs UTG open (2.5x)

3-bet value 0.9% · 3-bet bluff 0.9% · call 5.6% · fold 92.6% (price: call 2.5 to win 4 → 38% raw equity needed)

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|**3B**|C|C|C|C|||||3b|3b|3b||
|**K**|C|**3B**|C|||||||||||
|**Q**|C||C|||||||||||
|**J**||||C||||||||||
|**T**|||||C|||||||||
|**9**||||||C||||||||
|**8**|||||||C|||||||
|**7**||||||||||||||
|**6**||||||||||||||
|**5**||||||||||||||
|**4**||||||||||||||
|**3**||||||||||||||
|**2**||||||||||||||


#### SB vs UTG open (2.5x)

3-bet value 3.8% · 3-bet bluff 1.5% · call 0.0% · fold 94.7% (price: call 2 to win 4 → 33% raw equity needed)

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|**3B**|**3B**|**3B**|||||||3b|3b|3b|3b|
|**K**|**3B**|**3B**||||3b||||||||
|**Q**|||**3B**|||||||||||
|**J**||||**3B**||||||||||
|**T**|||||**3B**|||||||||
|**9**||||||||||||||
|**8**||||||||||||||
|**7**||||||||||||||
|**6**||||||||||||||
|**5**||||||||||||||
|**4**||||||||||||||
|**3**||||||||||||||
|**2**||||||||||||||


#### BB vs UTG open (2.5x)

3-bet value 0.9% · 3-bet bluff 0.9% · call 26.4% · fold 71.8% (price: call 1.5 to win 4 → 27% raw equity needed)

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|**3B**|C|C|C|C|C|C|C|C|3b|3b|3b|C|
|**K**|C|**3B**|C|C|C|C|C|C|C|C|C|C|C|
|**Q**|C|C|C|C|C|C|C|C|C|C||||
|**J**|C|C||C|C|C|C|||||||
|**T**|C|C|||C|C|C|C||||||
|**9**|C|||||C|C|C|C|||||
|**8**|||||||C|C|C|C||||
|**7**||||||||C|C|C||||
|**6**|||||||||C|C|C|||
|**5**||||||||||C|C|C||
|**4**|||||||||||C|C|C|
|**3**||||||||||||C||
|**2**|||||||||||||C|


#### BTN vs MP open (2.5x)

3-bet value 1.7% · 3-bet bluff 1.2% · call 9.7% · fold 87.5% (price: call 2.5 to win 4 → 38% raw equity needed)

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|**3B**|**3B**|C|C|C|C|C|C|C|3b|3b|3b|3b|
|**K**|C|**3B**|C|C||||||||||
|**Q**|C||**3B**|C|C|||||||||
|**J**|C|||C||||||||||
|**T**|C||||C|||||||||
|**9**||||||C||||||||
|**8**|||||||C|||||||
|**7**||||||||C||||||
|**6**|||||||||C|||||
|**5**||||||||||||||
|**4**||||||||||||||
|**3**||||||||||||||
|**2**||||||||||||||


#### SB vs MP open (2.5x)

3-bet value 5.0% · 3-bet bluff 2.1% · call 0.0% · fold 92.9% (price: call 2 to win 4 → 33% raw equity needed)

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|**3B**|**3B**|**3B**|**3B**||||||3b|3b|3b|3b|
|**K**|**3B**|**3B**||||3b|3b|3b||||||
|**Q**|**3B**||**3B**|||||||||||
|**J**||||**3B**||||||||||
|**T**|||||**3B**|||||||||
|**9**||||||||||||||
|**8**||||||||||||||
|**7**||||||||||||||
|**6**||||||||||||||
|**5**||||||||||||||
|**4**||||||||||||||
|**3**||||||||||||||
|**2**||||||||||||||


#### BB vs MP open (2.5x)

3-bet value 1.7% · 3-bet bluff 1.2% · call 39.8% · fold 57.3% (price: call 1.5 to win 4 → 27% raw equity needed)

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|**3B**|**3B**|C|C|C|C|C|C|C|3b|3b|3b|3b|
|**K**|C|**3B**|C|C|C|C|C|C|C|C|C|C|C|
|**Q**|C|C|**3B**|C|C|C|C|C|C|C|C|C|C|
|**J**|C|C|C|C|C|C|C|C|C|C|C|C|C|
|**T**|C|C|C|C|C|C|C|C|C|C|C|||
|**9**|C|||||C|C|C|C|C||||
|**8**|C||||||C|C|C|C|C|||
|**7**|C|||||||C|C|C|C|||
|**6**|C||||||||C|C|C|C||
|**5**|C|||||||||C|C|C|C|
|**4**|C||||||||||C|C|C|
|**3**|C|||||||||||C|C|
|**2**|C||||||||||||C|


#### CO vs HJ open (2.5x)

3-bet value 6.6% · 3-bet bluff 2.7% · call 0.0% · fold 90.6% (price: call 2.5 to win 4 → 38% raw equity needed)

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|**3B**|**3B**|**3B**|**3B**|**3B**|||||3b|3b|3b|3b|
|**K**|**3B**|**3B**||||3b|3b|3b|3b|3b||||
|**Q**|**3B**||**3B**|||||||||||
|**J**|**3B**|||**3B**||||||||||
|**T**|||||**3B**|||||||||
|**9**||||||**3B**||||||||
|**8**||||||||||||||
|**7**||||||||||||||
|**6**||||||||||||||
|**5**||||||||||||||
|**4**||||||||||||||
|**3**||||||||||||||
|**2**||||||||||||||


#### BTN vs HJ open (2.5x)

3-bet value 3.0% · 3-bet bluff 2.1% · call 14.0% · fold 80.8% (price: call 2.5 to win 4 → 38% raw equity needed)

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|**3B**|**3B**|C|C|C|C|C|C|C|3b|3b|3b|3b|
|**K**|**3B**|**3B**|C|C|C|3b|3b|3b|C|||||
|**Q**|C|C|**3B**|C|C|||||||||
|**J**|C|C||**3B**|C|C||||||||
|**T**|C|C|||C|||||||||
|**9**|C|||||C||||||||
|**8**|||||||C|||||||
|**7**||||||||C||||||
|**6**|||||||||C|||||
|**5**||||||||||C||||
|**4**|||||||||||C|||
|**3**||||||||||||||
|**2**||||||||||||||


#### SB vs HJ open (2.5x)

3-bet value 6.6% · 3-bet bluff 2.7% · call 0.0% · fold 90.6% (price: call 2 to win 4 → 33% raw equity needed)

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|**3B**|**3B**|**3B**|**3B**|**3B**|||||3b|3b|3b|3b|
|**K**|**3B**|**3B**||||3b|3b|3b|3b|3b||||
|**Q**|**3B**||**3B**|||||||||||
|**J**|**3B**|||**3B**||||||||||
|**T**|||||**3B**|||||||||
|**9**||||||**3B**||||||||
|**8**||||||||||||||
|**7**||||||||||||||
|**6**||||||||||||||
|**5**||||||||||||||
|**4**||||||||||||||
|**3**||||||||||||||
|**2**||||||||||||||


#### BB vs HJ open (2.5x)

3-bet value 3.0% · 3-bet bluff 2.1% · call 40.6% · fold 54.3% (price: call 1.5 to win 4 → 27% raw equity needed)

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|**3B**|**3B**|C|C|C|C|C|C|C|3b|3b|3b|3b|
|**K**|**3B**|**3B**|C|C|C|3b|3b|3b|C|C|C|C|C|
|**Q**|C|C|**3B**|C|C|C|C|C|C|C|C|C|C|
|**J**|C|C|C|**3B**|C|C|C|C|C|C|C|C|C|
|**T**|C|C|C|C|C|C|C|C|C|C|C|C|C|
|**9**|C|||||C|C|C|C|C|C|C|C|
|**8**|C||||||C|C|C|C|C|C|C|
|**7**|C|||||||C|C|C|C|C|C|
|**6**|C||||||||C|C|C|C|C|
|**5**|C|||||||||C|C|C|C|
|**4**|C||||||||||C|C|C|
|**3**|C|||||||||||C|C|
|**2**|C||||||||||||C|


#### BTN vs CO open (2.5x)

3-bet value 3.5% · 3-bet bluff 2.7% · call 14.6% · fold 79.2% (price: call 2.5 to win 4 → 38% raw equity needed)

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|**3B**|**3B**|C|C|C|C|C|C|C|3b|3b|3b|3b|
|**K**|**3B**|**3B**|C|C|C|3b|3b|3b|3b|3b||||
|**Q**|C|C|**3B**|C|C|C||||||||
|**J**|C|C||**3B**|C|C||||||||
|**T**|C|C|||**3B**|C||||||||
|**9**|C|||||C|C|||||||
|**8**|||||||C|||||||
|**7**||||||||C||||||
|**6**|||||||||C|||||
|**5**||||||||||C||||
|**4**|||||||||||C|||
|**3**||||||||||||C||
|**2**||||||||||||||


#### SB vs CO open (2.5x)

3-bet value 8.3% · 3-bet bluff 3.3% · call 0.0% · fold 88.4% (price: call 2 to win 4 → 33% raw equity needed)

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|**3B**|**3B**|**3B**|**3B**|**3B**|||||3b|3b|3b|3b|
|**K**|**3B**|**3B**|**3B**|||3b|3b|3b|3b|3b||||
|**Q**|**3B**||**3B**|||3b||||||||
|**J**|**3B**|||**3B**||3b||||||||
|**T**|**3B**||||**3B**|||||||||
|**9**||||||**3B**||||||||
|**8**|||||||**3B**|||||||
|**7**||||||||||||||
|**6**||||||||||||||
|**5**||||||||||||||
|**4**||||||||||||||
|**3**||||||||||||||
|**2**||||||||||||||


#### BB vs CO open (2.5x)

3-bet value 3.5% · 3-bet bluff 2.7% · call 40.4% · fold 53.4% (price: call 1.5 to win 4 → 27% raw equity needed)

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|**3B**|**3B**|C|C|C|C|C|C|C|3b|3b|3b|3b|
|**K**|**3B**|**3B**|C|C|C|3b|3b|3b|3b|3b|C|C|C|
|**Q**|C|C|**3B**|C|C|C|C|C|C|C|C|C|C|
|**J**|C|C|C|**3B**|C|C|C|C|C|C|C|C|C|
|**T**|C|C|C|C|**3B**|C|C|C|C|C|C|C|C|
|**9**|C||||C|C|C|C|C|C|C|C|C|
|**8**|C||||||C|C|C|C|C|C|C|
|**7**|C|||||||C|C|C|C|C|C|
|**6**|C||||||||C|C|C|C|C|
|**5**|C|||||||||C|C|C|C|
|**4**|C||||||||||C|C|C|
|**3**|C|||||||||||C|C|
|**2**|C||||||||||||C|


#### SB vs BTN open (2.5x)

3-bet value 10.3% · 3-bet bluff 4.2% · call 0.0% · fold 85.5% (price: call 2 to win 4 → 33% raw equity needed)

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|**3B**|**3B**|**3B**|**3B**|**3B**|**3B**|**3B**|**3B**||3b|3b|3b|3b|
|**K**|**3B**|**3B**|**3B**|**3B**|**3B**|3b|3b|3b|3b|3b||||
|**Q**|**3B**||**3B**|||3b||||||||
|**J**|**3B**|||**3B**||3b||||||||
|**T**|**3B**||||**3B**||3b|||||||
|**9**||||||**3B**||3b||||||
|**8**|||||||**3B**||3b|||||
|**7**||||||||**3B**||||||
|**6**||||||||||||||
|**5**||||||||||||||
|**4**||||||||||||||
|**3**||||||||||||||
|**2**||||||||||||||


#### BB vs BTN open (2.5x)

3-bet value 5.1% · 3-bet bluff 3.6% · call 43.3% · fold 48.0% (price: call 1.5 to win 4 → 27% raw equity needed)

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|**3B**|**3B**|**3B**|C|C|C|C|C|C|3b|3b|3b|3b|
|**K**|**3B**|**3B**|C|C|C|3b|3b|3b|3b|3b|C|C|C|
|**Q**|**3B**|C|**3B**|C|C|3b|C|C|C|C|C|C|C|
|**J**|C|C|C|**3B**|C|3b|C|C|C|C|C|C|C|
|**T**|C|C|C|C|**3B**|C|3b|C|C|C|C|C|C|
|**9**|C|C|C||C|**3B**|C|C|C|C|C|C|C|
|**8**|C|C||||C|C|C|C|C|C|C|C|
|**7**|C|C||||||C|C|C|C|C|C|
|**6**|C|C|||||||C|C|C|C|C|
|**5**|C|||||||||C|C|C|C|
|**4**|C||||||||||C|C|C|
|**3**|C|||||||||||C|C|
|**2**|C||||||||||||C|


#### BB vs SB open (3x)

3-bet value 5.1% · 3-bet bluff 3.6% · call 39.7% · fold 51.6% (price: call 2 to win 4 → 33% raw equity needed)

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|**3B**|**3B**|**3B**|C|C|C|C|C|C|3b|3b|3b|3b|
|**K**|**3B**|**3B**|C|C|C|3b|3b|3b|3b|3b|C|C|C|
|**Q**|**3B**|C|**3B**|C|C|3b|C|C|C|C|C|C|C|
|**J**|C|C|C|**3B**|C|3b|C|C|C|C|C|C|C|
|**T**|C|C|C|C|**3B**|C|3b|C|C|C|C|C|C|
|**9**|C|C|||C|**3B**|C|C|C|C|C|C|C|
|**8**|C|C|||||C|C|C|C|C|C|C|
|**7**|C|||||||C|C|C|C|C|C|
|**6**|C||||||||C|C|C|C|C|
|**5**|C|||||||||C|C|C|C|
|**4**|C||||||||||C|C|C|
|**3**|C|||||||||||C|C|
|**2**|C||||||||||||C|
<!--/T-->

Notes on the defence charts:
* **BB vs BTN**: defends about 52% (≈9% 3-bet, 43% call). Fold the offsuit trash. Keep every suited hand.
* **BB vs UTG**: defends about 28%. Against an early-position range, offsuit hands are mostly dominated.
* **SB**: 3-bet or fold. Flatting from the SB invites the BB to squeeze, and you play the hand out of position.
* **Cold-calling** in the middle seats is mostly a mistake at 50 bb. Either 3-bet or fold.

## 3. Facing a 3-bet: 4-bet jam (50 bb deep)

At 50 bb a 4-bet *is* all-in. This table is the **solved jam-or-fold equilibrium** against each defender's 3-bet range from §2:

<!--T:holdem_4betjam-->
| Spot | 3-bettor's range | You 4-bet jam 50bb | They call the jam with |
|---|---|---|---|
| CO opens 2.5, BTN 3-bets to 7.5 | 6.2% | 5.6%: 66+, AQs+, AKo | QQ+, AKs, AKo |
| BTN opens 2.5, SB 3-bets to 10 | 14.5% | 9.8%: 44+, ATs+, KJs+, QJs, AJo+ | 77+, ATs+, KJs+, AJo+ |
| BTN opens 2.5, BB 3-bets to 11 | 8.7% | 5.4%: 99+, AJs+, AQo+ | 99+, AQs+, AKo |
| CO opens 2.5, BB 3-bets to 11 | 6.2% | 3.3%: JJ+, AQs+, AKo | JJ+, AKs, AKo |
| CO opens 2.5, SB 3-bets to 10 | 11.6% | 7.7%: 66+, AJs+, KJs+, QJs, AQo+ | 88+, AJs+, KQs, AQo+ |
| SB opens 3, BB 3-bets to 9 | 8.7% | 5.9%: TT+, AJs+, KJs+, QJs, AQo+ | 99+, AQs+, AKo |
<!--/T-->

* **In position vs a 3-bet**, also **flat-call** with hands just below the jam range that play well (TT-77, AQo/AJs, KQs, suited broadways, suited connectors when the 3-bet is small). The SPR is ≈2, so plan to get the money in on most flops where you hit.
* **Out of position vs a 3-bet**: mostly jam or fold.
* Against players who only 3-bet premiums (common in home games), fold everything except QQ+/AK.

## 4. Short stacks: heads-up push/fold Nash (exact)

When the effective stack is short (rebuys, or a blind-vs-blind battle with a short stack), use these. The table is the solved equilibrium for SB shoves / BB calls, no ante.

<!--T:holdem_pushfold-->
**SB shove** (heads-up or blind-vs-blind, no ante): shove if your effective stack in big blinds is at or below the number shown.

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|25+|25+|25+|25+|25+|25+|25+|25+|25+|25+|25+|25+|25+|
|**K**|25+|25+|25+|25+|25+|25+|25+|25+|25+|25+|25+|18|18|
|**Q**|25+|25+|25+|25+|25+|25+|25+|25+|25+|22|16|13|12|
|**J**|25+|25+|25+|25+|25+|25+|25+|25+|18|14|13|10|8|
|**T**|25+|25+|25+|25+|25+|25+|25+|25+|20|12|10|7|6|
|**9**|25+|22|20|25+|25+|25+|25+|25+|25+|14|5|4|3|
|**8**|25+|18|13|12|16|20|25+|25+|25+|18|7|2.5|2.5|
|**7**|25+|16|10|8|9|10|14|25+|25+|22|13|2.5|2|
|**6**|25+|14|9|6|5|4|7|11|25+|25+|16|2|2|
|**5**|25+|14|8|6|4|3|2.5|2.5|2|25+|22|2|2|
|**4**|25+|13|8|5|3|2.5|2|2|2|2|25+|2|1.5|
|**3**|25+|12|7|5|3|2.5|1.5|1.5|1.5|1.5|1.5|25+|1.5|
|**2**|25+|11|7|4|2.5|2|1.5|1.5|1.5|1.5|-|-|25+|

**BB call vs a SB shove**: call if the effective stack is at or below the number shown.

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|25+|25+|25+|25+|25+|25+|25+|25+|25+|25+|25+|22|22|
|**K**|25+|25+|25+|25+|25+|22|16|15|14|13|12|11|10|
|**Q**|25+|25+|25+|25+|22|16|12|10|9|8|8|7|7|
|**J**|25+|25+|18|25+|18|13|10|8|7|6|6|5|5|
|**T**|25+|22|15|12|25+|11|9|7|6|5|5|4|4|
|**9**|25+|16|11|9|8|25+|8|6|5|4|4|4|3|
|**8**|25+|14|9|7|6|6|25+|6|5|4|4|3|3|
|**7**|25+|12|8|6|5|5|4|25+|5|4|4|3|3|
|**6**|20|10|7|5|4|4|4|4|25+|4|4|3|3|
|**5**|20|10|6|5|3|3|3|3|3|25+|4|4|3|
|**4**|18|9|6|4|3|3|3|3|3|3|25+|3|3|
|**3**|16|8|5|4|3|3|2.5|2.5|2.5|3|3|22|3|
|**2**|16|8|5|4|3|3|2.5|2.5|2.5|2.5|2.5|2.5|15|

| Stack (BB) | SB shoves | BB calls |
|---|---|---|
| 1.5 | 98% | 100% |
| 2 | 89% | 100% |
| 2.5 | 82% | 100% |
| 3 | 77% | 92% |
| 4 | 74% | 73% |
| 5 | 71% | 62% |
| 6 | 69% | 54% |
| 7 | 67% | 48% |
| 8 | 63% | 45% |
| 9 | 60% | 41% |
| 10 | 58% | 37% |
| 11 | 55% | 35% |
| 12 | 54% | 33% |
| 13 | 51% | 31% |
| 14 | 48% | 30% |
| 15 | 45% | 29% |
| 16 | 45% | 27% |
| 18 | 42% | 24% |
| 20 | 40% | 22% |
| 22 | 38% | 20% |
| 25 | 36% | 17% |
<!--/T-->

## 5. Re-shoving (3-bet all-in) over an open with 10-25 bb

You're short (S bb), someone opens 2.5 bb, everyone else has folded to you. This is the solved jam-or-fold game against each opening range from §1. The opener's best-response calling range is shown too, so you know what to call with when someone jams on *you*.

<!--T:holdem_reshove-->
**vs UTG open (2.5x)** - jam range / opener's correct calling range

| Your stack | You jam | Opener calls |
|---|---|---|
| 10 BB | 6%: 88+, ATs+, AQo+ | 77+, ATs+, KJs+, QJs, JTs, AQo+ |
| 12 BB | 6%: 88+, AJs+, KJs+, AQo+ | 88+, AJs+, AQo+ |
| 15 BB | 7%: 66+, AQs+, KJs+, AQo+ | 99+, AQs+, AQo+ |
| 18 BB | 6%: 99+, AJs+, KJs+, AQo+ | 99+, AQs+, AKo |
| 20 BB | 6%: 99+, ATs+, KJs+, AQo+ | 99+, AQs+, AKo |
| 25 BB | 6%: 66+, AKs,AQs,AJs,A5s, KQs, AKo | JJ+, AKs, AKo |

**vs MP open (2.5x)** - jam range / opener's correct calling range

| Your stack | You jam | Opener calls |
|---|---|---|
| 10 BB | 10%: 66+, ATs+, KQs, ATo+, KQo | 55+, A9s+, K9s+, Q9s+, J9s+, T9s, 98s, ATo+, KQo |
| 12 BB | 10%: 55+, ATs+, KJs+, ATo+ | 55+, A9s+, KTs+, JTs, AJo+ |
| 15 BB | 10%: 66+, ATs+, KTs+, QTs+, AJo+ | 66+, ATs+, KJs+, AJo+ |
| 18 BB | 10%: 44+, ATs+, KTs+, QTs+, AJo+ | 77+, AJs+, KQs, AJo+ |
| 20 BB | 9%: 77+, ATs+, KTs+, QTs+, JTs, AJo+ | 77+, AJs+, KQs, AQo+ |
| 25 BB | 9%: 66+, ATs+, KTs+, QJs, JTs, AQo+ | 88+, AQs+, AQo+ |

**vs HJ open (2.5x)** - jam range / opener's correct calling range

| Your stack | You jam | Opener calls |
|---|---|---|
| 10 BB | 16%: 55+, A4s+, KTs+, QJs, A8o+, KJo+ | 33+, A2s+, K7s+, Q8s+, J8s+, T8s+, 97s+, 87s, 76s, 65s, A9o+, KTo+, QTo+, JTo |
| 12 BB | 16%: 33+, A3s+, KTs+, QJs, A8o+, KQo | 33+, A2s+, K9s+, Q9s+, J9s+, T8s+, 98s, 87s, A9o+, KJo+ |
| 15 BB | 16%: 33+, A3s+, KTs+, QJs, JTs, A9o+, KQo | 33+, AKs,AQs,AJs,ATs,A9s,A8s,A7s,A5s, KTs+, QJs, JTs, A9o+, KQo |
| 18 BB | 16%: 33+, A4s+, KTs+, QTs+, JTs, A9o+, KQo | 33+, A7s+, KJs+, QJs, ATo+ |
| 20 BB | 16%: 22+, A5s+, KTs+, QTs+, J9s+, T9s, ATo+, KQo | 44+, A8s+, KJs+, ATo+, KQo |
| 25 BB | 14%: 44+, A9s+, K9s+, QTs+, J9s+, T9s, ATo+, KQo | 66+, ATs+, KQs, AJo+ |

**vs CO open (2.5x)** - jam range / opener's correct calling range

| Your stack | You jam | Opener calls |
|---|---|---|
| 10 BB | 16%: 44+, A4s+, KTs+, QJs, A8o+, KJo+ | 22+, A2s+, K6s+, Q8s+, J8s+, T8s+, 97s+, 86s+, 75s+, 65s, 54s, AKo,AQo,AJo,ATo,A9o,A8o,A5o, KTo+, QTo+, JTo |
| 12 BB | 18%: 33+, A2s+, KTs+, QJs, A7o+, KJo+ | 22+, A2s+, K9s+, Q9s+, J9s+, T8s+, 98s, 87s, AKo,AQo,AJo,ATo,A9o,A8o,A5o, KJo+, QJo |
| 15 BB | 18%: 22+, A2s+, KTs+, QTs+, JTs, A8o+, KQo | 22+, A4s+, KTs+, QTs+, JTs, A8o+, KQo |
| 18 BB | 17%: 22+, A3s+, KTs+, QTs+, JTs, T9s, A9o+, KQo | 33+, AKs,AQs,AJs,ATs,A9s,A8s,A7s,A5s, KTs+, QJs, A9o+, KQo |
| 20 BB | 17%: 22+, A3s+, K9s+, QTs+, JTs, T9s, A9o+, KQo | 33+, A7s+, KJs+, QJs, A9o+, KQo |
| 25 BB | 16%: 22+, A5s+, K9s+, Q9s+, J9s+, T9s, 98s, ATo+, KQo | 44+, A9s+, KJs+, ATo+ |

**vs BTN open (2.5x)** - jam range / opener's correct calling range

| Your stack | You jam | Opener calls |
|---|---|---|
| 10 BB | 28%: 33+, A2s+, K8s+, Q9s+, JTs, A2o+, K9o+, QTo+ | 22+, A2s+, K2s+, Q5s+, J7s+, T7s+, 96s+, 85s+, 75s+, 64s+, 53s+, 43s, A2o+, K8o+, Q9o+, J9o+, T8o+, 98o |
| 12 BB | 27%: 22+, A2s+, K7s+, QTs+, JTs, A2o+, KTo+, QJo | 22+, A2s+, K4s+, Q8s+, J7s+, T7s+, 96s+, 86s+, 75s+, 65s, 54s, A2o+, K9o+, QTo+, JTo, T9o |
| 15 BB | 27%: 22+, A2s+, K9s+, Q9s+, J9s+, T9s, A2o+, KTo+, QJo | 22+, A2s+, K8s+, Q9s+, J9s+, T9s, 98s, A2o+, KTo+, QJo |
| 18 BB | 28%: 22+, A2s+, K9s+, Q9s+, J9s+, T9s, 98s, 87s, A2o+, KTo+, QJo | 22+, A2s+, K9s+, QTs+, JTs, A4o+, KTo+ |
| 20 BB | 27%: 22+, A2s+, K9s+, Q9s+, J9s+, T8s+, 98s, 87s, A3o+, KTo+, QJo | 22+, A2s+, KTs+, QTs+, JTs, A5o+, KJo+ |
| 25 BB | 26%: 22+, A2s+, K9s+, Q9s+, J9s+, T8s+, 98s, 87s, A4o+, KJo+, QJo, JTo | 22+, A4s+, KTs+, QTs+, A7o+, KJo+ |
<!--/T-->

---

## 6. Post-flop: c-betting by texture (simulated range vs range)

The table compares **the preflop raiser's (PFR) opening range** with **the caller's calling range** from §2 over 3 million random flops. Columns:
* **Equity**: PFR's raw all-in equity on that texture.
* **Nut%**: the share of the range holding two pair or better.
* **TP+%**: top pair or better.
* **Air%**: no pair and no draw.

<!--T:holdem_texture-->
Preflop raiser (PFR) vs caller, single-raised pot. Equity = PFR's all-in equity on that flop; Nut% = share of the range holding two pair or better on the flop; TP+% = top pair or better; Air% = no pair and no draw. Freq = how often this texture comes up.


### BTN open vs BB call

| Texture | Freq | PFR equity | PFR nut% | BB nut% | PFR TP+% | BB TP+% | PFR air% | BB air% |
|---|---|---|---|---|---|---|---|---|
| **All flops** | 100% | **54%** | 5% | 5% | 22% | 17% | 43% | 46% |
| A-high paired | 2% | **56%** | 14% | 11% | 27% | 21% | 48% | 58% |
| A-high unpaired | 18% | **56%** | 7% | 5% | 31% | 22% | 30% | 38% |
| Q-high paired | 2% | **55%** | 8% | 8% | 17% | 14% | 59% | 65% |
| K-high paired | 2% | **55%** | 10% | 9% | 19% | 16% | 57% | 63% |
| J/T-high paired | 4% | **55%** | 8% | 8% | 19% | 15% | 60% | 64% |
| K-high unpaired | 16% | **54%** | 5% | 4% | 21% | 17% | 38% | 43% |
| Q-high unpaired | 13% | **54%** | 4% | 4% | 19% | 14% | 40% | 45% |
| 9-high or lower paired | 7% | **54%** | 6% | 7% | 18% | 13% | 68% | 69% |
| J/T-high unpaired | 19% | **54%** | 4% | 3% | 20% | 16% | 42% | 43% |
| 9-high or lower unpaired | 17% | **53%** | 4% | 4% | 21% | 15% | 46% | 44% |
| rainbow | 40% | **55%** | 5% | 5% | 21% | 16% | 47% | 52% |
| two-tone | 55% | **54%** | 5% | 4% | 22% | 17% | 41% | 44% |
| monotone | 5% | **54%** | 10% | 11% | 28% | 24% | 25% | 29% |
| unpaired, dry | 64% | **54%** | 4% | 4% | 22% | 17% | 41% | 46% |
| unpaired, connected | 15% | **54%** | 7% | 6% | 24% | 18% | 34% | 32% |
| unpaired, very connected | 4% | **53%** | 9% | 8% | 25% | 20% | 26% | 24% |
| high (A/K/Q), dry, rainbow | 15% | **55%** | 4% | 3% | 23% | 17% | 41% | 49% |
| high (A/K/Q), connected, rainbow | 2% | **56%** | 10% | 6% | 28% | 20% | 28% | 32% |
| high (A/K/Q), very connected, rainbow | 0% | **55%** | 11% | 8% | 30% | 22% | 20% | 26% |
| high (A/K/Q), dry, two-tone | 23% | **55%** | 4% | 3% | 23% | 17% | 37% | 42% |
| high (A/K/Q), connected, two-tone | 3% | **55%** | 10% | 6% | 29% | 20% | 25% | 28% |
| high (A/K/Q), very connected, two-tone | 1% | **55%** | 12% | 8% | 30% | 22% | 17% | 22% |
| high (A/K/Q), dry, monotone | 3% | **54%** | 10% | 11% | 28% | 25% | 25% | 31% |
| high (A/K/Q), connected, monotone | 0% | **54%** | 15% | 14% | 34% | 28% | 17% | 21% |
| high (A/K/Q), very connected, monotone | 0% | **54%** | 17% | 16% | 33% | 30% | 13% | 18% |
| middle/low (J and below), dry, rainbow | 9% | **54%** | 2% | 3% | 19% | 15% | 52% | 53% |
| middle/low (J and below), connected, rainbow | 4% | **53%** | 5% | 4% | 21% | 16% | 41% | 37% |
| middle/low (J and below), very connected, rainbow | 1% | **52%** | 8% | 7% | 22% | 18% | 32% | 26% |
| middle/low (J and below), dry, two-tone | 14% | **54%** | 2% | 3% | 19% | 15% | 47% | 48% |
| middle/low (J and below), connected, two-tone | 5% | **53%** | 5% | 5% | 21% | 16% | 38% | 33% |
| middle/low (J and below), very connected, two-tone | 1% | **52%** | 8% | 7% | 22% | 18% | 29% | 25% |
| middle/low (J and below), dry, monotone | 2% | **53%** | 9% | 10% | 26% | 22% | 31% | 32% |
| middle/low (J and below), connected, monotone | 1% | **53%** | 11% | 12% | 27% | 23% | 24% | 21% |
| middle/low (J and below), very connected, monotone | 0% | **52%** | 13% | 14% | 28% | 25% | 19% | 16% |

### CO open vs BTN call

| Texture | Freq | PFR equity | PFR nut% | BTN nut% | PFR TP+% | BTN TP+% | PFR air% | BTN air% |
|---|---|---|---|---|---|---|---|---|
| **All flops** | 100% | **49%** | 6% | 6% | 24% | 23% | 39% | 39% |
| 9-high or lower unpaired | 18% | **51%** | 5% | 5% | 22% | 16% | 49% | 59% |
| 9-high or lower paired | 7% | **50%** | 5% | 4% | 19% | 13% | 65% | 71% |
| J/T-high unpaired | 19% | **50%** | 5% | 4% | 25% | 22% | 37% | 37% |
| J/T-high paired | 4% | **49%** | 8% | 9% | 22% | 18% | 52% | 50% |
| Q-high paired | 2% | **49%** | 9% | 9% | 20% | 18% | 50% | 46% |
| Q-high unpaired | 13% | **49%** | 5% | 4% | 23% | 22% | 35% | 32% |
| K-high unpaired | 16% | **48%** | 6% | 6% | 23% | 24% | 33% | 30% |
| A-high unpaired | 17% | **48%** | 8% | 8% | 33% | 36% | 23% | 19% |
| A-high paired | 2% | **48%** | 14% | 15% | 28% | 31% | 38% | 32% |
| K-high paired | 2% | **47%** | 10% | 10% | 20% | 20% | 49% | 43% |
| rainbow | 40% | **49%** | 6% | 6% | 24% | 22% | 43% | 43% |
| two-tone | 55% | **49%** | 6% | 6% | 24% | 23% | 37% | 37% |
| monotone | 5% | **49%** | 12% | 11% | 31% | 29% | 24% | 24% |
| unpaired, dry | 64% | **49%** | 5% | 5% | 25% | 24% | 37% | 37% |
| unpaired, connected | 15% | **50%** | 8% | 8% | 26% | 23% | 33% | 35% |
| unpaired, very connected | 4% | **50%** | 10% | 9% | 29% | 24% | 26% | 26% |
| high (A/K/Q), dry, rainbow | 15% | **48%** | 5% | 5% | 25% | 26% | 34% | 31% |
| high (A/K/Q), connected, rainbow | 2% | **47%** | 11% | 12% | 31% | 33% | 23% | 15% |
| high (A/K/Q), very connected, rainbow | 0% | **48%** | 14% | 11% | 33% | 32% | 19% | 13% |
| high (A/K/Q), dry, two-tone | 22% | **48%** | 5% | 5% | 25% | 26% | 30% | 27% |
| high (A/K/Q), connected, two-tone | 3% | **48%** | 11% | 12% | 31% | 33% | 20% | 12% |
| high (A/K/Q), very connected, two-tone | 1% | **48%** | 14% | 11% | 33% | 32% | 16% | 11% |
| high (A/K/Q), dry, monotone | 2% | **49%** | 11% | 10% | 31% | 32% | 22% | 19% |
| high (A/K/Q), connected, monotone | 0% | **49%** | 17% | 16% | 36% | 36% | 16% | 10% |
| high (A/K/Q), very connected, monotone | 0% | **47%** | 18% | 16% | 37% | 36% | 13% | 9% |
| middle/low (J and below), dry, rainbow | 9% | **50%** | 3% | 4% | 23% | 19% | 50% | 54% |
| middle/low (J and below), connected, rainbow | 4% | **51%** | 5% | 5% | 23% | 18% | 43% | 50% |
| middle/low (J and below), very connected, rainbow | 1% | **51%** | 8% | 7% | 26% | 20% | 32% | 35% |
| middle/low (J and below), dry, two-tone | 14% | **50%** | 3% | 4% | 23% | 19% | 44% | 49% |
| middle/low (J and below), connected, two-tone | 6% | **51%** | 5% | 5% | 23% | 18% | 39% | 45% |
| middle/low (J and below), very connected, two-tone | 1% | **51%** | 9% | 8% | 27% | 20% | 29% | 32% |
| middle/low (J and below), dry, monotone | 2% | **50%** | 10% | 10% | 29% | 25% | 31% | 32% |
| middle/low (J and below), connected, monotone | 1% | **50%** | 11% | 12% | 29% | 25% | 25% | 29% |
| middle/low (J and below), very connected, monotone | 0% | **50%** | 14% | 14% | 32% | 27% | 20% | 22% |

### UTG open vs BB call

| Texture | Freq | PFR equity | PFR nut% | BB nut% | PFR TP+% | BB TP+% | PFR air% | BB air% |
|---|---|---|---|---|---|---|---|---|
| **All flops** | 100% | **60%** | 7% | 6% | 35% | 21% | 33% | 39% |
| Q-high paired | 2% | **66%** | 12% | 8% | 34% | 15% | 32% | 52% |
| A-high paired | 2% | **65%** | 17% | 11% | 35% | 21% | 20% | 44% |
| Q-high unpaired | 13% | **64%** | 7% | 5% | 40% | 18% | 22% | 35% |
| A-high unpaired | 17% | **64%** | 11% | 6% | 41% | 24% | 12% | 28% |
| J/T-high paired | 4% | **62%** | 7% | 8% | 30% | 16% | 47% | 55% |
| K-high paired | 2% | **62%** | 13% | 11% | 29% | 22% | 30% | 45% |
| K-high unpaired | 15% | **61%** | 8% | 6% | 35% | 25% | 19% | 30% |
| J/T-high unpaired | 19% | **59%** | 5% | 5% | 34% | 18% | 38% | 38% |
| 9-high or lower paired | 7% | **58%** | 2% | 6% | 31% | 19% | 62% | 61% |
| 9-high or lower unpaired | 18% | **55%** | 3% | 6% | 31% | 22% | 54% | 44% |
| rainbow | 40% | **61%** | 7% | 6% | 35% | 20% | 37% | 45% |
| two-tone | 55% | **60%** | 7% | 5% | 35% | 21% | 31% | 36% |
| monotone | 5% | **58%** | 12% | 14% | 41% | 30% | 20% | 27% |
| unpaired, dry | 64% | **61%** | 6% | 5% | 35% | 21% | 30% | 37% |
| unpaired, connected | 15% | **58%** | 8% | 8% | 37% | 23% | 34% | 31% |
| unpaired, very connected | 4% | **57%** | 11% | 9% | 41% | 25% | 26% | 24% |
| high (A/K/Q), dry, rainbow | 15% | **63%** | 7% | 5% | 37% | 22% | 21% | 37% |
| high (A/K/Q), connected, rainbow | 2% | **65%** | 16% | 8% | 44% | 25% | 10% | 25% |
| high (A/K/Q), very connected, rainbow | 0% | **66%** | 22% | 10% | 48% | 26% | 8% | 23% |
| high (A/K/Q), dry, two-tone | 22% | **62%** | 7% | 5% | 37% | 22% | 18% | 30% |
| high (A/K/Q), connected, two-tone | 3% | **63%** | 16% | 8% | 44% | 25% | 9% | 20% |
| high (A/K/Q), very connected, two-tone | 1% | **65%** | 23% | 10% | 49% | 26% | 7% | 19% |
| high (A/K/Q), dry, monotone | 2% | **60%** | 12% | 13% | 42% | 30% | 13% | 25% |
| high (A/K/Q), connected, monotone | 0% | **61%** | 19% | 17% | 47% | 33% | 7% | 19% |
| high (A/K/Q), very connected, monotone | 0% | **61%** | 25% | 19% | 51% | 35% | 6% | 17% |
| middle/low (J and below), dry, rainbow | 9% | **59%** | 4% | 4% | 31% | 18% | 51% | 50% |
| middle/low (J and below), connected, rainbow | 4% | **55%** | 4% | 6% | 33% | 22% | 51% | 40% |
| middle/low (J and below), very connected, rainbow | 1% | **55%** | 6% | 8% | 37% | 24% | 36% | 29% |
| middle/low (J and below), dry, two-tone | 14% | **58%** | 4% | 4% | 31% | 18% | 46% | 43% |
| middle/low (J and below), connected, two-tone | 6% | **55%** | 4% | 6% | 33% | 22% | 45% | 35% |
| middle/low (J and below), very connected, two-tone | 1% | **54%** | 6% | 8% | 37% | 24% | 32% | 25% |
| middle/low (J and below), dry, monotone | 2% | **57%** | 10% | 13% | 37% | 27% | 31% | 32% |
| middle/low (J and below), connected, monotone | 1% | **55%** | 11% | 15% | 40% | 31% | 31% | 26% |
| middle/low (J and below), very connected, monotone | 0% | **53%** | 12% | 19% | 43% | 34% | 24% | 18% |

### SB open vs BB call

| Texture | Freq | PFR equity | PFR nut% | BB nut% | PFR TP+% | BB TP+% | PFR air% | BB air% |
|---|---|---|---|---|---|---|---|---|
| **All flops** | 100% | **55%** | 5% | 5% | 23% | 17% | 43% | 46% |
| A-high paired | 2% | **57%** | 15% | 11% | 30% | 22% | 44% | 55% |
| K-high paired | 2% | **57%** | 10% | 8% | 19% | 14% | 56% | 64% |
| Q-high paired | 2% | **57%** | 9% | 8% | 18% | 13% | 57% | 65% |
| A-high unpaired | 18% | **57%** | 7% | 5% | 33% | 24% | 28% | 35% |
| K-high unpaired | 16% | **56%** | 5% | 4% | 21% | 15% | 38% | 44% |
| Q-high unpaired | 13% | **55%** | 5% | 4% | 20% | 14% | 40% | 45% |
| J/T-high paired | 4% | **55%** | 8% | 9% | 19% | 16% | 60% | 63% |
| 9-high or lower paired | 7% | **54%** | 5% | 7% | 17% | 13% | 68% | 68% |
| J/T-high unpaired | 19% | **54%** | 4% | 4% | 21% | 18% | 42% | 42% |
| 9-high or lower unpaired | 17% | **53%** | 4% | 5% | 20% | 14% | 48% | 44% |
| rainbow | 40% | **55%** | 5% | 5% | 22% | 16% | 47% | 51% |
| two-tone | 55% | **55%** | 5% | 5% | 22% | 16% | 41% | 43% |
| monotone | 5% | **54%** | 10% | 12% | 29% | 25% | 25% | 29% |
| unpaired, dry | 64% | **55%** | 4% | 4% | 23% | 17% | 41% | 45% |
| unpaired, connected | 15% | **54%** | 7% | 6% | 24% | 18% | 34% | 32% |
| unpaired, very connected | 4% | **53%** | 9% | 8% | 26% | 20% | 25% | 24% |
| high (A/K/Q), dry, rainbow | 15% | **57%** | 5% | 3% | 24% | 17% | 40% | 49% |
| high (A/K/Q), connected, rainbow | 2% | **57%** | 10% | 7% | 30% | 21% | 27% | 32% |
| high (A/K/Q), very connected, rainbow | 0% | **57%** | 12% | 8% | 32% | 22% | 18% | 25% |
| high (A/K/Q), dry, two-tone | 23% | **56%** | 5% | 3% | 24% | 17% | 35% | 41% |
| high (A/K/Q), connected, two-tone | 3% | **56%** | 10% | 6% | 30% | 21% | 23% | 27% |
| high (A/K/Q), very connected, two-tone | 1% | **56%** | 12% | 8% | 32% | 22% | 15% | 20% |
| high (A/K/Q), dry, monotone | 3% | **55%** | 10% | 12% | 30% | 26% | 24% | 31% |
| high (A/K/Q), connected, monotone | 0% | **55%** | 15% | 15% | 35% | 29% | 17% | 21% |
| high (A/K/Q), very connected, monotone | 0% | **55%** | 18% | 16% | 36% | 31% | 11% | 18% |
| middle/low (J and below), dry, rainbow | 9% | **54%** | 2% | 3% | 20% | 15% | 53% | 52% |
| middle/low (J and below), connected, rainbow | 4% | **53%** | 4% | 4% | 21% | 15% | 42% | 38% |
| middle/low (J and below), very connected, rainbow | 1% | **52%** | 7% | 7% | 23% | 18% | 32% | 27% |
| middle/low (J and below), dry, two-tone | 14% | **54%** | 3% | 3% | 20% | 15% | 48% | 46% |
| middle/low (J and below), connected, two-tone | 5% | **53%** | 4% | 5% | 21% | 16% | 39% | 34% |
| middle/low (J and below), very connected, two-tone | 1% | **52%** | 7% | 8% | 23% | 19% | 29% | 25% |
| middle/low (J and below), dry, monotone | 2% | **53%** | 9% | 11% | 26% | 23% | 31% | 32% |
| middle/low (J and below), connected, monotone | 1% | **53%** | 10% | 12% | 26% | 23% | 25% | 22% |
| middle/low (J and below), very connected, monotone | 0% | **52%** | 14% | 15% | 29% | 26% | 19% | 16% |
<!--/T-->

### What this tells you

**In position as the raiser (BTN vs BB, CO vs BB, HJ vs BB):**
* The raiser has a **small equity edge on every texture**: 52-56% as BTN vs BB, highest on A-high boards. Neither side has much of a nut edge (both ranges hold two pair+ about 5% of the time).
* That's the textbook case for a **small, frequent c-bet: 25-33% of the pot with most of your range.** It works best on A-high, K-high and paired boards, where the caller has the most air (38-69%).
* On **low, connected boards** (9-high-or-lower connected, e.g. 7♠6♠5♦), the caller's air shrinks and their nut% catches up. Check more, about half your range. Bet sets, two pair, overpairs and strong draws. When you bet, use bigger sizes (60-75%).
* On **monotone boards** both ranges are evenly matched and polarised. Bet small and seldom. Check most one-pair hands.

**From early position (UTG vs BB):**
* The raiser has **≈60% equity and a clear nut edge** (top pair+ 35% vs 21%). Most visible on A/K/Q-high boards: 61-64% equity, with the BB holding 28-35% air.
* **C-bet very often and small** on high boards. On low boards (9-high or lower: 55%) the BB has more two pairs and straights, so check more there.

**Out of position as the raiser (CO opens, BTN calls):**
* The raiser is **slightly behind** (49%) and acts first. **Check most of your range.** Bet small only on low, dry boards, where the button's range misses: 51% equity and the button holds 59% air.
* On A-high boards the button's flatting range has more top pairs than you do (36% vs 33%), because it is built from the strong Ax hands that flat. Check a lot there.

### Sizing summary (single-raised pot, SPR ≈ 8)

| Situation | Flop | Turn | River |
|---|---|---|---|
| Range-advantage board, IP | 25-33%, high frequency | 50-75% with value + good draws, check back weak showdown | 75%-pot or jam with value. Bluff with the best blockers to their calls |
| Dynamic / low connected board | Check more. Bet 60-75% with strong hands + draws | Barrel when the turn helps your range (overcards) | Polarised: big or check |
| Out of position as raiser | Check most. Small bets on low dry boards | | |
| 3-bet pot (SPR ≈ 2) | 25-33% with any reasonable part of your range. You're committed with top pair+ | Jam | |

### Turn and river (GTO principles)

* **Geometric sizing.** With SPR ≈ 8, betting about 75% on each of three streets gets the stacks in. With SPR ≈ 3 after a flop bet, one more bet of 2/3 to pot does it.
* **Choose bluffs by blockers.** Pick hands that block the caller's strongest calls (holding the A♠ on a three-spade board, for example) and that don't block their folds.
* **River bluff ratios** heads-up: about 2 value : 1 bluff for a pot-sized bet, 3:1 for a half-pot bet (see [Fundamentals §2](00_fundamentals.md)).
* **Facing a river bet:** defend about MDF (e.g. 50% against pot) with the hands that beat bluffs. Against typical home-game players, who under-bluff rivers, **fold more than MDF**, especially to big bets.

---

## 7. Multiway and limped pots (very common at home games)

When 3+ players see the flop with wide ranges (limped pots), the random-hand tables from the variant sims apply. This is the Hold'em version, with every player holding a random hand:

**What wins at showdown when everyone goes to the river:**

<!--T:holdem_winners-->
| Players | High card | Pair | Two pair | Trips | Straight | Flush | Full house | Quads | Str. flush | Straight+ | Median winner |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 5.9% | 37.1% | 31.5% | 7.2% | 8.0% | 5.2% | 4.7% | 0.3% | 0.1% | 18.3% | Two pair |
| 3 | 1.9% | 30.0% | 33.9% | 9.3% | 10.7% | 7.1% | 6.6% | 0.4% | 0.1% | 24.9% | Two pair |
| 4 | 0.6% | 24.1% | 33.7% | 11.0% | 13.1% | 8.6% | 8.1% | 0.6% | 0.1% | 30.5% | Two pair |
| 5 | 0.2% | 19.7% | 32.3% | 12.5% | 15.0% | 9.8% | 9.6% | 0.7% | 0.2% | 35.3% | Two pair |
| 6 | 0.1% | 16.1% | 30.5% | 13.9% | 16.7% | 10.8% | 10.9% | 0.9% | 0.2% | 39.5% | Trips |
| 7 | 0.0% | 13.4% | 28.5% | 15.0% | 17.9% | 11.8% | 12.2% | 1.0% | 0.2% | 43.1% | Trips |
| 8 | 0.0% | 11.2% | 26.4% | 16.0% | 19.1% | 12.6% | 13.2% | 1.2% | 0.2% | 46.3% | Trips |
| 9 | 0.0% | 9.4% | 24.6% | 16.7% | 20.1% | 13.4% | 14.2% | 1.3% | 0.3% | 49.2% | Trips |
<!--/T-->

**Flop equity by hand vs random hands:**

<!--T:holdem_flop_made-->
| Hand | How often (6p) | 3 players | 4 players | 5 players | 6 players | 7 players | 8 players | 9 players |
|---|---|---|---|---|---|---|---|---|
| nothing | 63.01% | 21.7% | 15.1% | 11.7% | 9.6% | 8.1% | 7.1% | 6.3% |
| weak pair (bottom pair / small pocket pair) | 10.90% | 36.0% | 24.7% | 18.3% | 14.6% | 12.2% | 10.5% | 9.4% |
| middle pair (or pocket pair between top & 2nd card) | 10.76% | 48.8% | 36.0% | 27.6% | 21.8% | 17.7% | 14.6% | 12.5% |
| top pair, kicker below J | 6.53% | 61.3% | 49.1% | 40.1% | 32.9% | 27.6% | 23.2% | 19.6% |
| top pair, J+ kicker | 2.88% | 64.9% | 53.8% | 44.8% | 37.8% | 32.6% | 28.2% | 24.4% |
| overpair | 1.37% | 64.4% | 52.3% | 43.6% | 36.3% | 30.8% | 26.2% | 22.5% |
| two pair (both cards) | 1.90% | 74.9% | 66.6% | 59.5% | 54.0% | 49.0% | 45.0% | 41.8% |
| trips (board pair + 1 card) | 1.26% | 87.4% | 81.3% | 76.9% | 72.3% | 68.6% | 64.3% | 60.8% |
| set | 0.64% | 85.4% | 80.7% | 76.2% | 72.6% | 69.1% | 66.4% | 64.1% |
| straight (non-nut) | 0.14% | 79.4% | 72.1% | 64.0% | 60.4% | 54.4% | 51.3% | 47.1% |
| nut straight | 0.25% | 86.8% | 81.7% | 78.0% | 73.1% | 69.0% | 66.1% | 63.1% |
| flush (non-nut) | 0.16% | 86.7% | 81.3% | 77.1% | 74.7% | 70.0% | 66.9% | 62.6% |
| nut flush | 0.04% | 97.0% | 95.1% | 94.3% | 92.7% | 90.9% | 89.9% | 88.3% |
| full house or better | 0.17% | 93.9% | 92.4% | 90.2% | 89.2% | 88.6% | 86.5% | 86.0% |
<!--/T-->

Rules of thumb for multiway Hold'em pots:
* **Top pair is only about 2× fair share at 6-handed.** Bet it for value and protection, but don't stack off against a lot of action.
* **Sets and two pair** are the hands to build pots with.
* **Draws gain value as more opponents join**, because the pot odds improve. Nut flush draws are the best of them.

---

## 8. Home-game adjustments (exploitative, on top of GTO)

GTO is the baseline. Home 5/10 games usually have these leaks:

| Their leak | Your adjustment |
|---|---|
| Too many limps / loose calls preflop | Isolate wider and bigger (5-6 bb + 1 per limper) with the top ~20% of hands. Value-bet thinner post-flop |
| Rarely 3-bet light | Fold more to 3-bets (QQ+/AK only to jam). Flat-call opens in position more with suited hands |
| Calling stations | Bluff less, value-bet bigger and thinner (2nd pair for value) |
| Over-folding to c-bets | C-bet more often, even on bad textures |
| Few river bluffs | Fold medium hands to big river bets |
| Tilters after big losses | Widen value ranges against them |

Appendix: the full table of equity vs 1-8 random hands for all 169 hands is in [`results/tables/holdem_equity_all.md`](results/tables/holdem_equity_all.md).
