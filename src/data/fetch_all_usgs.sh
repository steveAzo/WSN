#!/usr/bin/env bash
# Fetch calendar-year data for every candidate site (sequential to be polite to the USGS server).
YEAR=${1:-2023}
tail -n +2 data/raw/usgs/candidate_sites.csv | cut -d, -f1 | while read s; do
  [ -f "data/raw/usgs/${s}_${YEAR}-01-01_${YEAR}-12-31.csv" ] && continue
  python -u src/data/fetch_usgs.py "$s" "${YEAR}-01-01" "${YEAR}-12-31"
done
