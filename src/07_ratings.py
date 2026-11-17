"""
07_ratings.py  -  Pressure ratings (component empirical-Bayes), reliability, robustness
=====================================================================
WHY THIS DESIGN (evidence from our own reliability tests, see outputs/reliability_*.csv)
  * Raw Win Probability Added per pressure ball is dominated by luck:
    split-half reliability ~0.1. Ranking on it is close to a lottery.
  * Leverage is therefore used to SELECT pressure balls, and performance on
    them is measured in situation-adjusted units, split into two components:
        RAE = runs above expected   (batter runs, or runs conceded for bowlers)
        WAE = wickets above expected (dismissals avoided / wickets taken)
    "Expected" = what an average player produces in the identical situation
    (innings, over, wickets left, balls left, required rate, score, competition),
    estimated by a gradient-boosting model on all deliveries.

PRESSURE ESTIMATE PER COMPONENT (hierarchical / empirical-Bayes)
    overall_i  = player's mean on ALL balls, shrunk toward the league mean
    dev_i      = (mean on PRESSURE balls) - overall_i, shrunk toward 0 by the
                 measured reliability of pressure-specific deviations
    pressure_i = overall_i + dev_i
  -> uses every ball we have, but lets genuine pressure over/under-performance
     move a player exactly as much as the data can support.

PRESSURE SCORE (PS) - the ranking metric, in RUNS per 100 pressure balls
    PS = 100 * ( RAE_pressure + c * WAE_pressure )
    c  = runs a wicket is worth in pressure situations (= avg win-prob value of
         a wicket / avg win-prob value of a run, over pressure balls)
  Read: "in high-pressure situations this player is worth +PS runs per 100
  balls more than an average player in the identical situations."

RUN : python src/07_ratings.py
OUT : outputs/batting_rankings.csv, outputs/bowling_rankings.csv,
      outputs/reliability_components.csv, outputs/robustness.csv,
      outputs/figures/top10_*.png, quadrant_*.png, reliability.png
=====================================================================
"""
import os
import duckdb, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import pearsonr, spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier

# ----------------------- CONFIGURATION ------------------------------
LI_THRESHOLD = 1.5
# PRESSURE DEFINITION
#   "role_over" (main): an over is a pressure over for a player if, at the START of the over,
#       (a) leverage is high (LI of the over's first ball >= LI_THRESHOLD) and
#       (b) that player's side is behind: batting side win prob <= GATE (batters),
#           bowling side win prob <= GATE, i.e. batting side >= 1 - GATE (bowlers).
#       Judged at the start of the over, so nothing the player does inside the over
#       can switch pressure on or off (no "self-made pressure", no truncated success).
#   "symmetric_ball" (v1, robustness): any ball with LI >= LI_THRESHOLD, for both roles.
PRESSURE_MODE = "role_over"
GATE = 0.5
MIN_PRESSURE_BALLS = {"bat": 60, "bowl": 60}
MIN_PRESSURE_MATCHES = 6
N_BOOT = 500
N_SPLITS = 20       # random half-splits used to estimate shrinkage constants
SEED = 7
# --------------------------------------------------------------------
os.makedirs("outputs/figures", exist_ok=True)
con = duckdb.connect("superr.duckdb")
rng = np.random.default_rng(SEED)

bv = con.sql("SELECT * FROM ball_value").df()
for c in ["team_wicket", "bowler_wicket", "is_legal", "in_scope", "full_member_or_ipl"]:
    bv[c] = bv[c].fillna(False).astype(bool)
bv["rrr_f"] = bv.rrr.fillna(-1)
names = con.sql("SELECT player_id, mode(player_name) AS n FROM competition_team_player_mapping "
                "GROUP BY player_id").df().set_index("player_id")["n"]
team_names = con.sql("SELECT team_id, mode(team_name) AS n FROM teams GROUP BY team_id").df() \
    .set_index("team_id")["n"]

