#!/bin/sh
# Downloads daily OHLCV CSVs from the eod2_data repo (the same source Quantis' Eod2Provider reads)
# for every symbol in data/fo_universe_sorted.txt into data/eod2/.
mkdir -p data/eod2
tr 'A-Z' 'a-z' < data/fo_universe_sorted.txt | while read s; do
  echo "$s"
done | xargs -P 12 -I{} sh -c 'code=$(curl -s -m 60 -o "data/eod2/{}.csv" -w "%{http_code}" "https://raw.githubusercontent.com/BennyThadikaran/eod2_data/main/daily/{}.csv"); [ "$code" = "200" ] || echo "FAILED $code {}"'
