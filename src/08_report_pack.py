"""
08_report_pack.py  -  Collects every number, table and figure needed for the report
=====================================================================
RUN : python src/08_report_pack.py     (after 01, 05, 06, 07)
OUT : outputs/REPORT_DATA.md           (all evidence tables, in report order)
      outputs/figures/li_by_category.png, outcomes_by_li.png,
      outputs/figures/pressure_map_*.png, outputs/player_cards_*.csv
=====================================================================
"""
import os
import duckdb, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

con = duckdb.connect("superr.duckdb")
os.makedirs("outputs/figures", exist_ok=True)
q = lambda s: con.sql(s).df()
md = []
H = lambda t, lvl=2: md.append("\n" + "#" * lvl + " " + t + "\n")
T = lambda df, fmt=2: md.append(df.round(fmt).to_markdown(index=False) + "\n")
P = lambda t: md.append(t + "\n")

md.append("# SupeRR Selector S2 - Report data pack (auto-generated)\n")
P("Every number below is produced by the scripts in `src/` from the supplied CSVs. "
  "Re-run `01 -> 05 -> 06 -> 07 -> 08` to reproduce.")

# ------------------------------------------------------------------ 1. DATA
H("1. Data used and exclusions")
s = q("""
SELECT
 (SELECT COUNT(*) FROM matches) AS matches_total,
 (SELECT COUNT(DISTINCT match_id) FROM ball_by_ball) AS matches_with_balls,
 (SELECT COUNT(*) FROM ball_by_ball) AS deliveries_total,
 (SELECT COUNT(*) FROM ball_by_ball WHERE innings > 2) AS super_over_deliveries,
 (SELECT COUNT(*) FROM bad_matches) AS broken_matches_excluded,
 (SELECT COUNT(*) FROM matches WHERE NOT (win_team_id IN (home_team_id, away_team_id)) OR win_team_id IS NULL) AS no_result_matches,
 (SELECT COUNT(DISTINCT match_id) FROM model_balls) AS decided_matches_modelled,
 (SELECT COUNT(*) FROM model_balls) AS deliveries_modelled,
 (SELECT COUNT(*) FROM ball_value WHERE in_scope) AS deliveries_in_rating_scope
""")
T(s.T.reset_index().rename(columns={"index": "item", 0: "value"}), 0)
comp = q("""SELECT CASE WHEN comp_name LIKE 'IPL%' THEN 'IPL'
                        WHEN comp_name ILIKE '%Emerging%' OR comp_name ILIKE '%Rising Stars%' THEN 'Youth/A-team (excluded from ratings)'
                        ELSE 'T20I' END AS competition_group,
                   COUNT(DISTINCT match_id) AS matches, COUNT(*) AS deliveries
            FROM model_balls GROUP BY 1 ORDER BY 2 DESC""")
T(comp, 0)
P("**Cleaning rules:** `extras1_runs` is an extras-type code (6 none, 2 wide, 3 leg-bye, 4 bye, 1 overstep no-ball, "
  "5 other no-ball, 7 penalty); `extras_2_runs` = byes off a no-ball. Legal ball = not wide and not no-ball. "
  "Batter runs = `runs`; bowler runs = batter runs + wide/no-ball penalty (not byes/leg-byes); "
  "bowler wickets = Caught, Bowled, LBW, Stump, Hit Wicket (run outs, obstructing, retired out are team wickets only). "
  "Revised-overs columns are in balls. Super overs (innings 3-4) excluded. Season = year of match date.")

