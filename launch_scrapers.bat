@echo off
cd /d "C:\Users\bahma\Downloads\base-juridique-app"

echo Arret des scrapers existants...
taskkill /F /FI "WINDOWTITLE eq scraper_*" >nul 2>&1

echo Lancement des scrapers...
start /B "scraper_cce" python -u scrapers\cce_scraper.py --max-docs 100000 >>"logs\cce.log" 2>&1
start /B "scraper_consconst" python -u scrapers\scrape_consconst_fast.py --start-year 1985 --end-year 2013 >>"logs\consconst_fast.log" 2>&1
start /B "scraper_moniteur" python -u scrapers\moniteur_scraper.py --max 100000 >>"logs\moniteur.log" 2>&1
start /B "scraper_gallilex" python -u scrapers\gallilex_scraper.py >>"logs\gallilex.log" 2>&1
start /B "scraper_wallex" python -u scrapers\wallex_scraper.py >>"logs\wallex.log" 2>&1
start /B "scraper_juportal" python -u scrapers\juportal_scraper.py --max-docs 100000 >>"logs\juportal.log" 2>&1
start /B "scraper_hudoc" python -u scrapers\hudoc_scraper.py --max 10000 >>"logs\hudoc.log" 2>&1

timeout /t 3 /nobreak >nul
tasklist /FI "IMAGENAME eq python.exe" | find /c "python"
echo scrapers actifs
