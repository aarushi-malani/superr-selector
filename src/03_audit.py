import duckdb
con = duckdb.connect("superr.duckdb", read_only=True)
show = lambda q: print(con.sql(q).df().to_string(), "\n")

# full extras table (no truncation)
show("""SELECT extras_type, extras1_runs, extras_2_runs, runs, COUNT(*) n
        FROM ball_by_ball GROUP BY ALL ORDER BY extras_type, n DESC""")

# the 7 domestic competitions
show("SELECT comp_id, comp_name, season FROM competitions WHERE match_format='T20'")

# what result strings look like
show("SELECT result, COUNT(*) n FROM matches GROUP BY ALL ORDER BY n DESC LIMIT 15")

# revised overs / targets in use
show("""SELECT first_inn_revised_overs, second_inn_revised_overs,
        revised_target IS NOT NULL AS has_rev_target, COUNT(*) n
        FROM matches GROUP BY ALL ORDER BY n DESC""")

# ordering: is innings_ball_num unique within an innings? where does overid start?
show("""SELECT COUNT(*) AS dup_rows FROM (
          SELECT match_id, innings, innings_ball_num, COUNT(*) c
          FROM ball_by_ball GROUP BY ALL HAVING c > 1)""")
show("SELECT MIN(overid) min_over, MAX(overid) max_over FROM ball_by_ball WHERE innings <= 2")
show("SELECT innings, COUNT(DISTINCT match_id) matches FROM ball_by_ball GROUP BY 1 ORDER BY 1")