# ------------------------------------------------------------------ 2. VALIDATION
H("2. Validation of reconstructed scores")
v = q(r"""
WITH t AS (
  SELECT m.match_id, m.win_team_id, lower(m.result) res, TRY_CAST(m.revised_target AS INT) rt,
         i1.total t1, i2.total t2, i2.batting_team_id bat2
  FROM matches m JOIN innings_summary i1 ON i1.match_id=m.match_id AND i1.innings=1
                 JOIN innings_summary i2 ON i2.match_id=m.match_id AND i2.innings=2
  WHERE m.match_id NOT IN (SELECT match_id FROM bad_matches))
SELECT 'Batting-first wins: our margin minus official margin' AS check_,
       COUNT(*) AS matches,
       AVG(CASE WHEN abs((t1-t2) - TRY_CAST(regexp_extract(res,'(\d+)\s*run',1) AS INT)) = 0 THEN 1.0 ELSE 0 END) AS share_exact,
       AVG(CASE WHEN abs((t1-t2) - TRY_CAST(regexp_extract(res,'(\d+)\s*run',1) AS INT)) <= 5 THEN 1.0 ELSE 0 END) AS share_within_5,
       MEDIAN(abs((t1-t2) - TRY_CAST(regexp_extract(res,'(\d+)\s*run',1) AS INT))) AS median_abs_error
FROM t WHERE res LIKE '%run%' AND rt IS NULL
UNION ALL
SELECT 'Chasing wins: runs short of target (0 = reached)', COUNT(*),
       AVG(CASE WHEN COALESCE(rt, t1+1) - t2 <= 0 THEN 1.0 ELSE 0 END),
       AVG(CASE WHEN COALESCE(rt, t1+1) - t2 <= 5 THEN 1.0 ELSE 0 END),
       MEDIAN(GREATEST(COALESCE(rt, t1+1) - t2, 0))
FROM t WHERE win_team_id = bat2
""")
T(v, 3)
P("Before the strike-rotation fix (each extra counted as 1 run): batting-first margins exact in 31.6% of matches, "
  "within 2 runs in 57.7%; 73.4% of winning chases reached the reconstructed target.")
P("Chase targets used in the analysis, by source (anchored to the official result):")
T(q("SELECT target_source, COUNT(*) AS matches FROM chase_target GROUP BY 1 ORDER BY 2 DESC"), 0)
P("Manual check against ESPNcricinfo scorecards:")
T(pd.DataFrame([
    ["AUS v IND, 2nd T20I, 31 Oct 2025", "India (1st)", 125, 125, 0, ""],
    ["", "Australia (2nd)", 126, 119, -7, "Extras 10 after 4.1 overs"],
    ["AFG v SL, Asia Cup, 18 Sep 2025", "Afghanistan (1st)", 169, 166, -3, "Extras 7 (lb 5, nb 1, w 1)"],
    ["", "Sri Lanka (2nd)", 171, 162, -9, ""],
    ["SL v ZIM, 1st T20I, 14 Jan 2024", "Zimbabwe (1st)", 143, 143, 0, ""],
    ["", "Sri Lanka (2nd)", 144, 143, -1, ""]],
    columns=["match", "innings", "official", "reconstructed", "gap", "note"]), 0)
P("**Cause of gaps:** the data records that a wide/bye/leg-bye occurred but not how many runs it yielded. "
  "We infer odd/even runs from strike rotation (did the batters change ends?) - wide: crossed = 2 runs, else 1; "
  "bye/leg-bye: crossed = 1, else 4. Boundary wides stay undetectable (e.g. NZ v PAK, 17 Apr 2023: NZ 163 official, "
  "159 reconstructed). Because the most important deliveries are at the end of chases, the chase TARGET is anchored "
  "to the official result (e.g. NZ won by 4 and PAK made 159, so target = 164). Matches with gaps > 15 runs "
  "(missing deliveries) are excluded.")

# ------------------------------------------------------------------ 3. WP MODEL
H("3. Win-probability model")
T(pd.read_csv("outputs/wp_model_metrics.csv"), 3)
P("Lower is better; 'no-skill' = always predicting the base rate. Calibration: `figures/wp_calibration.png`.")
P("Expected further runs ('resources', learned from completed 1st innings) by balls left x wickets left:")
T(pd.read_csv("outputs/resources_table.csv"), 1)

# ------------------------------------------------------------------ 4. PRESSURE (LI)
H("4. Pressure definition: Leverage Index - evidence it separates pressure from ordinary play")
cat = pd.read_csv("outputs/li_by_category.csv")
T(cat, 3)
oc = pd.read_csv("outputs/outcomes_by_li.csv")
P("League-wide ball outcomes by leverage band (legal balls):")
T(oc, 3)
P("Highest-leverage deliveries in the data (sanity check - these are well-known last-ball finishes):")
T(pd.read_csv("outputs/top_li_moments.csv").head(10), 2)

fig, ax = plt.subplots(figsize=(8, 4.2))
c2 = cat[cat.situation != "ALL BALLS"].sort_values("mean_LI")
ax.barh(c2.situation, c2.mean_LI, color=["#c0392b" if x > 1 else "#7f8c8d" for x in c2.mean_LI])
ax.axvline(1, color="black", lw=.8, ls="--")
ax.text(1.02, -0.6, "average ball = 1", fontsize=8)
ax.set_xlabel("Mean Leverage Index of deliveries in this situation")
ax.set_title("Classic 'pressure' situations vs the Leverage Index")
fig.tight_layout(); fig.savefig("outputs/figures/li_by_category.png", dpi=150); plt.close(fig)

