# Simulation code and methods

Everything in the guides is reproducible with `./run_all.sh` (≈10-15 min on 4 cores; needs `gcc` with OpenMP, Python 3 and numpy).

## Hand evaluator (`common.h`)
* Bitmask evaluator: per-suit 13-bit rank masks. It handles 4-9 cards and returns a value where bigger is better.
* **Verified exactly** by `test_eval`: all 2,598,960 five-card hands and all 133,784,560 seven-card hands give the textbook category counts, and there are exactly 7,462 distinct five-card hand values.
* Variant evaluators: Hold'em/Pineapple (best 5 of 7), Omaha (exactly 2 of 4 hole + exactly 3 of the board), Tic-tac-toe (both hole cards + the 3 cards of any of the 8 lines).

## Programs

| Program | What it computes | Output |
|---|---|---|
| `preflop holdem/ttt N T` | Equity of all 169 two-card classes vs N−1 random hands, for N = 2..9 (T deals each) | `results/*_preflop_equity.csv` |
| `preflop matrix T` | 169×169 heads-up Hold'em equity matrix, sampling random concrete combos per class | `results/holdem_hu_matrix.csv` |
| `pineapple discard N T [strategy]` | For each of the 1,755 three-card classes, the equity of each of the 3 discards. All three use the **same** deals (common random numbers), against opponents who also discard | `results/pineapple_discard_N*.csv` |
| `run_pineapple.py` | Iterates the above: opponents discard randomly, then best-respond to the previous strategy (3 rounds) | strategy + final CSVs |
| `cats VARIANT N T` | Full deals; every seat classified on flop and turn (made hand + draw, outs counted by enumerating every unseen card) and on the river; showdown shares; heads-up shares for every pair of seats | `results/cats/*.csv` |
| `omaha_pre features/named` | Omaha starting-hand equity by feature and for named hands | `results/omaha_*.csv` |
| `holdem_preflop.py` | Card-removal combo weights; push/fold, re-shove and 4-bet-jam equilibria by fictitious play; opening and defence charts | `results/tables/holdem_*.md`, `results/holdem_ranges.json` |
| `texture RANGE_A RANGE_B T` + `run_texture.py` | Range vs range on 3M random flops, grouped by texture (high card, paired, suits, connectedness) | `results/tables/holdem_texture.md` |
| `analyze_cats.py`, `analyze_preflop.py` | CSV → markdown tables (also fits and tests the Pineapple point system) | `results/tables/*.md` |
| `build_guides.py` | Puts the tables into the guides between `<!--T:name-->` markers | `../*.md` |

## Method notes and honest limitations
* **Solved equilibria** (fictitious play, then a pure best response to the converged average strategy): heads-up push/fold, re-shove vs an open, 4-bet jam vs a 3-bet. All of these are jam-or-fold subgames, and the equities include exact card-removal weights. Pairs are made monotone (if 66 jams, so do 77+) to remove Monte-Carlo noise at the margins.
* **Hold'em opening widths** follow the standard solver structure for 50 bb with no ante (set by hand). Hands are ordered by the simulated equity. The **defence charts** combine simulated equity vs range with an explicit equity-realisation model (written out in `holdem_preflop.py: realisation`).
* **Multiway post-flop** play has no unique equilibrium and can't be solved at this scale. The variant guides give exact equities against the actual starting distribution (random hands, because nobody folds preflop) and derive strategy from pot odds, MDF and polarisation.
* **Pineapple discard objective** = showdown equity vs the field. Post-flop playability isn't modelled beyond that. Equity is the standard proxy, and the decisions that matter differ by whole percentage points.
* **Monte-Carlo precision:** preflop cells ±0.1-0.2%, heads-up matrix ±0.3%, street tables ±0.1-0.5% (cells with fewer than 200-300 samples are blanked). Pineapple discards are compared on common random numbers, so the *differences* between discards are far more precise than the levels.
