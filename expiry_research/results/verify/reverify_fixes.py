"""Re-verify two fixes (calendar look-ahead; final-period seal) from raw bhavcopy + the built files.

Run from C:\\Users\\sherw\\project-f-0:
  INDEX_STORE=../fo-index-data/data/index ../.venvs/fo/Scripts/python.exe expiry_research/results/verify/reverify_fixes.py
Outputs: results/verify/reverify_checks.csv, reverify_nifty_2019_window.csv, reverify_stdout.txt (via tee).
No final-period label value is read: sealed y_ columns are checked only via parquet null-count statistics.
"""
import sys, os, glob
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np, pandas as pd, pyarrow.parquet as pq

S = os.environ.get("INDEX_STORE", "../fo-index-data/data/index")
R = "expiry_research"
OUT = f"{R}/results/verify"
FINAL = "2024-07-01"
rows = []


def chk(name, ok, detail):
    rows.append(dict(check=name, ok=bool(ok), detail=str(detail)))
    print(("PASS " if ok else "FAIL ") + name + " | " + str(detail))


# ---------- raw: first trade day per expiry and listed expiries per day (bhavcopy, IDO + IDF) ----------
raw = {}
for u in ["NIFTY", "BANKNIFTY"]:
    b = pd.concat([pd.read_parquet(f, columns=["TradDt", "FinInstrmTp", "XpryDt"])
                   for f in sorted(glob.glob(f"{S}/options_daily/{u}/*.parquet"))])
    b = b[b.FinInstrmTp.isin(["IDO", "IDF"])]
    b["TradDt"] = pd.to_datetime(b.TradDt).dt.strftime("%Y-%m-%d")
    b["XpryDt"] = pd.to_datetime(b.XpryDt).dt.strftime("%Y-%m-%d")
    b = b[["TradDt", "XpryDt"]].drop_duplicates()
    first = b.groupby("XpryDt").TradDt.min()
    listed = b[b.XpryDt >= b.TradDt].groupby("TradDt").XpryDt.apply(lambda s: sorted(set(s)))
    raw[u] = (first, listed)

first_n, listed_n = raw["NIFTY"]
chk("raw NIFTY 2019-02-14 first trade day", first_n.get("2019-02-14") == "2019-02-11", first_n.get("2019-02-14"))
for d in ["2019-02-01", "2019-02-08"]:
    chk(f"raw NIFTY nearest listed expiry on {d}", listed_n[d][0] == "2019-02-28", listed_n[d][:3])

cal = pd.read_csv(f"{R}/data/expiry_calendar.csv", dtype=str)
for u in ["NIFTY", "BANKNIFTY"]:
    c = cal[(cal.underlying == u) & cal.source.str.startswith("bhavcopy", na=False)].copy()
    c["raw_first"] = c.expiry_date.map(raw[u][0])
    bad = c[c.known_from.notna() & c.raw_first.notna() & (c.known_from > c.raw_first)]
    chk(f"{u} calendar known_from <= raw first trade day (bhavcopy rows)", len(bad) == 0,
        f"{len(c)} rows, {len(bad)} with known_from later than raw first trade")
    diff = c[c.known_from.notna() & c.raw_first.notna() & (c.known_from != c.raw_first)]
    print(f"  {u}: known_from != raw first on {len(diff)} rows:", diff[["expiry_date", "known_from", "raw_first"]].values.tolist()[:10])
    nb = c[c.known_from.isna()]
    print(f"  {u}: blank known_from on bhavcopy rows: {len(nb)}", nb.expiry_date.tolist()[:10])
print("  known_from blank by source:", cal.groupby("source").known_from.apply(lambda s: f"{s.isna().sum()}/{len(s)}").to_dict())

# ---------- sessions files: every next_* pointer listed (raw) by that day ----------
sess = {}
for u in ["NIFTY", "BANKNIFTY", "SENSEX"]:
    s = pd.read_csv(f"{R}/data/sessions_{u}.csv", dtype={"date": str})
    sess[u] = s
    if u == "SENSEX":
        continue
    first, listed = raw[u]
    for col in ["next_expiry", "next_weekly", "next_monthly"]:
        m = s[col].notna()
        rf = s.loc[m, col].map(first)
        late = s.loc[m][(rf > s.loc[m, "date"]).to_numpy()]
        chk(f"{u} sessions {col}: raw-listed on the row date", len(late) == 0,
            f"{m.sum()} non-blank, {len(late)} point to an expiry first traded after the row date"
            + (f" ({late.date.min()}..{late.date.max()})" if len(late) else ""))
    # next_expiry vs nearest raw-listed expiry that day (gaps / blanks reported, not judged)
    s2 = s[s.date.isin(listed.index)].copy()
    s2["raw_nearest"] = s2.date.map(lambda d: listed[d][0])
    nb = s2[s2.next_expiry.notna()]
    dif = nb[nb.next_expiry != nb.raw_nearest]
    print(f"  {u}: next_expiry != nearest raw-listed expiry on {len(dif)} of {len(nb)} rows;",
          dif[["date", "next_expiry", "raw_nearest"]].values.tolist()[:8])
    if u == "NIFTY":
        chk("NIFTY next_expiry == nearest raw-listed, 2019-02-01..08",
            (s2[(s2.date >= "2019-02-01") & (s2.date <= "2019-02-08")].eval("next_expiry == raw_nearest")).all(), "")