# ------------------------------------------------------------------
# 1. Expected runs / wickets for an AVERAGE player in each exact situation
# ------------------------------------------------------------------
X = ["innings", "overid", "wkts_left", "balls_left", "rrr_f", "score_before", "is_ipl", "season"]   # season: scoring rose sharply from 2023
faced = bv[bv.xt != "wide"]
kw = dict(max_iter=200, min_samples_leaf=300, random_state=SEED)
bv["xr_bat"] = HistGradientBoostingRegressor(**kw).fit(faced[X], faced.batter_runs).predict(bv[X])
bv["xw_bat"] = HistGradientBoostingClassifier(**kw).fit(faced[X], faced.team_wicket).predict_proba(bv[X])[:, 1]
bv["xr_bowl"] = HistGradientBoostingRegressor(**kw).fit(bv[X], bv.bowler_runs).predict(bv[X])
bv["xw_bowl"] = HistGradientBoostingClassifier(**kw).fit(bv[X], bv.bowler_wicket).predict_proba(bv[X])[:, 1]
bv = bv[bv.in_scope].copy()


def role_frame(role, data, T=LI_THRESHOLD, mode=None, gate=None):
    mode = PRESSURE_MODE if mode is None else mode
    gate = GATE if gate is None else gate
    data = data.sort_values(["match_id", "innings", "innings_ball_num"])
    grp = data.groupby(["match_id", "innings", "overid"], sort=False)
    li_over, wp_over = grp.li.transform("first"), grp.wp_before.transform("first")
    if mode == "symmetric_ball":
        pr_all = data.li >= T
    elif role == "bat":
        pr_all = (li_over >= T) & (wp_over <= gate)
    else:
        pr_all = (li_over >= T) & (wp_over >= 1 - gate)
    data = data.assign(pr=pr_all.values, li_over=li_over.values, wp_over=wp_over.values)
    if role == "bat":
        d = data[data.bat_player_id.notna()].copy()
        d["pid"], d["team"] = d.bat_player_id.astype("int64"), d.batting_team_id
        d["rae"] = d.batter_runs - d.xr_bat                       # + = more runs than expected
        d["wae"] = -(d.team_wicket.astype(float) - d.xw_bat)      # + = fewer dismissals than expected
        d["wpa"] = d.bat_wpa
        d["out"] = d.team_wicket.astype(int)
    else:
        d = data[data.bowl_wpa.notna()].copy()
        d["pid"], d["team"] = d.bowler_id.astype("int64"), d.bowling_team_id
        d["rae"] = -(d.bowler_runs - d.xr_bowl)                  # + = fewer runs conceded than expected
        d["wae"] = d.bowler_wicket.astype(float) - d.xw_bowl     # + = more wickets than expected
        d["wpa"] = d.bowl_wpa
        d["out"] = d.bowler_wicket.astype(int)
    return d


def moments(d, col):
    """Per-player mean, n, and pooled within-player variance."""
    g = d.groupby("pid")[col].agg(["mean", "var", "count"])
    g["var"] = g["var"].fillna(0)
    sigma2 = (g["var"] * (g["count"] - 1)).sum() / max(g["count"].sum() - len(g), 1)
    return g, sigma2