fig, ax1 = plt.subplots(figsize=(7.5, 4))
x = np.arange(len(oc))
ax1.bar(x - 0.2, 100 * oc.wicket_pct, width=0.4, color="#c0392b", label="Wicket % per ball")
ax1.bar(x + 0.2, 100 * oc.boundary_pct / 4, width=0.4, color="#1f4e79", label="Boundary % per ball (/4)")
ax1.set_xticks(x); ax1.set_xticklabels(oc.band.astype(str))
ax1.set_xlabel("Leverage Index band"); ax1.set_ylabel("% of legal balls")
ax2 = ax1.twinx(); ax2.plot(x, oc.run_rate, "o-", color="black", label="Run rate (rhs)")
ax2.set_ylabel("Runs per over")
h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")
ax1.set_title("Play changes as leverage rises: more risk, more wickets")
fig.tight_layout(); fig.savefig("outputs/figures/outcomes_by_li.png", dpi=150); plt.close(fig)

# pressure maps for two famous finishes
H("5. Match pressure maps", 3)
for date, team in [("2024-05-02", "Sunrisers Hyderabad"), ("2024-04-21", "Kolkata Knight Riders")]:
    mm = q(f"""SELECT match_id, home_team, away_team, result FROM matches
               WHERE match_date = DATE '{date}' AND (home_team = '{team}' OR away_team = '{team}')""")
    if mm.empty:
        continue
    mid = int(mm.match_id[0])
    b = q(f"""SELECT bv.innings, bv.innings_ball_num, bv.wp_before, bv.li, bv.batting_team_id,
                     bv.overid, bv.team_wicket
              FROM ball_value bv WHERE match_id = {mid} ORDER BY innings, innings_ball_num""")
    first_bat = b.loc[b.innings == 1, "batting_team_id"].iloc[0]
    b["wp_first"] = np.where(b.batting_team_id == first_bat, b.wp_before, 1 - b.wp_before)
    b["seq"] = np.arange(len(b))
    names = q(f"SELECT team_id, mode(team_name) n FROM teams WHERE team_id IN "
              f"(SELECT DISTINCT batting_team_id FROM ball_value WHERE match_id={mid}) GROUP BY team_id").set_index("team_id")["n"]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(b.seq, 100 * b.wp_first, color="#1f4e79", lw=1.5, label=f"Win probability: {names.get(first_bat, 'batting first')}")
    ax.set_ylabel("Win probability (%)"); ax.set_ylim(0, 100)
    w = b[b.team_wicket.astype(bool)]
    ax.scatter(w.seq, 100 * w.wp_first, color="#c0392b", s=14, zorder=3, label="Wicket")
    ax.axvline(b.loc[b.innings == 2, "seq"].min(), color="grey", ls=":", lw=1)
    ax2 = ax.twinx(); ax2.fill_between(b.seq, 0, b.li, color="#f39c12", alpha=0.35, label="Leverage Index")
    ax2.set_ylabel("Leverage Index (pressure)")
    ax.set_xlabel("Delivery number in match (dotted line = start of chase)")
    ax.set_title(f"{mm.home_team[0]} v {mm.away_team[0]}, {date}: {mm.result[0]}")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")
    fig.tight_layout()
    fn = f"pressure_map_{date}.png"
    fig.savefig(f"outputs/figures/{fn}", dpi=150); plt.close(fig)
    P(f"- `figures/{fn}`: {mm.home_team[0]} v {mm.away_team[0]} ({date}) - {mm.result[0]}")

H("Why LI >= 1.5?", 3)
li_share = q("SELECT AVG((li >= 1.0)::INT) a, AVG((li >= 1.5)::INT) b, AVG((li >= 2.0)::INT) c FROM ball_value")
P(f"(1) Convention: in baseball sabermetrics, where the Leverage Index originates (Tom Tango), LI = 1 is average "
  f"and values above roughly 1.5-2.0 are labelled high leverage; about 20% of plate appearances are high-leverage. "
  f"(2) In our data LI >= 1.5 selects {100*li_share.b[0]:.1f}% of deliveries (LI >= 1.0: {100*li_share.a[0]:.1f}%, "
  f">= 2.0: {100*li_share.c[0]:.1f}%) - the same 'top ~1 in 5' share. (3) It separates the brief's own categories: "
  f"see the table above (tight finishes and difficult chases mostly above 1.5, comfortable chases almost never). "
  f"(4) Ball outcomes change above it (more wickets and boundaries, higher run rate). (5) It is not "
  f"result-critical: thresholds 1.25 and 2.0 are reported in section 8.")

