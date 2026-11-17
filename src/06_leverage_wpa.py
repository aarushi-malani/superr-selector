"""
06_leverage_wpa.py  -  Pressure (Leverage Index) and credit (WPA) per ball
=====================================================================
LEVERAGE INDEX (our pressure measure)
  For each ball we ask: "how much could THIS ball move the match?"
  We take the realistic outcomes of a ball (dot, 1, 2, four, six,
  wicket, wide/no-ball) with their league frequencies for that innings
  and phase, compute the win probability after each one, and average
  the absolute swings:
        swing = sum_o  p(o) * |WP(after o) - WP(now)|
        LI    = swing / (average swing over all balls)
  LI = 1 -> an average ball.  LI = 3 -> three times as consequential.
  A PRESSURE BALL is LI >= 1.5 (thresholds 1.25 and 2.0 are tested in 07).

WIN PROBABILITY ADDED (credit)
  dWP = WP after the ball - WP before (batting side's view).
  Because the WP model already "expects" average play, an average player
  earns ~0 WPA in any situation. So WPA = value above an average player
  in that exact situation (target, wickets, balls, venue, opponent).
    batter : + dWP on every ball they face (wides excluded, they are the
             bowler's). If the NON-striker is run out, it is charged to him.
    bowler : - dWP on every ball they bowl, except run-outs / obstructing /
             retired out (not the bowler's doing).

RUN : python src/06_leverage_wpa.py
OUT : table ball_value (one row per delivery with li, dwp, credits)
      outputs/li_by_category.csv, outputs/outcomes_by_li.csv,
      outputs/top_li_moments.csv, outputs/figures/li_distribution.png
=====================================================================
"""
import os, pickle
import duckdb, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

os.makedirs("outputs/figures", exist_ok=True)
con = duckdb.connect("superr.duckdb")
W = pickle.load(open("models/wp_models.pkl", "rb"))
m1, m2, F1, F2, RES = W["models"][1], W["models"][2], W["F1"], W["F2"], W["resources"]

FULL_MEMBERS = {"Afghanistan", "Australia", "Bangladesh", "England", "India", "Ireland",
                "New Zealand", "Pakistan", "South Africa", "Sri Lanka", "West Indies", "Zimbabwe"}

df = con.sql("""
SELECT mb.*, d.xt, d.is_legal, d.team_wicket, d.bowler_wicket, d.team_runs, d.batter_runs,
       d.bowler_runs, d.striker_id, d.striker_name, d.non_striker_id, d.bowler_id, d.bowler_name,
       d.dismissed_player_id, d.dismissal_type, d.over_ball_num,
       m.knock_out, m.home_team, m.away_team, m.match_date
FROM model_balls mb
JOIN deliveries_clean d USING (match_id, innings, innings_ball_num)
JOIN matches m USING (match_id)
ORDER BY match_id, innings, innings_ball_num
""").df()
print(f"Balls: {len(df):,}")


# ------------------------------------------------------------------
# Win probability for ANY state (handles innings-ending states too)
# ------------------------------------------------------------------
def wp_state(inn, score, wkts_left, balls_left, need, elo, par, ipl, maxb):
    n = len(inn)
    out = np.full(n, np.nan)
    # first innings: always the 1st-innings model. If the innings ends (all out /
    # overs done) we feed balls_left = 0 so the model sees "no balls left".
    # (We deliberately do NOT switch to the chase model here: mixing two models on
    #  one ball creates fake swings. The hand-over between innings is credited to nobody.)
    i1 = inn == 1
    if i1.any():
        bl1 = np.where(wkts_left[i1] <= 0, 0, np.maximum(balls_left[i1], 0))
        wl1 = np.maximum(wkts_left[i1], 0)
        more = RES.predict(pd.DataFrame({"balls_left": bl1, "wkts_left": wl1}))
        more = np.where(bl1 <= 0, 0.0, more)
        X = pd.DataFrame({"proj_gap": score[i1] + more - par[i1], "wkts_left": wl1,
                          "balls_left": bl1, "elo_diff": elo[i1], "is_ipl": ipl[i1]})[F1]
        out[i1] = m1.predict_proba(X)[:, 1]
    # second innings
    i2 = inn == 2
    won = i2 & (need <= 0)
    over = i2 & ~won & ((wkts_left <= 0) | (balls_left <= 0))
    live2 = i2 & ~won & ~over
    out[won] = 1.0
    out[over] = np.where(need[over] == 1, 0.5, 0.0)          # need 1 = tie -> super over
    if live2.any():
        bl = np.maximum(balls_left[live2], 1)
        more = RES.predict(pd.DataFrame({"balls_left": bl, "wkts_left": wkts_left[live2]}))
        X = pd.DataFrame({"shortfall": need[live2] - more, "rrr": 6 * need[live2] / bl,
                          "wkts_left": wkts_left[live2], "balls_left": bl,
                          "elo_diff": elo[live2], "is_ipl": ipl[live2]})[F2]
        out[live2] = m2.predict_proba(X)[:, 1]
    return out