sn = sess["NIFTY"]
pre = sn[sn.date < "2019-02-11"]
chk("NIFTY sessions weekly countdown blank before 2019-02-11",
    pre.next_weekly.isna().all() and pre.sessions_to_next_weekly.isna().all(),
    f"{len(pre)} rows; non-blank next_weekly {pre.next_weekly.notna().sum()}, sessions {pre.sessions_to_next_weekly.notna().sum()}")
w = sn[(sn.date >= "2019-01-28") & (sn.date <= "2019-02-15")][
    ["date", "next_expiry", "sessions_to_next_expiry", "cal_days_to_next_expiry", "next_expiry_kind",
     "next_weekly", "sessions_to_next_weekly", "next_monthly", "sessions_to_next_monthly"]]
print(w.to_string(index=False))

# ---------- panel: same-day and next-day tags ----------
pn = pd.read_parquet(f"{R}/data/panel_NIFTY.parquet")
pp = pn[pn.date < "2019-02-11"]
chk("panel NIFTY cal_sessions_to_weekly blank before 2019-02-11", pp.cal_sessions_to_weekly.isna().all(),
    f"non-null {pp.cal_sessions_to_weekly.notna().sum()} of {len(pp)}")
chk("panel NIFTY cal_next_sessions_to_weekly blank for t < 2019-02-11", pp.cal_next_sessions_to_weekly.isna().all(),
    f"non-null {pp.cal_next_sessions_to_weekly.notna().sum()} of {len(pp)}")
win = pn[(pn.date >= "2019-01-28") & (pn.date <= "2019-02-15")][
    ["date", "cal_sessions_to_expiry", "cal_days_to_expiry", "cal_upcoming_kind", "cal_sessions_to_weekly",
     "cal_next_date", "cal_next_is_expiry", "cal_next_kind", "cal_next_sessions_to_expiry",
     "cal_next_days_to_expiry", "cal_next_upcoming_kind", "cal_next_sessions_to_weekly"]]
win.to_csv(f"{OUT}/reverify_nifty_2019_window.csv", index=False)
print(win.to_string(index=False))
# cal_sessions_to_expiry on 2019-02-01..08: raw count of full sessions to 2019-02-28
for u in ["NIFTY", "BANKNIFTY"]:
    P = pd.read_parquet(f"{R}/data/panel_{u}.parquet")
    sx = sess[u].set_index("date")
    first = raw[u][0]
    # same-day tags must equal the sessions file (which is now filtered by known_from)
    j = sx.reindex(P.date)
    for pc, sc in [("cal_sessions_to_expiry", "sessions_to_next_expiry"), ("cal_sessions_to_weekly", "sessions_to_next_weekly"),
                   ("cal_sessions_to_monthly", "sessions_to_next_monthly"), ("cal_days_to_expiry", "cal_days_to_next_expiry")]:
        a = pd.to_numeric(P[pc], errors="coerce").to_numpy(dtype=float)
        b2 = pd.to_numeric(j[sc], errors="coerce").to_numpy(dtype=float)
        same = ((np.isnan(a) & np.isnan(b2)) | (a == b2)).all()
        chk(f"{u} panel {pc} == sessions {sc}", same, f"{(~((np.isnan(a) & np.isnan(b2)) | (a == b2))).sum()} differ")
    # next-day tags: the expiry t+1 points to must be raw-listed by t, else the tag is blank
    nxt = sx.reindex(P.date.shift(-1))
    for kc, cols in [("next_expiry", ["cal_next_sessions_to_expiry", "cal_next_days_to_expiry", "cal_next_upcoming_kind"]),
                     ("next_weekly", ["cal_next_sessions_to_weekly"]), ("next_monthly", ["cal_next_sessions_to_monthly"])]:
        rf = nxt[kc].map(first).to_numpy()
        late = pd.Series([isinstance(x, str) and x > t for x, t in zip(rf, P.date)], index=P.index)
        for c in cols:
            nn = P.loc[late, c].notna().sum()
            chk(f"{u} panel {c}: blank when t+1's {kc} not raw-listed by t", nn == 0,
                f"{late.sum()} such rows, {nn} non-blank")
    # is_expiry/kind of t+1 blank only when t+1 is itself an expiry first traded after t
    t1 = P.date.shift(-1)
    unk = pd.Series([isinstance(d, str) and isinstance(first.get(d), str) and first.get(d) > t
                     for d, t in zip(t1, P.date)], index=P.index)
    chk(f"{u} panel cal_next_is_expiry blank when t+1 is an expiry not listed by t",
        P.loc[unk, "cal_next_is_expiry"].isna().all(), f"{unk.sum()} such rows")

