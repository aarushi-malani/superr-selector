-- =====================================================================
-- 01_deliveries_clean.sql
-- WHAT: one clean row per delivery (super overs removed) with correct
--       run/wicket definitions and the match state BEFORE each ball.
-- WHY : every later step (win probability, pressure, credit) reads
--       the match state from this table, so it must be right.
-- DATA NOTES (verified 13-16 Nov):
--   * extras1_runs is an extras-TYPE code (6=none, 2=wide, 3=legbyes,
--     4=byes, 1=Overstep no-ball, 5=other no-ball, 7=penalty).
--   * extras_2_runs = byes run off a no-ball (values 1 or 4).
--   * The number of runs from a wide / bye / leg-bye is NOT recorded.
--     We INFER it from strike rotation: if the batters changed ends
--     (next ball's striker vs this ball's non-striker, allowing for the
--     end-of-over swap) an odd number of runs was run.
--       wide:            crossed -> 2 (wide + 1 run), else 1
--       bye / leg-bye:   crossed -> 1, else 4 (boundary is the common even case)
--     Boundary wides (5) remain undetectable.
--   * CHASE TARGETS are anchored to the official result (see bottom), so the
--     runs-needed state is exact at the end of close finishes.
--   * revised overs columns are already in BALLS (114 = 19 overs).
-- =====================================================================

CREATE OR REPLACE TABLE deliveries_clean AS
WITH base AS (
  SELECT d.*,
         COALESCE(d.extras_type, 'None') AS xt,
         m.comp_id, m.match_date, m.venue_id, m.knock_out,
         TRY_CAST(m.first_inn_revised_overs  AS INT) AS first_inn_revised_overs,
         TRY_CAST(m.second_inn_revised_overs AS INT) AS second_inn_revised_overs,
         TRY_CAST(m.revised_target           AS INT) AS revised_target,
         c.match_format, c.season AS season_label, CAST(year(m.match_date) AS INT) AS season, c.comp_name
  FROM ball_by_ball d
  JOIN matches m      USING (match_id)
  JOIN competitions c ON c.comp_id = m.comp_id
  WHERE d.innings IN (1, 2)                        -- drop super overs
),
nx AS (
  SELECT *,
    LEAD(striker_id) OVER w AS nx_striker,
    LEAD(overid)     OVER w AS nx_over
  FROM base
  WINDOW w AS (PARTITION BY match_id, innings ORDER BY innings_ball_num)
),
cr AS (
  SELECT *,
    CASE WHEN nx_striker IS NULL OR is_wicket = 1 THEN NULL
         WHEN nx_over = overid THEN nx_striker = non_striker_id      -- same over: crossed if roles swapped
         ELSE nx_striker = striker_id END AS crossed                  -- over ended: ends swap automatically
  FROM nx
),
flags AS (
  SELECT *,
    (xt = 'wide')                                  AS is_wide,
    (xt IN ('Overstep', 'other'))                  AS is_noball,
    (xt NOT IN ('wide', 'Overstep', 'other'))      AS is_legal,
    runs                                           AS batter_runs,
    CASE WHEN xt IN ('wide','Overstep','other','legbyes','byes') THEN 1
         WHEN xt = 'Penalty' THEN 5 ELSE 0 END
      + CASE WHEN xt = 'wide' AND crossed THEN 1
             WHEN xt IN ('legbyes', 'byes') AND crossed = false THEN 3 ELSE 0 END
      + COALESCE(TRY_CAST(extras_2_runs AS INT), 0)                 AS extra_runs,
    CASE WHEN xt IN ('wide','Overstep','other') THEN 1 ELSE 0 END
      + CASE WHEN xt = 'wide' AND crossed THEN 1 ELSE 0 END         AS bowler_extra_runs,
    (is_wicket = 1)                                AS team_wicket,
    (is_wicket = 1 AND dismissal_type IN
        ('Caught','Bowled','LBW','Stump','Hit Wicket')) AS bowler_wicket
  FROM cr
),
runsx AS (
  SELECT *,
    batter_runs + extra_runs        AS team_runs,
    batter_runs + bowler_extra_runs AS bowler_runs
  FROM flags
)
SELECT *,
  COALESCE(SUM(team_runs)        OVER w_prev, 0) AS score_before,
  COALESCE(SUM(team_wicket::INT) OVER w_prev, 0) AS wkts_before,
  COALESCE(SUM(is_legal::INT)    OVER w_prev, 0) AS legal_before,
  CASE WHEN innings = 1 THEN COALESCE(NULLIF(first_inn_revised_overs, 0), 120)
       ELSE COALESCE(NULLIF(second_inn_revised_overs, 0),
                     NULLIF(first_inn_revised_overs, 0), 120) END AS max_balls
