import pandas as pd
pd.set_option('display.width',250,'display.max_columns',30,'display.max_rows',500)
T=pd.read_csv('regime_tests.csv')
print(T[T.section=='explanatory_all'][['strategy','hypothesis','kw_p','n_cells_ge10','welch_pair','welch_diff_pct','welch_p','bh10_survives']].round(3))
print(T[(T.section=='discovery_to_2025-09-30')&T.bh10_survives])
print(T[(T.section=='explanatory_all')&T.bh10_survives])
print(pd.read_csv('triple_status.csv'))
