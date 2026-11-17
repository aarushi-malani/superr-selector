"""
01_load_and_clean.py
WHAT: loads the 6 CSVs into superr.duckdb and builds deliveries_clean + innings_summary.
RUN : python src/01_load_and_clean.py            (CSVs must be in data/raw/)
"""
import duckdb, sys

RAW = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
con = duckdb.connect("superr.duckdb")

for t in ["competitions", "matches", "teams", "competition_team_player_mapping",
          "playing_eleven", "ball_by_ball"]:
    con.execute(f"CREATE OR REPLACE TABLE {t} AS SELECT * FROM "
                f"read_csv('{RAW}/{t}.csv', header=true, sample_size=-1)")
    print(f"{t:35s}{con.sql(f'SELECT COUNT(*) FROM {t}').fetchall()[0][0]:>9,} rows")

con.execute(open("sql/01_deliveries_clean.sql").read())
print(con.sql("SELECT COUNT(*) AS clean_rows, MAX(max_balls) AS max_balls, "
              "MIN(balls_left) AS min_balls_left FROM deliveries_clean"))
