import duckdb
con = duckdb.connect("superr.duckdb", read_only=True)

print(con.sql("DESCRIBE ball_by_ball"))
print(con.sql("DESCRIBE matches"))

# Day-1 decoding queries
print(con.sql("""
    SELECT extras_type, extras1_runs, extras_2_runs, runs, COUNT(*) AS n
    FROM ball_by_ball
    GROUP BY ALL ORDER BY n DESC LIMIT 40
"""))
print(con.sql("""
    SELECT dismissal_type, COUNT(*) AS n
    FROM ball_by_ball WHERE is_wicket = 1
    GROUP BY ALL ORDER BY n DESC
"""))
print(con.sql("SELECT match_format, COUNT(*) FROM competitions GROUP BY ALL"))
print(con.sql("SELECT knock_out, stage, COUNT(*) FROM matches GROUP BY ALL"))