# ------------------------------------------------------------------
# 1. WP after each ball and dWP
# ------------------------------------------------------------------
g = df.groupby(["match_id", "innings"])
df["wp_after"] = g["wp_before"].shift(-1)
# last ball of the 1st innings: WP of the end-of-innings state (same model);
# last ball of the 2nd innings: the actual result (1 = batting side won, 0 = lost)
last1 = df.innings.eq(1) & df.wp_after.isna()
end_score = (df.score_before + df.team_runs).values
end_wl = (df.wkts_left - df.team_wicket.astype(int)).values
end_bl = (df.balls_left - df.is_legal.astype(int)).values
z = np.zeros(len(df))
wp_end1 = wp_state(np.where(last1, 1, 0), end_score, end_wl, np.where(last1, 0, end_bl), z,
                   df.elo_diff.values, df.venue_par.values, df.is_ipl.values, df.max_balls.values)
df.loc[last1, "wp_after"] = wp_end1[last1.values]
still = df.wp_after.isna()
df.loc[still, "wp_after"] = df.loc[still, "bat_won"].astype(float)
df["dwp"] = df.wp_after - df.wp_before

# ------------------------------------------------------------------
# 2. Leverage Index
# ------------------------------------------------------------------
df["phase"] = pd.cut(df.overid, [0, 6, 15, 99], labels=["powerplay", "middle", "death"]).astype(str)


def outcome(r_legal, r_wkt, r_runs):
    if not r_legal:
        return "X"
    if r_wkt:
        return "W"
    return {0: "0", 1: "1", 2: "2", 3: "2", 4: "4", 5: "4"}.get(int(r_runs), "6")


df["oc"] = [outcome(a, b, c) for a, b, c in zip(df.is_legal, df.team_wicket, df.team_runs)]
probs = (df.groupby(["innings", "phase"])["oc"].value_counts(normalize=True)
         .rename("p").reset_index())
print("\nBall-outcome frequencies used for LI (by innings & phase):")
print(probs.pivot_table(index=["innings", "phase"], columns="oc", values="p").round(3).to_string())

# effect of each outcome on the state: (runs added, ball used, wicket)
EFFECT = {"0": (0, 1, 0), "1": (1, 1, 0), "2": (2, 1, 0), "4": (4, 1, 0),
          "6": (6, 1, 0), "W": (0, 1, 1), "X": (1, 0, 0)}
inn, sc, wl, bl = df.innings.values, df.score_before.values, df.wkts_left.values, df.balls_left.values
need = df.runs_needed.fillna(0).values
elo, par, ipl, maxb = df.elo_diff.values, df.venue_par.values, df.is_ipl.values, df.max_balls.values
P, WPO = [], []
for o, (r, b, w) in EFFECT.items():
    P.append(df[["innings", "phase"]].merge(probs[probs.oc == o], how="left",
                                            on=["innings", "phase"])["p"].fillna(0).values)
    WPO.append(wp_state(inn, sc + r, wl - w, bl - b, need - r, elo, par, ipl, maxb))
P, WPO = np.array(P), np.array(WPO)
P = P / P.sum(axis=0)
expected = (P * WPO).sum(axis=0)              # expected WP after this ball
swing = (P * np.abs(WPO - expected)).sum(axis=0)  # how much the outcome of THIS ball matters
df["swing"] = swing
# marginal values used for the component (runs / wickets) rating in step 07:
#   v_run  = win-probability gained per extra run on this ball
#   v_wkt  = win-probability lost if a wicket falls on this ball
keys = list(EFFECT.keys())
WP0, WP4, WPW = WPO[keys.index("0")], WPO[keys.index("4")], WPO[keys.index("W")]
df["v_run"] = (WP4 - WP0) / 4
df["v_wkt"] = WP0 - WPW
df["li"] = swing / swing.mean()
print(f"\nLI quantiles: " + ", ".join(f"p{int(q*100)}={df.li.quantile(q):.2f}"
                                       for q in [.1, .25, .5, .75, .9, .99]))
for t in [1.25, 1.5, 2.0]:
    print(f"Share of balls with LI >= {t}: {(df.li >= t).mean():.1%}")

# ------------------------------------------------------------------
# 3. Credit (WPA)
# ------------------------------------------------------------------
for c in ["team_wicket", "bowler_wicket", "is_legal"]:
    df[c] = df[c].fillna(False).astype(bool)
not_bowler = (df.dismissal_type.isin(["RunOut", "Obstructing the field",
                                      "Obstracting the field", "Retire Out"]) & df.team_wicket).fillna(False).astype(bool)
ns_out = (df.team_wicket & (df.dismissed_player_id == df.non_striker_id)).fillna(False).astype(bool)
df["bat_player_id"] = np.where(ns_out, df.non_striker_id, df.striker_id)
df.loc[df.xt == "wide", "bat_player_id"] = np.nan
df["bat_wpa"] = np.where(df.bat_player_id.notna(), df.dwp, np.nan)
df["bowl_wpa"] = np.where(not_bowler, np.nan, -df.dwp)

