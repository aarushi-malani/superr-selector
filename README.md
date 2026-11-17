# SupeRR Selector S2: Who delivers under pressure?

Pipeline (run from this folder, in order):

    pip install -r requirements.txt
    python src/01_load_and_clean.py     # 6 CSVs (data/raw) -> superr.duckdb; deliveries_clean, innings_summary
    python src/05_wp_model.py           # Elo, venue par, "resources", win-probability model (+ out-of-sample test)
    python src/06_leverage_wpa.py       # Leverage Index (pressure) + win-probability credit per ball
    python src/07_ratings.py            # component empirical-Bayes ratings, bootstrap, reliability, robustness
    python src/08_report_pack.py        # outputs/REPORT_DATA.md + all report figures

Outputs: `outputs/` (CSVs, REPORT_DATA.md, *_console.txt logs), `outputs/figures/`.

## Method in one paragraph
A win-probability model (gradient boosting, monotone constraints, trained 2022-24 and tested on 2025-26)
gives the batting side's chance of winning before every ball. The **Leverage Index** of a ball is the expected
absolute swing in win probability across its possible outcomes, relative to an average ball. A **pressure over**
for a player starts with LI >= 1.5 AND that player's side behind (win probability <= 50%); all its balls are
pressure balls (~10% of each role's balls). Judged at the start of the over, so a player cannot switch
pressure on or off by his own play inside it. On every ball, performance is measured against what an average player
produces in the identical situation (runs above expected, wickets above expected). Each player's pressure level =
usual situation-adjusted skill (shrunk to the league mean) + pressure-specific deviation (shrunk by its measured
reliability). The two components are combined at pressure-situation exchange rates (a wicket is worth about
5.5 runs on pressure balls). **Pressure Score = runs above an average player per 100 pressure balls.**

Key settings: `MODEL_TYPE` (05), `LI_THRESHOLD`, `MIN_PRESSURE_BALLS`, `MIN_PRESSURE_MATCHES`, `N_BOOT` (07).
