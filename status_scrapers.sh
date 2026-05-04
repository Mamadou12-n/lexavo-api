#!/bin/bash
# Check scraping status
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== PROCESSUS ==="
ps aux | grep "[p]ython.*scraper\|scrape_consconst" | wc -l
echo "processus actifs"

echo ""
echo "=== DOCUMENTS ==="
for d in "$DIR"/output/*/; do
  name=$(basename "$d")
  count=$(find "$d" -maxdepth 1 -name "*.json" 2>/dev/null | wc -l)
  [ "$count" -gt 0 ] && printf "%7d %s\n" "$count" "$name"
done | sort -rn

echo ""
echo "=== DERNIERS LOGS ==="
for log in cce consconst_fast moniteur gallilex wallex juportal hudoc; do
  printf "%-20s " "$log:"
  tail -1 "$DIR/logs/$log.log" 2>/dev/null | cut -c1-100
done
