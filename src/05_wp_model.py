"""
05_wp_model.py  -  Win-probability (WP) model
=====================================================================
WHAT: For every delivery, estimate P(batting team wins | match state).
WHY : Pressure (Leverage Index) and player credit (Win Probability Added)
      are both computed from this number in step 06.

Steps inside this script
  1. Flag broken matches (ball data clearly incomplete) -> excluded.
  2. Team Elo ratings (pre-match team strength) -> opponent adjustment.
  3. Venue par (typical 1st-innings score at the ground) -> pitch adjustment.
  4. Two gradient-boosted models (1st innings, 2nd innings) with
     MONOTONE constraints, e.g. "more wickets in hand can never lower WP".
  5. Honest test: train on 2022-2024 seasons, test on 2025-2026,
     report log-loss / Brier score and save a calibration plot.
  6. Refit on all seasons and store wp_before for every ball.

RUN : python src/05_wp_model.py
OUT : tables bad_matches, match_elo, venue_par, model_balls (in superr.duckdb)
      models/wp_models.pkl
      outputs/figures/wp_calibration.png
=====================================================================
"""
import os, pickle
import duckdb, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import log_loss, brier_score_loss
from sklearn.calibration import calibration_curve
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler
from sklearn.linear_model import LogisticRegression

# "gbm"    = gradient boosting with monotone constraints (default, most accurate)
# "spline" = logistic regression on smooth spline features (use this if the
#            top-LI moments in step 06 look spiky / implausible)
MODEL_TYPE = "gbm"

os.makedirs("models", exist_ok=True)
os.makedirs("outputs/figures", exist_ok=True)
con = duckdb.connect("superr.duckdb")

# ------------------------------------------------------------------
# 1. Broken matches: our reconstructed totals disagree with the official
#    result by > 15 runs -> deliveries are missing. Exclude everywhere.
# ------------------------------------------------------------------
con.execute(r"""
CREATE OR REPLACE TABLE bad_matches AS
WITH t AS (
  SELECT m.match_id, m.win_team_id, lower(m.result) AS res, TRY_CAST(m.revised_target AS INT) AS revised_target,
         i1.total AS t1, i2.total AS t2, i2.batting_team_id AS bat2
  FROM matches m
  JOIN innings_summary i1 ON i1.match_id = m.match_id AND i1.innings = 1
  JOIN innings_summary i2 ON i2.match_id = m.match_id AND i2.innings = 2)
SELECT match_id FROM t
WHERE (win_team_id = bat2 AND COALESCE(NULLIF(revised_target, 0), t1 + 1) - t2 > 15)
   OR (res LIKE '%run%' AND revised_target IS NULL AND
       abs((t1 - t2) - TRY_CAST(regexp_extract(res, 'by (\d+) run', 1) AS INT)) > 15)
""")
print("Broken matches excluded:", con.sql("SELECT COUNT(*) FROM bad_matches").fetchall()[0][0])

# ------------------------------------------------------------------
# 2. Elo: every team starts at 1500; after each match the winner takes
#    points from the loser, more if the win was unexpected (K = 20).
#    We store each team's rating BEFORE the match (no peeking ahead).
# ------------------------------------------------------------------
m = con.sql("""SELECT match_id, match_date, match_number, home_team_id, away_team_id, win_team_id
               FROM matches ORDER BY match_date, match_number, match_id""").df()
K, elo, rows = 20, {}, []
for r in m.itertuples():
    a, b = r.home_team_id, r.away_team_id
    ea, eb = elo.get(a, 1500.0), elo.get(b, 1500.0)
    rows.append((r.match_id, a, ea, b, eb))
    if pd.notna(r.win_team_id) and r.win_team_id in (a, b):
        exp_a = 1 / (1 + 10 ** ((eb - ea) / 400))
        s_a = 1.0 if r.win_team_id == a else 0.0
        elo[a] = ea + K * (s_a - exp_a)
        elo[b] = eb - K * (s_a - exp_a)
elo_df = pd.DataFrame(rows, columns=["match_id", "team_a", "elo_a", "team_b", "elo_b"])
con.register("elo_tmp", elo_df)
con.execute("CREATE OR REPLACE TABLE match_elo AS SELECT * FROM elo_tmp")