H("Pressure definition used for the rankings", 3)
P("A **pressure over** for a player is an over that STARTS with (a) Leverage Index >= 1.5 and (b) that player's side "
  "behind - batting side win probability <= 50% for batters; bowling side win probability <= 50% for bowlers. "
  "Judged at the start of the over so nothing the player does inside the over can switch pressure on or off. "
  "All balls of a pressure over are pressure balls (~10% of each role's balls). The v1 symmetric ball-level "
  "definition, a 40%/60% gate and LI thresholds 1.25/2.0 are reported as robustness checks (section 8).")

comp_rows = []
for role in ("bat", "bowl"):
    cmp = q(f"""SELECT p.pr, b.innings, b.overid, b.rrr, b.wk_last24, b.wkts_left, b.balls_left, b.runs_needed,
                       m.knock_out
                FROM player_ball_values_{role} p JOIN ball_value b USING (match_id, innings, innings_ball_num)
                JOIN matches m USING (match_id)""")
    pr = cmp[cmp.pr]
    comp_rows.append({"role": "batters" if role == "bat" else "bowlers",
                      "pressure balls": len(pr), "share of all balls %": 100 * cmp.pr.mean(),
                      "1st innings %": 100 * (pr.innings == 1).mean(),
                      "powerplay (ov 1-6) %": 100 * (pr.overid <= 6).mean(),
                      "middle (7-15) %": 100 * pr.overid.between(7, 15).mean(),
                      "death (16-20) %": 100 * (pr.overid >= 16).mean(),
                      "during collapse %": 100 * (pr.wk_last24 >= 3).mean(),
                      "knockout matches %": 100 * (pr.knock_out == 1).mean()})
P("Where pressure balls occur, by role:")
T(pd.DataFrame(comp_rows), 1)

# ------------------------------------------------------------------ 6. RELIABILITY
H("6. Which measures reflect skill rather than luck? (split-half reliability)")
rel = pd.read_csv("outputs/reliability_components.csv")
T(rel, 3)
P("Split-half r = correlation of a player's metric in odd- vs even-numbered matches (min 50 pressure balls each). "
  "`*_predicted_same_skill` = the reliability expected if pressure performance were simply the player's usual skill "
  "measured on ~19% of the balls (Spearman-Brown). Observed pressure-only reliability is at or below that prediction "
  "-> no evidence of a large, separate 'clutch' skill; our score therefore anchors on usual situation-adjusted skill "
  "and adds the pressure-specific deviation only as far as the data supports.")
T(pd.read_csv("outputs/shrinkage_constants.csv").replace(np.inf, "inf (no signal)"), 0)
P("k_pressure_dev = balls of pressure data at which a player's pressure-specific deviation gets 50% weight; "
  "'inf' = no repeatable pressure-specific signal detected.")
P("k = number of balls at which a player's own record and the prior get equal weight.")

