# Öljymalli – Brent/WTI fair value, ennustekartio ja Hormuz-hasardi

Automaattisesti 2×/vrk päivittyvä öljyn hintaennuste. Sivu: GitHub Pages (`docs/index.html`).

## Mitä ajetaan (`pipeline/run_all.py`)
1. `pipeline/fetch_daily.py` – FRED, EIA (viikko/kk/päivä), STEO, CFTC, IMF PortWatch, GPR-päiväindeksi, OVX, Yahoo (futuurisopimukset, S&P, WTI-optioketju). Jokainen lähde on eristetty: haun epäonnistuessa edellinen tiedosto jää käyttöön ja tila kirjataan `data/status_fetch.json`.
2. `pipeline/refresh_daily_files.py` – futures_daily.csv, hormuz_daily.csv, cftc_wti_cot.csv.
3. `scripts/build_panel.py`, `long_panel.py`, `analyze.py`, `build_page.py`, `extra_series.py`, `curve_now.py`.
4. Mallit: `model.py` (fair value + kartio + yhdistelmä), `models17.py` (optiojakauma, skenaariopuu, regiimit, Kalman, kvantiilit, viikkonowcast, SVAR), `models8.py` (STEO, DM/CW-testit, pino, tiltti), `hazard.py` (päivittäinen Hormuz-hasardi), `daily_signals.py`, `weights.py`.
5. Sivu kootaan `page/template.html` + `data/page_data.json` → `docs/index.html`; ennusteet kirjataan `data/forecast_log.csv`.

Ajo paikallisesti: `OIL_ROOT=$(pwd) python pipeline/run_all.py --no-fetch` (skriptit käyttävät polkua `/home/claude/oil`; Actions linkittää työtilan siihen).

Lähteet, jotka estävät palvelinhaut: CME (käyrä/optiot, manuaalinen `data/raw4/`), investing.com (EIA-konsensus), stock-marketdata.com (BDI/konttirahti, staattinen).