# ------------------------------------------------------------------
# 3. Venue par = average completed 1st-innings score at the ground,
#    EXCLUDING the current match (no leakage), shrunk toward the global
#    average with 5 'pseudo-matches' so rarely used grounds stay sensible.
# ------------------------------------------------------------------
con.execute("""
CREATE OR REPLACE TABLE venue_par AS
WITH f AS (
  SELECT i.match_id, m.venue_id, i.total
  FROM innings_summary i JOIN matches m USING (match_id)
  WHERE i.innings = 1 AND (i.legal_balls >= 120 OR i.wkts = 10)
    AND TRY_CAST(m.first_inn_revised_overs AS INT) IS NULL
    AND i.match_id NOT IN (SELECT match_id FROM bad_matches)),
g AS (SELECT AVG(total) AS mu FROM f),
v AS (SELECT venue_id, SUM(total) AS s, COUNT(*) AS n FROM f GROUP BY venue_id)
SELECT m.match_id,
       (COALESCE(v.s, 0) - COALESCE(f.total, 0) + 5 * g.mu) /
       (COALESCE(v.n, 0) - CASE WHEN f.total IS NULL THEN 0 ELSE 1 END + 5) AS venue_par
FROM matches m CROSS JOIN g
LEFT JOIN v ON v.venue_id = m.venue_id
LEFT JOIN f ON f.match_id = m.match_id
""")

# ------------------------------------------------------------------
# 4. Modelling table: one row per ball of every DECIDED match.
# ------------------------------------------------------------------
con.execute("""
CREATE OR REPLACE TABLE model_balls AS
SELECT d.match_id, d.innings, d.innings_ball_num, d.overid, d.season, d.comp_name,
       d.batting_team_id, d.bowling_team_id,
       d.score_before, 10 - d.wkts_before AS wkts_left,
       GREATEST(d.balls_left, 1) AS balls_left, d.max_balls,
       d.runs_needed, d.target,
       CASE WHEN e.team_a = d.batting_team_id THEN e.elo_a - e.elo_b
            ELSE e.elo_b - e.elo_a END AS elo_diff,
       vp.venue_par,
       CAST(d.comp_name LIKE 'IPL%' AS INT) AS is_ipl,
       CAST(m.win_team_id = d.batting_team_id AS INT) AS bat_won
FROM deliveries_clean d
JOIN matches m   USING (match_id)
JOIN match_elo e USING (match_id)
JOIN venue_par vp USING (match_id)
WHERE m.win_team_id IN (m.home_team_id, m.away_team_id)
  AND d.match_id NOT IN (SELECT match_id FROM bad_matches)
""")
df = con.sql("SELECT * FROM model_balls").df()
df["rrr"] = 6 * df["runs_needed"] / df["balls_left"]
print(f"Model rows: {len(df):,} balls from {df.match_id.nunique()} decided matches")

# ------------------------------------------------------------------
# "Resources" feature (Duckworth-Lewis idea): how many MORE runs does an
# average side add from here, given balls left and wickets in hand?
# Learned from completed 1st innings (monotone: more balls / wickets -> more runs).
#   1st innings: proj_gap  = score + expected_more - venue_par
#   2nd innings: shortfall = runs_needed - expected_more
# These carry the score x balls x wickets interaction, so a smooth model works.
# ------------------------------------------------------------------
fin = con.sql("""SELECT match_id, total FROM innings_summary
                 WHERE innings = 1 AND (legal_balls >= 120 OR wkts = 10)""").df()
d1_all = df[df.innings == 1].merge(fin, on="match_id")
d1_all["more"] = d1_all.total - d1_all.score_before


def fit_resources(train):
    r = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, min_samples_leaf=100,
                                      monotonic_cst=[1, 1], random_state=42)
    return r.fit(train[["balls_left", "wkts_left"]], train["more"])


def add_features(frame, res_model):
    f = frame.copy()
    f["exp_more"] = res_model.predict(f[["balls_left", "wkts_left"]])
    f["proj_gap"] = f.score_before + f.exp_more - f.venue_par
    f["shortfall"] = f.runs_needed - f.exp_more
    return f


F1, M1 = ["proj_gap", "wkts_left", "balls_left", "elo_diff", "is_ipl"], [1, 1, 0, 1, 0]
F2, M2 = ["shortfall", "rrr", "wkts_left", "balls_left", "elo_diff", "is_ipl"], [-1, -1, 1, 1, 1, 0]


def new_model(mono):
    if MODEL_TYPE == "spline":
        return make_pipeline(StandardScaler(), SplineTransformer(n_knots=6, degree=3),
                             LogisticRegression(C=1.0, max_iter=2000))
    return HistGradientBoostingClassifier(max_iter=400, learning_rate=0.05, max_leaf_nodes=31,
                                          min_samples_leaf=200, l2_regularization=1.0,
                                          monotonic_cst=mono, random_state=42)