# ------------------------------------------------------------------ 7. RANKINGS
for role, fname, label in [("bat", "batting", "Batters"), ("bowl", "bowling", "Bowlers")]:
    H(f"7{'a' if role == 'bat' else 'b'}. Top 10 {label} under pressure")
    r = pd.read_csv(f"outputs/{fname}_rankings.csv")
    cols = ["rank", "player_name", "teams", "pressure_balls", "pressure_matches", "PS", "PS_p10", "PS_p90",
            "P_top10_pct", "PS_overall", "clutch_delta", "pressure_innings", "pressure_failures", "consistency_pct"]
    cols += ["SR_all", "SR_pressure", "dismissal_pct_pressure"] if role == "bat" else \
        ["econ_all", "econ_pressure", "wkts_pressure"]
    T(r[cols].head(10), 2)
    P(("PS = runs ADDED vs an average batter in the identical situations" if role == "bat" else
       "PS = runs SAVED vs an average bowler in the identical situations") +
      " per 100 pressure balls (wickets converted to runs at their pressure-situation worth); "
      "PS_p10-p90 = bootstrap interval; P_top10 = % of 500 match re-samples in which the player is top 10; "
      "PS_overall = usual level (all balls); clutch_delta = shrunk pressure-specific adjustment; "
      "consistency = % of pressure innings (>= 3 pressure balls or dismissed/wicket on one) with positive value.")
    P("**Observed pressure-only record** (secondary, descriptive: pressure balls only, no shrinkage toward usual "
      "level; split-half reliability is low, so treat as a record of what happened, not a skill estimate):")
    obs = r.sort_values("PS_raw_pressure_only", ascending=False)
    T(obs[["player_name", "pressure_balls", "pressure_innings", "pressure_successes", "pressure_failures",
           "PS_raw_pressure_only", "PS", "rank"]].head(10).rename(columns={"rank": "main_rank"}), 2)
    cut = r.PS.iloc[9]
    above = r[(r.PS_raw_pressure_only > r.PS_overall) & (r["rank"] > 10)].copy()
    above["raw_gap"] = above.PS_raw_pressure_only - above.PS_overall

    def why(x):
        t = (f"Raw gap +{x.raw_gap:.1f} on {int(x.pressure_balls)} pressure balls; reliability supports "
             f"{x.clutch_delta:+.1f}, so PS = {x.PS_overall:.1f} {x.clutch_delta:+.1f} = {x.PS:.1f} < cut-off {cut:.1f}")
        if x.PS_overall + x.raw_gap >= cut:
            t += " (would enter only if the whole raw gap were taken at face value)"
        else:
            t += " (usual level too low even with the full raw gap)"
        return t
    above["reason_not_in_top10"] = above.apply(why, axis=1)
    P(f"**Above the diagonal but not in the top 10 - why** (diagonal y = x in `figures/quadrant_{role}.png` "
      f"means 'pressure record equals usual level'; top-10 cut-off = PS of #10 = {cut:.2f}). "
      f"See also `figures/selection_{role}.png`:")
    T(above.sort_values("PS", ascending=False)[["rank", "player_name", "pressure_balls", "PS_overall",
                                                "PS_raw_pressure_only", "clutch_delta", "PS",
                                                "reason_not_in_top10"]].head(15), 2)
    P(f"Positions 11-20 (for discussion of close calls):")
    T(r[["rank", "player_name", "PS", "PS_p10", "PS_p90", "P_top10_pct"]].iloc[10:20], 2)

    # player cards: three most valuable pressure spells, with entry -> exit state
    pv = q(f"""SELECT p.*, m.match_date, m.home_team, m.away_team
               FROM player_ball_values_{role} p JOIN matches m USING (match_id) WHERE p.pr""")
    pv["val"] = pv.rae + pv.c * pv.wae
    raw = q("""SELECT match_id, innings, innings_ball_num, overid, batter_runs, bowler_runs, team_wicket,
                      bowler_wicket, is_legal, score_before, wkts_left, runs_needed, balls_left FROM ball_value""")
    pv = pv.merge(raw, on=["match_id", "innings", "innings_ball_num"], how="left").sort_values(
        ["match_id", "innings", "innings_ball_num"])

    def state(r):
        if r.innings == 2 and pd.notna(r.runs_needed):
            return f"{int(r.runs_needed)} off {int(r.balls_left)}, {int(r.wkts_left)} wkts left"
        return f"{int(r.score_before)}/{10 - int(r.wkts_left)} after {int(r.overid) - 1} ov (1st inn)"

    cards = []
    for _, row in r.head(10).iterrows():
        sub = pv[pv.pid == row.player_id]
        for (mid, inn), g in sorted(sub.groupby(["match_id", "innings"]), key=lambda kv: -kv[1].val.sum())[:3]:
            first, last = g.iloc[0], g.iloc[-1]
            cards.append(dict(rank=row["rank"], player=row.player_name, date=str(first.match_date)[:10],
                              match=f"{first.home_team} v {first.away_team}", innings=inn,
                              entry_state=state(first), last_pressure_ball_state=state(last),
                              pressure_balls=len(g),
                              runs=int(g.batter_runs.sum() if role == "bat" else g.bowler_runs.sum()),
                              wickets=int(g.team_wicket.sum() if role == "bat" else g.bowler_wicket.sum()),
                              value_runs_above_avg=round(g.val.sum(), 1)))
    cards = pd.DataFrame(cards)
    cards.to_csv(f"outputs/player_cards_{fname}.csv", index=False)
    P(f"**Evidence cards - each top-10 {label.lower()[:-1]}'s three most valuable pressure innings** "
      f"(runs = {'scored' if role == 'bat' else 'conceded'} on pressure balls; wickets = "
      f"{'dismissals' if role == 'bat' else 'taken'}):")
    T(cards, 1)

