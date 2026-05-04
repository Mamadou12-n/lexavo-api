#!/bin/bash
# Launch all scrapers from the correct directory
# Usage: bash launch_scrapers.sh

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR" || exit 1

echo "Working directory: $DIR"

# Kill existing scrapers
pkill -f "scrapers/.*_scraper\|scrape_consconst" 2>/dev/null
sleep 2

# Launch all active scrapers
python -u "$DIR/scrapers/cce_scraper.py" --max-docs 100000 >> "$DIR/logs/cce.log" 2>&1 &
python -u "$DIR/scrapers/scrape_consconst_fast.py" --start-year 1994 --end-year 2013 >> "$DIR/logs/consconst_fast.log" 2>&1 &
python -u "$DIR/scrapers/moniteur_scraper.py" --max 100000 >> "$DIR/logs/moniteur.log" 2>&1 &
python -u "$DIR/scrapers/gallilex_scraper.py" >> "$DIR/logs/gallilex.log" 2>&1 &
python -u "$DIR/scrapers/wallex_scraper.py" >> "$DIR/logs/wallex.log" 2>&1 &
python -u "$DIR/scrapers/juportal_scraper.py" --max-docs 100000 >> "$DIR/logs/juportal.log" 2>&1 &
python -u "$DIR/scrapers/hudoc_scraper.py" --max 10000 >> "$DIR/logs/hudoc.log" 2>&1 &

sleep 3
COUNT=$(ps aux | grep -c "[p]ython.*scraper")
echo "$COUNT scrapers lancés"
