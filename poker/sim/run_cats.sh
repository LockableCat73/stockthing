#!/bin/bash
# Run the street-category simulations for every variant and table size.
cd "$(dirname "$0")"
R=../results/cats; mkdir -p $R
for n in 2 3 4 5 6 7 8 9; do
  ./cats ttt $n 1000000 > $R/ttt_N$n.csv
  ./cats pineapple $n 1000000 ../results/pineapple_strategy_N$n.csv > $R/pineapple_N$n.csv
  ./cats holdem $n 500000 > $R/holdem_N$n.csv
  ./cats omaha $n 300000 > $R/omaha_N$n.csv
  echo "done N=$n $(date +%T)"
done