# ------------------------------------------------------------------
# 5. Out-of-sample test (train <= 2024, test >= 2025)
# ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6, 6))
metrics = []
for inn, F, M in [(1, F1, M1), (2, F2, M2)]:
    res_tr = fit_resources(d1_all[d1_all.season <= 2024])
    d = add_features(df[df.innings == inn], res_tr)
    tr, te = d[d.season <= 2024], d[d.season >= 2025]
    if len(te) == 0 or len(tr) == 0:
        print(f"Innings {inn}: not enough seasons for a time split, skipping test")
        continue
    mdl = new_model(M).fit(tr[F], tr.bat_won)
    p = mdl.predict_proba(te[F])[:, 1]
    base = np.full(len(te), tr.bat_won.mean())
    print(f"Innings {inn} TEST ({len(te):,} balls): log-loss {log_loss(te.bat_won, p):.3f} "
          f"(no-skill {log_loss(te.bat_won, base):.3f}) | Brier {brier_score_loss(te.bat_won, p):.3f} "
          f"(no-skill {brier_score_loss(te.bat_won, base):.3f})")
    metrics.append(dict(innings=inn, model=MODEL_TYPE, train_seasons="2022-2024", test_seasons="2025-2026",
                        test_balls=len(te), log_loss=round(log_loss(te.bat_won, p), 4),
                        log_loss_no_skill=round(log_loss(te.bat_won, base), 4),
                        brier=round(brier_score_loss(te.bat_won, p), 4),
                        brier_no_skill=round(brier_score_loss(te.bat_won, base), 4)))
    fy, fx = calibration_curve(te.bat_won, p, n_bins=10, strategy="quantile")
    ax.plot(fx, fy, "o-", label=f"Innings {inn}")
ax.plot([0, 1], [0, 1], "--", color="grey", label="Perfect calibration")
ax.set_xlabel("Predicted win probability (batting team)")
ax.set_ylabel("Observed win rate")
ax.set_title("WP model calibration on unseen seasons (2025-26)")
ax.legend()
fig.tight_layout()
fig.savefig("outputs/figures/wp_calibration.png", dpi=150)
pd.DataFrame(metrics).to_csv("outputs/wp_model_metrics.csv", index=False)

# ------------------------------------------------------------------
# 6. Final models on all data -> wp_before for every ball
# ------------------------------------------------------------------
res_model = fit_resources(d1_all)
df = add_features(df, res_model)
models = {}
df["wp_before"] = np.nan
for inn, F, M in [(1, F1, M1), (2, F2, M2)]:
    idx = df.innings == inn
    models[inn] = new_model(M).fit(df.loc[idx, F], df.loc[idx, "bat_won"])
    df.loc[idx, "wp_before"] = models[inn].predict_proba(df.loc[idx, F])[:, 1]
pickle.dump({"models": models, "F1": F1, "F2": F2, "resources": res_model},
            open("models/wp_models.pkl", "wb"))

con.register("wp_tmp", df[["match_id", "innings", "innings_ball_num", "wp_before"]])
con.execute("""CREATE OR REPLACE TABLE model_balls AS
               SELECT mb.*, w.wp_before FROM model_balls mb
               JOIN wp_tmp w USING (match_id, innings, innings_ball_num)""")

# Sanity check you can eyeball: WP should fall as the chase gets harder
print("\nSanity check - 2nd innings, 6 wickets left, 30 balls left, equal teams:")
chk = pd.DataFrame({"runs_needed": [20, 40, 60, 80], "wkts_left": 6, "balls_left": 30,
                    "elo_diff": 0.0, "is_ipl": 1, "score_before": 0, "venue_par": 0})
chk["rrr"] = 6 * chk.runs_needed / chk.balls_left
chk = add_features(chk, res_model)
chk["wp"] = models[2].predict_proba(chk[F2])[:, 1].round(3)
print(chk[["runs_needed", "balls_left", "wkts_left", "wp"]].to_string(index=False))
print("\nExpected further runs from 'resources' (balls left x wickets left):")
grid = pd.DataFrame([(b, w) for b in (120, 60, 30, 12) for w in (10, 7, 4, 2)], columns=["balls_left", "wkts_left"])
grid["exp_more"] = res_model.predict(grid).round(1)
gp = grid.pivot(index="balls_left", columns="wkts_left", values="exp_more").sort_index(ascending=False)
print(gp.to_string()); gp.to_csv("outputs/resources_table.csv")
print("\nDone. Calibration plot -> outputs/figures/wp_calibration.png")
