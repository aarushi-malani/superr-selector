import duckdb
con = duckdb.connect("superr.duckdb", read_only=True)
show = lambda q: print(con.sql(q).df().to_string(), "\n")

# A. For winning chases that "failed": how many runs short are we?
show("""
SELECT COALESCE(NULLIF(m.revised_target,0), i1.total+1) - i2.total AS runs_short,
       COUNT(*) AS matches
FROM matches m
JOIN innings_summary i1 ON i1.match_id=m.match_id AND i1.innings=1
JOIN innings_summary i2 ON i2.match_id=m.match_id AND i2.innings=2
WHERE m.win_team_id = i2.batting_team_id
GROUP BY 1 HAVING runs_short > 0 ORDER BY 1""")

# B. For teams that won batting first: our margin vs the official margin in `result`
show("""
WITH t AS (
  SELECT m.match_id, m.result,
         TRY_CAST(regexp_extract(lower(m.result), 'by (\\d+) run', 1) AS INT) AS official_margin,
         i1.total - i2.total AS our_margin
  FROM matches m
  JOIN innings_summary i1 ON i1.match_id=m.match_id AND i1.innings=1
  JOIN innings_summary i2 ON i2.match_id=m.match_id AND i2.innings=2
  WHERE regexp_matches(lower(m.result), 'by \\d+ run') AND m.revised_target IS NULL)
SELECT our_margin - official_margin AS error, COUNT(*) AS matches
FROM t GROUP BY 1 ORDER BY 1""")

# C. Three 'failed' chases to check by hand on ESPNcricinfo
show("""
SELECT m.match_id, m.match_date, m.home_team, m.away_team, m.result,
       i1.total AS our_inn1, i2.total AS our_inn2
FROM matches m
JOIN innings_summary i1 ON i1.match_id=m.match_id AND i1.innings=1
JOIN innings_summary i2 ON i2.match_id=m.match_id AND i2.innings=2
WHERE m.win_team_id = i2.batting_team_id
  AND i2.total < i1.total + 1 AND m.revised_target IS NULL
LIMIT 3""")