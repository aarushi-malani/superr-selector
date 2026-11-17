import duckdb
con = duckdb.connect("superr.duckdb")
con.execute(open("sql/01_deliveries_clean.sql").read())
print(con.sql("SELECT COUNT(*) rows, MAX(max_balls) max_balls FROM deliveries_clean"))