def estimate(d, T=LI_THRESHOLD, k_fixed=None):
    """Hierarchical component estimates. Returns per-player table + shrinkage constants."""
    p = d.pr
    out, ks = {}, {}
    for comp in ["rae", "wae"]:
        ga, s2a = moments(d, comp)
        gp, s2p = moments(d[p], comp)
        mu = d[comp].mean()
        if k_fixed is None:
            # Variance of TRUE player differences, estimated as the covariance of player means
            # across two random halves of the matches (luck in the two halves is independent,
            # so only repeatable skill survives). Averaged over N_SPLITS random partitions so
            # one lucky split cannot drive the result.
            #   tau2     : spread of overall skill            -> k_all = noise / tau2
            #   tau2_dev : spread of pressure-specific skill  -> k_dev = noise / tau2_dev
            mids = np.sort(d.match_id.unique())
            cov_all, cov_dev = [], []
            for sp in range(N_SPLITS):
                side = pd.Series(np.random.default_rng(1000 + sp).random(len(mids)) < 0.5, index=mids)
                half = d.match_id.map(side)
                A, D = [], []
                for h in (True, False):
                    dh = d[half == h]
                    a_h = dh.groupby("pid")[comp].agg(["mean", "count"])
                    p_h = dh[dh.pr].groupby("pid")[comp].agg(["mean", "count"])
                    A.append(a_h["mean"].where(a_h["count"] >= 100))
                    D.append((p_h["mean"] - a_h["mean"].reindex(p_h.index)).where(p_h["count"] >= 25))
                aa, dd = pd.concat(A, axis=1).dropna(), pd.concat(D, axis=1).dropna()
                if len(aa) > 10:
                    cov_all.append(np.cov(aa.iloc[:, 0], aa.iloc[:, 1])[0, 1])
                if len(dd) > 10:
                    cov_dev.append(np.cov(dd.iloc[:, 0], dd.iloc[:, 1])[0, 1])
            tau2 = max(np.mean(cov_all), 1e-9) if cov_all else 1e-9
            tau2_dev = max(np.mean(cov_dev), 0.0) if cov_dev else 0.0
            k_all = s2a / tau2
            k_dev = s2p / tau2_dev if tau2_dev > 0 else np.inf
        else:
            k_all, k_dev = k_fixed[comp]
        overall = (ga["count"] * ga["mean"] + k_all * mu) / (ga["count"] + k_all)
        gp = gp.join(overall.rename("overall"), how="left")
        w = 0.0 if np.isinf(k_dev) else gp["count"] / (gp["count"] + k_dev)
        gp["dev"] = w * (gp["mean"] - gp["overall"])
        out[comp] = pd.DataFrame({f"{comp}_overall": overall, f"{comp}_p_raw": gp["mean"],
                                  f"{comp}_dev": gp["dev"]})
        out[comp][f"{comp}_pressure"] = out[comp][f"{comp}_overall"] + out[comp][f"{comp}_dev"].fillna(0)
        ks[comp] = (k_all, k_dev)
    return out["rae"].join(out["wae"], how="outer"), ks


def wicket_rate(d, T=LI_THRESHOLD):
    """Runs a wicket is worth in pressure situations (ratio of average WP values)."""
    p = d[d.pr]
    return p.v_wkt.mean() / p.v_run.mean()


def rate(role, data, T=LI_THRESHOLD, k_fixed=None, c_fixed=None, mode=None, gate=None):
    d = role_frame(role, data, T, mode, gate)
    est, ks = estimate(d, T, k_fixed)
    c = wicket_rate(d, T) if c_fixed is None else c_fixed
    p = d[d.pr]
    res = est.copy()
    res["PS"] = 100 * (res.rae_pressure + c * res.wae_pressure)
    res["PS_overall"] = 100 * (res.rae_overall + c * res.wae_overall)
    res["clutch_delta"] = 100 * (res.rae_dev.fillna(0) + c * res.wae_dev.fillna(0))
    res["PS_raw_pressure_only"] = 100 * (res.rae_p_raw + c * res.wae_p_raw)
    res["pressure_balls"] = p.groupby("pid").size()
    res["pressure_matches"] = p.groupby("pid").match_id.nunique()
    res["matches"] = d.groupby("pid").match_id.nunique()
    res["balls_total"] = d.groupby("pid").size()
    res["pressure_WPA_total"] = p.groupby("pid").wpa.sum()            # realised match-winning contribution
    # a pressure innings/spell = >= 3 pressure balls OR an out on a pressure ball
    # (so quick dismissals under pressure count as failures - they are NOT dropped)
    inns = p.groupby(["pid", "match_id", "innings"]).agg(
        n=("rae", "size"), v=("rae", "sum"), w=("wae", "sum"), outs=("out", "sum"))
    inns = inns[(inns.n >= 3) | (inns.outs > 0)]
    inns["val"] = inns.v + c * inns.w
    res["pressure_innings"] = inns.groupby("pid").size()
    res["pressure_successes"] = inns[inns.val > 0].groupby("pid").size()
    res["pressure_failures"] = inns[inns.val <= 0].groupby("pid").size()
    res["consistency_pct"] = 100 * inns.assign(pos=inns.val > 0).groupby("pid").pos.mean()
    res["share_chase_pct"] = 100 * p.groupby("pid").innings.apply(lambda s: (s == 2).mean())
    res["share_death_pct"] = 100 * p.groupby("pid").overid.apply(lambda s: (s >= 16).mean())
    res = res.fillna({"pressure_balls": 0, "pressure_matches": 0})
    res["eligible"] = (res.pressure_balls >= MIN_PRESSURE_BALLS[role]) & \
                      (res.pressure_matches >= MIN_PRESSURE_MATCHES)
    return res, d, ks, c


