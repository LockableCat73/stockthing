#!/bin/bash
# Reproduce every result and rebuild the guides. Takes ~10-15 minutes on 4 cores.
set -e
cd "$(dirname "$0")"
make
./test_eval                                                     # evaluator self-check (exact counts)
mkdir -p ../results/tables
./preflop holdem 9 200000 > ../results/holdem_preflop_equity.csv
./preflop ttt 9 100000    > ../results/ttt_preflop_equity.csv
./preflop matrix 30000    > ../results/holdem_hu_matrix.csv
python3 run_pineapple.py 100000                                 # iterated discard strategy, 2-9 players
./run_cats.sh                                                   # street tables for all variants
HANDS=$(cat omaha_named_hands.txt)
for n in 2 4; do ./omaha_pre named $n 300000 $HANDS > ../results/omaha_named_N$n.csv; done
./omaha_pre named 6 400000 $HANDS > ../results/omaha_named_N6.csv
for n in 4 6 8; do ./omaha_pre features $n 3000000 > ../results/omaha_features_N$n.csv; done
python3 holdem_preflop.py
python3 run_texture.py
python3 analyze_cats.py
python3 analyze_preflop.py
python3 build_guides.py
