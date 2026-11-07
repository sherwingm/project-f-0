import sys; sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd, glob
S="../fo-index-data/data/index"
b=pd.read_parquet(f"{S}/options_daily/NIFTY/2023-05.parquet"); print(b.dtypes); print(b.head(3).T)
i=pd.read_parquet(f"{S}/index_close_daily.parquet"); print(i.dtypes); print(i.head(3))
m=pd.read_parquet(f"{S}/spot_1m/NIFTY50/2023-05.parquet"); print(m.dtypes); print(m.head(3)); print(m.tail(2))
p=pd.read_parquet("expiry_research/data/panel_NIFTY.parquet"); print(p.shape); print(p.dtypes.to_string()[:3000])