def traditional(role, d, T=LI_THRESHOLD):
    rows = []
    for tag, sub in [("all", d), ("pressure", d[d.pr])]:
        if role == "bat":
            f = sub[sub.xt != "wide"]
            g = f.groupby("striker_id").agg(r=("batter_runs", "sum"), b=("batter_runs", "size"))
            outs = sub[sub.team_wicket].groupby("pid").size()
            g.index = g.index.astype("int64")
            g[f"SR_{tag}"] = 100 * g.r / g.b
            g[f"avg_{tag}"] = g.r / outs.reindex(g.index)
            g[f"dismissal_pct_{tag}"] = 100 * outs.reindex(g.index).fillna(0) / g.b
            rows.append(g[[f"SR_{tag}", f"avg_{tag}", f"dismissal_pct_{tag}"]])
        else:
            g = sub.groupby("pid").agg(r=("bowler_runs", "sum"), lb=("is_legal", "sum"),
                                       w=("bowler_wicket", "sum"))
            g[f"econ_{tag}"] = 6 * g.r / g.lb
            g[f"wkts_{tag}"] = g.w
            g[f"ball_SR_{tag}"] = g.lb / g.w.replace(0, np.nan)
            rows.append(g[[f"econ_{tag}", f"wkts_{tag}", f"ball_SR_{tag}"]])
    return pd.concat(rows, axis=1)


def top10(res, col="PS"):
    return list(res[res.eligible].sort_values(col, ascending=False).index[:10])


def split_half(role, data, col_list, minb=50):
    """Correlate player metrics computed on odd vs even match_id."""
    halves = []
    for h in (0, 1):
        r, _, _, _ = rate(role, data[data.match_id % 2 == h])
        halves.append(r)
    j = halves[0].join(halves[1], lsuffix="_0", rsuffix="_1", how="inner")
    j = j[(j.pressure_balls_0 >= minb) & (j.pressure_balls_1 >= minb)]
    out = {}
    for c in col_list:
        jj = j[[f"{c}_0", f"{c}_1"]].dropna()
        out[c] = (pearsonr(jj[f"{c}_0"], jj[f"{c}_1"])[0], len(jj))
    return out


