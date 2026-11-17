import duckdb

con = duckdb.connect("superr.duckdb")   # creates the database file

tables = ["competitions", "matches", "teams",
          "competition_team_player_mapping", "playing_eleven", "ball_by_ball"]

for t in tables:
    con.execute(f"""
        CREATE OR REPLACE TABLE {t} AS
        SELECT * FROM read_csv('data/raw/{t}.csv',
                               header = true,
                               sample_size = -1)   -- scan the whole file before choosing types
    """)
    n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"{t:35s} {n:>8,} rows")

con.close()