# SENSEX: known_from blank everywhere -> no filter. Report how far ahead the first stored day of each pointed expiry is
cs = cal[cal.underlying == "SENSEX"]
print("SENSEX calendar sources:", cs.source.value_counts().to_dict(), "known_from non-blank:", cs.known_from.notna().sum())

# ---------- seal ----------
for u in ["NIFTY", "BANKNIFTY", "SENSEX"]:
    O = pd.read_parquet(f"{R}/data/panel_{u}.parquet")
    sp = f"{R}/data/sealed/panel_{u}_final.parquet"
    Fid = pd.read_parquet(sp, columns=["date", "split", "y_date"])
    chk(f"{u} open: no row with date >= {FINAL}", (O.date < FINAL).all() and set(O.split) <= {"discovery", "validation"},
        f"{len(O)} rows {O.date.min()}..{O.date.max()}, splits {O.split.value_counts().to_dict()}")
    yc = [c for c in O.columns if c.startswith("y_") and c != "y_date"]
    late = O.y_date.fillna("") >= FINAL
    chk(f"{u} open: no label of a final session", O.loc[late, yc].isna().all().all(),
        f"{late.sum()} row(s) with y_date >= {FINAL}: {O.loc[late, 'date'].tolist()} -> {O.loc[late, 'y_date'].tolist()}")
    # earlier rows keep their labels (the blanking did not over-reach)
    prev = O.loc[~late].iloc[-1]
    chk(f"{u} open: row before the edge keeps labels", prev[yc].notna().sum() > 0.8 * len(yc),
        f"{prev['date']} non-null labels {prev[yc].notna().sum()}/{len(yc)}")
    chk(f"{u} schema open == sealed", list(O.columns) == pq.read_schema(sp).names, "")
    fin = Fid[Fid.split == "final"]
    chk(f"{u} sealed = final rows + edge row", (fin.date >= FINAL).all() and list(Fid[Fid.split != "final"].date) == [O.date.iloc[-1]],
        f"{len(fin)} final {fin.date.min()}..{fin.date.max()}, edge {Fid[Fid.split != 'final'].date.tolist()}")
    # union = every stored session for that underlying (sessions file from the calendar build, from first tagged day)
    allp = sorted(set(O.date) | set(fin.date))
    chk(f"{u} open + final dates disjoint and cover a contiguous session list", len(set(O.date) & set(fin.date)) == 0 and len(allp) == len(O) + len(fin),
        f"{len(O)} + {len(fin)} = {len(allp)}; sessions file {len(sess[u])} rows {sess[u].date.min()}..{sess[u].date.max()}")
    missing = sorted(set(sess[u][sess[u].date >= O.date.min()].date) - set(allp))
    print(f"  {u}: sessions-file days (from panel start) not in open+final: {len(missing)}", missing[:8])
    # sealed labels present: parquet null counts only (no values read)
    md = pq.ParquetFile(sp).metadata
    names = pq.read_schema(sp).names
    nulls = {}
    for i in range(md.num_row_groups):
        rg = md.row_group(i)
        for k in range(rg.num_columns):
            col = rg.column(k)
            nm = col.path_in_schema
            if nm.startswith("y_") and col.statistics is not None and col.statistics.has_null_count:
                nulls[nm] = nulls.get(nm, 0) + col.statistics.null_count
    print(f"  {u}: sealed rows {md.num_rows}; y_ null counts (stats only): min {min(nulls.values())} max {max(nulls.values())} of {md.num_rows}")

# no other file under data/ or results/ (outside data/sealed) carries final-period label values
hits = []
for f in glob.glob(f"{R}/data/*.csv") + glob.glob(f"{R}/results/*.csv") + glob.glob(f"{R}/results/*/*.csv"):
    try:
        d = pd.read_csv(f, nrows=200000, low_memory=False)
    except Exception as e:
        continue
    dc = [c for c in d.columns if c.lower() in ("date", "t", "day", "tradedt", "y_date")]
    lab = [c for c in d.columns if c.startswith("y_") and c != "y_date"]
    if dc and lab:
        late = pd.Series(False, index=d.index)
        for c in dc:
            late |= d[c].astype(str) >= FINAL
        n = d.loc[late, lab].notna().any(axis=1).sum()
        if n:
            hits.append((f.replace("\\", "/"), int(n)))
chk("no CSV outside data/sealed holds final-period y_ values", len(hits) == 0, hits)

pd.DataFrame(rows).to_csv(f"{OUT}/reverify_checks.csv", index=False)
print(f"{sum(r['ok'] for r in rows)} of {len(rows)} checks pass")