rel_rows, robust_rows, ks_rows = [], [], []
for role, label in [("bat", "BATTERS"), ("bowl", "BOWLERS")]:
    res, d, ks, c = rate(role, bv)
    print(f"\n================ {label} ================")
    print(f"Wicket value in pressure situations: c = {c:.1f} runs")
    for comp, (ka, kd) in ks.items():
        print(f"  {comp}: k_overall = {ka:,.0f} balls, k_pressure_deviation = "
              f"{'inf (no detectable pressure-specific signal)' if np.isinf(kd) else f'{kd:,.0f} balls'}")
        ks_rows.append(dict(role=role, component=comp, k_overall=ka, k_pressure_dev=kd))
    print(f"Eligible: {int(res.eligible.sum())} players "
          f"(>= {MIN_PRESSURE_BALLS[role]} pressure balls, >= {MIN_PRESSURE_MATCHES} matches)")

    # ---- bootstrap over matches (Poisson weights), shrinkage constants held fixed ----
    # Pre-aggregate per (player, match): sums and counts on all balls and on pressure balls,
    # so each re-sample is just a weighted sum (fast).
    elig = res.index[res.eligible]
    agg = d.groupby(["pid", "match_id"]).agg(
        n_a=("rae", "size"), r_a=("rae", "sum"), w_a=("wae", "sum")).join(
        d[d.pr].groupby(["pid", "match_id"]).agg(n_p=("rae", "size"), r_p=("rae", "sum"), w_p=("wae", "sum")),
        how="left").fillna(0).reset_index()
    pi, players = pd.factorize(agg.pid)
    mi, mids = pd.factorize(agg.match_id)
    (ka_r, kd_r), (ka_w, kd_w) = ks["rae"], ks["wae"]
    boot = np.zeros((N_BOOT, len(players)))
    for b in range(N_BOOT):
        wt = rng.poisson(1.0, len(mids))[mi]
        S = {k_: np.bincount(pi, weights=agg[k_].values * wt, minlength=len(players))
             for k_ in ["n_a", "r_a", "w_a", "n_p", "r_p", "w_p"]}
        val = 0
        for comp, tot_col, p_col, ka, kd in [("r", "r_a", "r_p", ka_r, kd_r), ("w", "w_a", "w_p", ka_w, kd_w)]:
            mu = S[tot_col].sum() / S["n_a"].sum()
            overall = (S[tot_col] + ka * mu) / (S["n_a"] + ka)
            with np.errstate(invalid="ignore", divide="ignore"):
                pmean = np.where(S["n_p"] > 0, S[p_col] / S["n_p"], overall)
            wdev = 0.0 if np.isinf(kd) else S["n_p"] / (S["n_p"] + kd)
            comp_p = overall + wdev * (pmean - overall)
            val = val + (comp_p if comp == "r" else c * comp_p)
        boot[b] = 100 * val
    B = pd.DataFrame(boot.T, index=players.astype("int64")).reindex(elig)
    ranks = B.rank(ascending=False, axis=0)
    res.loc[elig, "PS_p10"] = B.quantile(.1, axis=1)
    res.loc[elig, "PS_p90"] = B.quantile(.9, axis=1)
    res.loc[elig, "P_top10_pct"] = 100 * (ranks <= 10).mean(axis=1)
    res.loc[elig, "median_rank"] = ranks.median(axis=1)

    res = res.join(traditional(role, d), how="left")
    side = "batting_team_id" if role == "bat" else "bowling_team_id"
    tm = (d.groupby(["pid", side]).size().reset_index(name="n").sort_values("n", ascending=False)
          .groupby("pid")[side].apply(lambda s: " / ".join(team_names.reindex(s.head(2)).fillna("?").astype(str))))
    res.insert(0, "player_name", names.reindex(res.index).values)
    res.insert(1, "teams", tm.reindex(res.index).values)

    ranked = res[res.eligible].sort_values("PS", ascending=False).copy()
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    ranked.index.name = "player_id"
    fname = "batting" if role == "bat" else "bowling"
    ranked.round(3).to_csv(f"outputs/{fname}_rankings.csv")
    pbv = d[["pid", "match_id", "innings", "innings_ball_num", "li", "li_over", "wp_over", "pr",
             "rae", "wae"]].assign(role=role, c=c)
    con.register("pbv_tmp", pbv)
    con.execute(f"CREATE OR REPLACE TABLE player_ball_values_{role} AS SELECT * FROM pbv_tmp")

    show = ["rank", "player_name", "pressure_balls", "PS", "PS_p10", "PS_p90", "P_top10_pct",
            "PS_overall", "clutch_delta", "pressure_innings", "pressure_failures", "consistency_pct"]
    show += ["SR_all", "SR_pressure", "dismissal_pct_pressure"] if role == "bat" else \
        ["econ_all", "econ_pressure", "wkts_pressure"]
    pd.set_option("display.width", 250)
    print(ranked[show].head(20).round(2).to_string(index=False))

    # ---- reliability of components: observed vs 'same skill, fewer balls' ----
    sh = split_half(role, bv, ["rae_overall", "wae_overall", "rae_p_raw", "wae_p_raw", "PS",
                               "PS_raw_pressure_only", "clutch_delta"])
    n_ratio = d.pr.mean()
    print("Split-half reliability (odd vs even matches):")
    for k_, (r_, n_) in sh.items():
        if np.isnan(r_):
            continue
        print(f"  {k_:22s} r = {r_:5.2f}  (n = {n_})")
        rel_rows.append(dict(role=role, metric=k_, split_half_r=round(r_, 3), players=n_))
    for comp in ["rae", "wae"]:
        r_all = sh[f"{comp}_overall"][0]
        pred = n_ratio * r_all / (1 - (1 - n_ratio) * r_all)
        print(f"  {comp}: pressure-only r = {sh[f'{comp}_p_raw'][0]:.2f} vs {pred:.2f} predicted if it were "
              f"the SAME skill measured on {n_ratio:.0%} of the balls")
        rel_rows.append(dict(role=role, metric=f"{comp}_pressure_predicted_same_skill",
                             split_half_r=round(pred, 3), players=np.nan))

    # ---- robustness ----
    main = top10(res)
    variants = {"v1 symmetric ball-level LI>=1.5": rate(role, bv, mode="symmetric_ball")[0]}
    variants.update({f"Behind-gate at {g:.0%}": rate(role, bv, gate=g)[0] for g in (0.4, 0.6)})
    variants.update({f"LI threshold {t}": rate(role, bv, T=t)[0] for t in (1.25, 2.0)})
    variants["Full members + IPL only"] = rate(role, bv[bv.full_member_or_ipl])[0]
    variants["IPL only"] = rate(role, bv[bv.is_ipl == 1])[0]
    bv_n = bv.copy(); bv_n["li"] = bv_n.li / bv_n.groupby("innings").li.transform("mean")
    variants["LI rescaled within innings"] = rate(role, bv_n)[0]
    bv_k = bv.copy(); bv_k.loc[bv_k.knock_out == 1, "li"] *= 1.5
    variants["Knockout leverage x1.5"] = rate(role, bv_k)[0]
    variants["Wicket valued at 2x"] = rate(role, bv, c_fixed=2 * c)[0]
    variants["Wicket valued at 0.5x"] = rate(role, bv, c_fixed=0.5 * c)[0]
    print("Robustness of the top 10:")
    for name, v in variants.items():
        common = res[res.eligible].index.intersection(v[v.eligible].index)
        rho = spearmanr(res.loc[common, "PS"], v.loc[common, "PS"])[0]
        ov = len(set(main) & set(top10(v)))
        print(f"  {name:28s}: top-10 overlap {ov}/10, rank correlation {rho:.2f}")
        robust_rows.append(dict(role=role, check=name, top10_overlap=ov, rank_corr=round(rho, 3)))
    for name, col in [("Rank by lower 80% bound", "PS_p10"), ("Raw pressure-only (no shrinkage)", "PS_raw_pressure_only"),
                      ("Realised pressure WPA total", "pressure_WPA_total")]:
        ov = len(set(main) & set(top10(res, col)))
        print(f"  {name:28s}: top-10 overlap {ov}/10")
        robust_rows.append(dict(role=role, check=name, top10_overlap=ov, rank_corr=np.nan))

    # ---- figures ----
    t10 = ranked.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.errorbar(t10.PS, t10.player_name, xerr=[t10.PS - t10.PS_p10, t10.PS_p90 - t10.PS],
                fmt="o", color="#1f4e79", ecolor="#9ab3cf", capsize=3)
    ax.axvline(0, color="grey", lw=.8)
    what = ("runs ADDED vs an average batter in the same situations" if role == "bat"
            else "runs SAVED vs an average bowler in the same situations")
    ax.set_xlabel(f"Pressure Score: {what}, per 100 pressure balls\n"
                  f"(wickets converted to runs at pressure value, 1 wicket = {c:.1f} runs; "
                  "bars = 10th-90th pct of 500 bootstraps)")
    ax.set_title(f"Top 10 {label.lower()} under pressure (pressure overs: LI >= {LI_THRESHOLD}, own side behind)")
    fig.tight_layout(); fig.savefig(f"outputs/figures/top10_{role}.png", dpi=150); plt.close(fig)

    e = res[res.eligible]
    cut = ranked.PS.iloc[9]
    fig, ax = plt.subplots(figsize=(7.5, 6))
    sc = ax.scatter(e.PS_overall, e.PS, s=8 + e.pressure_balls / 4, c=e.clutch_delta, cmap="coolwarm_r",
                    vmin=-5, vmax=5, edgecolor="grey", lw=.3)
    ax.axhline(cut, color="#c0392b", ls="--", lw=1, label=f"Top-10 cut-off (PS of #10 = {cut:.1f})")
    lo2, hi2 = e.PS_overall.min(), e.PS_overall.max()
    ax.plot([lo2, hi2], [lo2, hi2], ":", color="grey", lw=.8, label="PS = usual level (no pressure adjustment)")
    for i, (_, r_) in enumerate(ranked.head(10).iterrows()):
        ax.annotate(r_.player_name, (r_.PS_overall, r_.PS), fontsize=7, xytext=(-6, (8, -11, 16)[i % 3]),
                    textcoords="offset points", ha="right",
                    arrowprops=dict(arrowstyle="-", lw=.4, color="grey"))
    plt.colorbar(sc, ax=ax, label="Reliable pressure adjustment (runs / 100 pressure balls)")
    ax.set_xlabel("Usual level: runs above expected per 100 balls (all balls, shrunk)")
    ax.set_ylabel("Pressure Score (final)")
    ax.set_title(f"{label.title()}: how the top 10 is selected\n(PS = usual level + reliable pressure adjustment; "
                 "point size = pressure balls)", fontsize=9)
    ax.legend(fontsize=8, loc="upper left"); fig.tight_layout()
    fig.savefig(f"outputs/figures/selection_{role}.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 7))
    ax.scatter(e.PS_overall, e.PS_raw_pressure_only, s=12, color="#b0b0b0", label="Eligible players")
    ax.scatter(ranked.head(10).PS_overall, ranked.head(10).PS_raw_pressure_only, s=34, color="#c0392b",
               label="Top 10")
    for _, r_ in ranked.head(10).iterrows():
        ax.annotate(r_.player_name, (r_.PS_overall, r_.PS_raw_pressure_only), fontsize=7,
                    xytext=(3, 3), textcoords="offset points")
    lo, hi = min(e.PS_overall.min(), e.PS_raw_pressure_only.min()), max(e.PS_overall.max(), e.PS_raw_pressure_only.max())
    ax.plot([lo, hi], [lo, hi], "--", color="grey", lw=.8, label="Diagonal y = x: pressure record equals usual level")
    ax.axhline(0, color="grey", lw=.4); ax.axvline(0, color="grey", lw=.4)
    ax.set_xlabel("Usual level: runs above expected per 100 balls (all balls, shrunk)")
    ax.set_ylabel("Under pressure: runs above expected per 100 pressure balls (raw)")
    ax.set_title(f"{label.title()}: usual level vs raw pressure record\n"
                 "Above the diagonal = did better under pressure than usual (raw, before reliability shrinkage).\n"
                 "Rank uses usual level + only the reliable part of that gap (see selection chart)", fontsize=9)
    ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(f"outputs/figures/quadrant_{role}.png", dpi=150); plt.close(fig)

rel = pd.DataFrame(rel_rows); rel.to_csv("outputs/reliability_components.csv", index=False)
pd.DataFrame(robust_rows).to_csv("outputs/robustness.csv", index=False)
pd.DataFrame(ks_rows).to_csv("outputs/shrinkage_constants.csv", index=False)

# reliability chart
show = rel[rel.metric.isin(["rae_overall", "rae_p_raw", "wae_overall", "wae_p_raw", "PS", "clutch_delta"])]
lab = {"rae_overall": "Runs, all balls", "rae_p_raw": "Runs, pressure only", "wae_overall": "Wickets, all balls",
       "wae_p_raw": "Wickets, pressure only", "PS": "Pressure Score (ours)", "clutch_delta": "Clutch delta"}
fig, ax = plt.subplots(figsize=(8, 4.5))
for i, (role, col) in enumerate([("bat", "#1f4e79"), ("bowl", "#c0392b")]):
    s = show[show.role == role].set_index("metric").reindex(list(lab))
    ax.barh(np.arange(len(lab)) + i * 0.38, s.split_half_r, height=0.36, color=col,
            label="Batters" if role == "bat" else "Bowlers")
ax.set_yticks(np.arange(len(lab)) + 0.19); ax.set_yticklabels([lab[k] for k in lab])
ax.axvline(0, color="grey", lw=.8)
ax.set_xlabel("Split-half reliability (correlation between odd- and even-numbered matches)")
ax.set_title("Which measures reflect stable skill rather than luck?")
ax.legend(); fig.tight_layout(); fig.savefig("outputs/figures/reliability.png", dpi=150)
print("\nDone.")
