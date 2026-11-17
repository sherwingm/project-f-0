import pandas as pd
pd.set_option("display.width",250); pd.set_option("display.max_columns",30); pd.set_option("display.max_rows",500)
print(pd.read_csv("gift_vs_actual_descriptive.csv").round(3).to_string())
print(pd.read_csv("gift_triple_status.csv").drop(columns="cell_counts"))
t=pd.read_csv("gift_tests.csv")
print(t[(t.section=="explanatory_all")].round(3).to_string())