# ------------------------------------------------------------------ 8. ROBUSTNESS
H("7c. Super overs (descriptive only - 6 super overs, 38 balls in the data)")
so = q("""SELECT strftime(m.match_date, '%Y-%m-%d') AS date, m.home_team || ' v ' || m.away_team AS match, b.innings,
                 b.striker_name AS batter, b.bowler_name AS bowler,
                 SUM(b.runs) AS batter_runs, COUNT(*) FILTER (WHERE COALESCE(b.extras_type,'None') NOT IN ('wide','Overstep','other')) AS legal_balls,
                 SUM(b.is_wicket) AS wickets
          FROM ball_by_ball b JOIN matches m USING (match_id)
          WHERE b.innings > 2 GROUP BY ALL ORDER BY date, b.innings""")
T(so, 0)
P("Too few deliveries to enter any rating (1-2 balls per player); reported for completeness.")

H("7d. Knockout matches")
ko_n = q("SELECT COUNT(*) n, string_agg(DISTINCT stage, ', ') stages FROM matches WHERE knock_out = 1")
P(f"{int(ko_n.n[0])} knockout matches ({ko_n.stages[0]}). How they enter the analysis: (a) every knockout delivery is "
  "scored by the same Leverage Index as any other ball - a tight knockout finish is a pressure over like a tight "
  "league finish; (b) we do NOT add an arbitrary knockout weight to the main score, because knockout samples are "
  "tiny (a player has 0-6 knockout innings) - instead (c) a robustness check multiplies knockout leverage by 1.5 "
  "(section 8), and (d) the descriptive tables below compare knockout and regular-match performance.")
for role, lab in [("bat", "batters"), ("bowl", "bowlers")]:
    ko = q(f"""SELECT m.knock_out = 1 AS knockout, COUNT(*) balls,
                      ROUND(100 * AVG(p.rae), 2) AS runs_above_exp_per100, ROUND(100 * AVG(p.wae), 3) AS wkts_above_exp_per100
               FROM player_ball_values_{role} p JOIN matches m USING (match_id) GROUP BY 1 ORDER BY 1""")
    P(f"League-wide, {lab} (situation-adjusted; ~0 means knockouts are not systematically different):")
    T(ko, 3)
for role, fname in [("bat", "batting"), ("bowl", "bowling")]:
    r = pd.read_csv(f"outputs/{fname}_rankings.csv").head(10)
    ko = q(f"""SELECT p.pid AS player_id, COUNT(DISTINCT p.match_id) ko_matches, COUNT(*) ko_balls,
                      SUM(b.{'batter_runs' if role == 'bat' else 'bowler_runs'}) runs,
                      SUM(b.{'team_wicket' if role == 'bat' else 'bowler_wicket'}::INT) {'outs' if role == 'bat' else 'wickets'},
                      ROUND(100 * AVG(p.rae + p.c * p.wae), 1) value_per100
               FROM player_ball_values_{role} p JOIN ball_value b USING (match_id, innings, innings_ball_num)
               JOIN matches m USING (match_id) WHERE m.knock_out = 1 GROUP BY 1""")
    t = r[["rank", "player_id", "player_name", "PS"]].merge(ko, on="player_id", how="left").drop(columns="player_id")
    P(f"Knockout record of the top-10 {fname[:-3]}ers (value_per100 = runs {'added' if role == 'bat' else 'saved'} vs "
      "average per 100 knockout balls; small samples - descriptive only):")
    T(t, 1)

H("8. Robustness of the top 10")
T(pd.read_csv("outputs/robustness.csv"), 2)
P("Top-10 overlap with the main list under each alternative; rank correlation over all eligible players.")

H("9. Figures")
for f in sorted(os.listdir("outputs/figures")):
    P(f"- `figures/{f}`")

open("outputs/REPORT_DATA.md", "w", encoding="utf-8").write("\n".join(md))
print("Wrote outputs/REPORT_DATA.md and figures.")