# rating scope: IPL + T20I only (youth / A-team events excluded), no broken matches
df["in_scope"] = ~df.comp_name.str.contains("Emerging|Rising Stars", case=False, na=False)
df["full_member_or_ipl"] = (df.is_ipl == 1) | (df.home_team.isin(FULL_MEMBERS) & df.away_team.isin(FULL_MEMBERS))

# ------------------------------------------------------------------
# 4. Evidence that LI separates pressure from ordinary situations
# ------------------------------------------------------------------
df["wk_last24"] = (df.groupby(["match_id", "innings"])["team_wicket"]
                   .transform(lambda s: s.astype(int).rolling(24, min_periods=1).sum().shift(1).fillna(0)))
df["rrr"] = np.where(df.innings == 2, 6 * need / np.maximum(bl, 1), np.nan)
cats = {
    "Batting collapse (3+ wkts in last 24 balls)": df.wk_last24 >= 3,
    "Difficult chase (RRR >= 10)": (df.innings == 2) & (df.rrr >= 10),
    "Tight finish (2nd inn, <=36 balls, RRR 7-13)": (df.innings == 2) & (bl <= 36) & df.rrr.between(7, 13),
    "Death overs (16-20), any": df.overid >= 16,
    "Knockout match": df.knock_out == 1,
    "Comfortable chase (RRR < 6, 7+ wkts in hand)": (df.innings == 2) & (df.rrr < 6) & (wl >= 7),
    "1st inn powerplay, no wicket down": (df.innings == 1) & (df.overid <= 6) & (df.wkts_left == 10),
    "ALL BALLS": pd.Series(True, index=df.index),
}
tab = pd.DataFrame([{"situation": k, "balls": int(v.sum()), "mean_LI": df.loc[v, "li"].mean(),
                     "share_pressure_LI>=1.5": (df.loc[v, "li"] >= 1.5).mean()} for k, v in cats.items()])
print("\nMean Leverage Index by classic 'pressure' situation:")
print(tab.round(3).to_string(index=False))
tab.to_csv("outputs/li_by_category.csv", index=False)

legal = df[df.is_legal]
legal = legal.assign(band=pd.cut(legal.li, [0, .5, 1, 1.5, 2.5, 99],
                                 labels=["<0.5", "0.5-1", "1-1.5", "1.5-2.5", ">2.5"]))
oc = legal.groupby("band", observed=True).agg(
    balls=("li", "size"),
    dot_pct=("team_runs", lambda s: ((s == 0) & ~legal.loc[s.index, "team_wicket"]).mean()),
    boundary_pct=("batter_runs", lambda s: s.isin([4, 6]).mean()),
    wicket_pct=("team_wicket", "mean"),
    run_rate=("team_runs", lambda s: 6 * s.mean())).reset_index()
print("\nHow ball outcomes change with leverage (legal balls):")
print(oc.round(3).to_string(index=False))
oc.to_csv("outputs/outcomes_by_li.csv", index=False)

top = df.nlargest(15, "li")[["match_date", "home_team", "away_team", "innings", "overid", "over_ball_num",
                            "score_before", "wkts_left", "runs_needed", "balls_left",
                            "striker_name", "bowler_name", "wp_before", "li"]]
print("\nTop 15 highest-leverage balls (sanity check - do these look like famous finishes?):")
print(top.round({'wp_before': 2, 'li': 2}).to_string(index=False))
top.to_csv("outputs/top_li_moments.csv", index=False)

fig, ax = plt.subplots(figsize=(7, 4))
ax.hist(df.li.clip(upper=6), bins=60, color="#3b6ea5")
ax.axvline(1.5, color="#c0392b", ls="--", label="Pressure threshold (LI = 1.5)")
ax.set_xlabel("Leverage Index (1 = average ball; clipped at 6)")
ax.set_ylabel("Number of deliveries")
ax.set_title("Distribution of ball-by-ball pressure")
ax.legend()
fig.tight_layout()
fig.savefig("outputs/figures/li_distribution.png", dpi=150)

keep = ["match_id", "innings", "innings_ball_num", "overid", "phase", "season", "comp_name", "is_ipl",
        "knock_out", "in_scope", "full_member_or_ipl", "batting_team_id", "bowling_team_id",
        "striker_id", "non_striker_id", "bowler_id", "bat_player_id", "xt", "is_legal",
        "team_wicket", "bowler_wicket", "team_runs", "batter_runs", "bowler_runs",
        "score_before", "wkts_left", "balls_left", "runs_needed", "rrr", "wk_last24",
        "wp_before", "wp_after", "dwp", "li", "bat_wpa", "bowl_wpa", "v_run", "v_wkt"]
con.register("bv_tmp", df[keep])
con.execute("CREATE OR REPLACE TABLE ball_value AS SELECT * FROM bv_tmp")
print("\nDone. Table ball_value written.")