FROM runsx
WINDOW w_prev AS (PARTITION BY match_id, innings ORDER BY innings_ball_num
                  ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING);

-- innings totals
CREATE OR REPLACE TABLE innings_summary AS
SELECT match_id, innings, ANY_VALUE(batting_team_id) AS batting_team_id,
       SUM(team_runs) AS total, SUM(team_wicket::INT) AS wkts, SUM(is_legal::INT) AS legal_balls
FROM deliveries_clean GROUP BY match_id, innings;

-- ---------------------------------------------------------------------
-- CHASE TARGET, anchored to the official result
--   revised (DLS) target given          -> use it
--   match went to a super over (tie)    -> chase ended level: target = chase total + 1
--   batting-first side won by R runs    -> target = chase total + R + 1
--   chasing side won but our total is   -> target = chase total (the winning ball
--     below our target                     reached it; missing extras were earlier)
--   otherwise                           -> first-innings total + 1
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE chase_target AS
WITH r AS (
  SELECT m.match_id, m.win_team_id, TRY_CAST(m.revised_target AS INT) AS rt,
         TRY_CAST(regexp_extract(lower(m.result), '(\d+)\s*run', 1) AS INT) AS run_margin,
         i1.total AS t1, i2.total AS t2, i2.batting_team_id AS bat2,
         m.match_id IN (SELECT DISTINCT match_id FROM ball_by_ball WHERE innings > 2) AS super_over
  FROM matches m
  JOIN innings_summary i1 ON i1.match_id = m.match_id AND i1.innings = 1
  LEFT JOIN innings_summary i2 ON i2.match_id = m.match_id AND i2.innings = 2)
SELECT match_id, t1 + 1 AS target_raw,
  CASE WHEN rt > 0 THEN rt
       WHEN super_over AND t2 IS NOT NULL THEN t2 + 1
       WHEN run_margin IS NOT NULL AND win_team_id <> bat2 AND t2 IS NOT NULL THEN t2 + run_margin + 1
       WHEN win_team_id = bat2 AND t2 < t1 + 1 THEN t2
       ELSE t1 + 1 END AS target,
  CASE WHEN rt > 0 THEN 'revised target'
       WHEN super_over AND t2 IS NOT NULL THEN 'tie (super over)'
       WHEN run_margin IS NOT NULL AND win_team_id <> bat2 AND t2 IS NOT NULL THEN 'official run margin'
       WHEN win_team_id = bat2 AND t2 < t1 + 1 THEN 'chase completed'
       ELSE 'first-innings total' END AS target_source
FROM r;

-- balls left, target, runs needed (second innings)
CREATE OR REPLACE TABLE deliveries_clean AS
SELECT d.*,
       d.max_balls - d.legal_before AS balls_left,
       CASE WHEN d.innings = 2 THEN ct.target END AS target,
       CASE WHEN d.innings = 2 THEN ct.target - d.score_before END AS runs_needed
FROM deliveries_clean d
LEFT JOIN chase_target ct ON ct.match_id = d.match_id;
