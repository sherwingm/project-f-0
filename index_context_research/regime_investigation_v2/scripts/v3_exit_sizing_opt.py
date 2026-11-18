"""G1-F excursion audit, time-stop and inverse-volatility sizing. Plan: PREREG_V3_EXIT_SIZING.md (commit 46120f9e8).
Read-only on all data and the engine. Year 2 is only touched after one candidate has been chosen on Year 1."""
import os, sys, warnings
from datetime import date, timedelta
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__)); V2 = os.path.dirname(HERE)
REPO = "C:/Users/sherw/project-f-0"
sys.path.insert(0, REPO); sys.path.insert(0, REPO + "/index_research/scripts")
from index_data import load as L  # noqa: E402
from scanner.s3_engine import ENTRY_STALE, MARK_STALE, Leg, Spec, chain_between, simulate, spot_at  # noqa: E402
from scanner.s3_buy_maxup import legs_of  # noqa: E402
import lib  # noqa: E402

AN = REPO + "/index_context_research/regime_investigation/interim/agent2_anatomy/"
OUT = os.path.join(V2, "results"); os.makedirs(OUT, exist_ok=True)
Y1_END = date(2025, 9, 30)
NS, GS = [30, 60, 120, 240], [0.0, 0.10]
days = lib.minutes("NIFTY50"); SES = sorted(days)

def load(nm, fn):
    d = pd.read_csv(AN + fn); d["day"] = pd.to_datetime(d["day"]).dt.date; d["expiry"] = pd.to_datetime(d["expiry"]).dt.date
    d["set"] = nm; return d
SETS = {"G1F": load("G1F", "anatomy_dataset.csv"), "G1": load("G1", "anatomy_dataset_G1.csv"), "G1C": load("G1C", "anatomy_dataset_G1C.csv")}
G1F_DAYS = set(SETS["G1F"].day)

def tmin(ts): return ts.hour * 60 + ts.minute - 555

def process(r, cells):
    """baseline engine result, path stats and time-stop cells for one recorded trade."""
    side = r.side; opt = side
    nxt = SES[SES.index(r.day) + 1]
    eh, em = (int(x) for x in r.entry_time.split(":"))
    spot = spot_at(r.day, eh, em, "NIFTY50")
    ch = chain_between("NIFTY", r.expiry, r.day, nxt)
    lot = L.lot_on(r.day, "NIFTY", r.expiry)
    base_spec = Spec("b", [Leg("BUY", side, 0)], entry=(eh, em), exit=(15, 29), stop=0.5)
    res = simulate(ch, spot, r.day, base_spec, lot, "NIFTY", nxt)
    if res.get("skip"): return None
    _, k, o, fi, _fo = legs_of(res["legs"])[0]
    ent = pd.Timestamp(L.at(r.day, eh, em)); t_end = pd.Timestamp(L.at(nxt, 15, 29))
    exit_t = pd.Timestamp(f"{res['exit_day']} {res['exit_at']}")
    if ent.tzinfo is not None and exit_t.tzinfo is None: exit_t = exit_t.tz_localize(ent.tzinfo)
    w = ch[(ch["timestamp"] > ent) & (ch["timestamp"] <= t_end)]
    mins = pd.DatetimeIndex(sorted(w["timestamp"].unique()))
    g = w[(w["strike"] == k) & (w["option_type"] == o)].drop_duplicates("timestamp", keep="last")
    ser = pd.Series(g["close"].to_numpy(float), index=pd.DatetimeIndex(g["timestamp"]))
    px0 = L.price_at(ch, k, o, ent, stale=ENTRY_STALE)
    val = ser.reindex(mins).ffill().fillna(px0 if px0 is not None else fi).to_numpy()
    up = (val / fi - 1) * 100
    held = mins <= exit_t
    row = dict(day=r.day, set=r.set, net_pct=res["net_pct_premium"], net_rs=res["net_rs"], reason=res["reason"], recorded_net_pct=r.net_pct,
               vix=r.vix_signal, atm_iv=r.atm_iv, mae=float(up[held].min()) if held.any() else np.nan,
               mfe=float(up[held].max()) if held.any() else np.nan)
    def tt(th):
        hit = np.where(held & (up >= th))[0]
        if not len(hit): return np.nan
        t = mins[hit[0]]
        return (tmin(t) - tmin(ent)) if t.date() == r.day else (375 - tmin(ent)) + tmin(t)
    row["t20"], row["t50"] = tt(20), tt(50)
    for N in NS:
        tgt = ent + timedelta(minutes=N)
        for gth in GS:
            key = f"T{N}_{int(gth*100)}"
            row[key + "_pct"], row[key + "_rs"], row[key + "_fired"] = row["net_pct"], row["net_rs"], 0
            if tgt.date() != r.day or tgt.hour * 60 + tgt.minute > 15 * 60 + 28 or exit_t <= tgt: continue
            i = np.searchsorted(mins.values, np.datetime64(tgt.tz_localize(None) if tgt.tzinfo is not None else tgt), side="right") - 1
            mark = val[i] if i >= 0 else px0
            if mark > fi * (1 + gth): continue
            sp = Spec("t", [Leg("BUY", side, 0)], entry=(eh, em), exit=(tgt.hour, tgt.minute), stop=0.5)
            rr = simulate(ch, spot, r.day, sp, lot, "NIFTY", r.day)
            if rr.get("skip"): continue
            row[key + "_pct"], row[key + "_rs"], row[key + "_fired"] = rr["net_pct_premium"], rr["net_rs"], 1
    return row

def metrics(pct, rs, w=None, days_span=365.0, daysidx=None):
    pct, rs = np.asarray(pct, float), np.asarray(rs, float)
    w = np.ones(len(rs)) if w is None else np.asarray(w, float)
    rsw = rs * w; n = len(rs)
    lo, hi = np.percentile(pct, [2, 98])
    wins, loss = rsw[rsw > 0].sum(), -rsw[rsw < 0].sum()
    cum = np.cumsum(rsw); dd = (cum - np.maximum.accumulate(np.maximum(cum, 0))).min()
    sd = rsw.std(ddof=1)
    return dict(trades=n, win_rate=(pct > 0).mean() * 100, mean_pct=(w * pct).sum() / w.sum(), wins_mean_pct=np.clip(pct, lo, hi).mean(),
                expectancy_rs=rsw.mean(), profit_factor=wins / loss if loss > 0 else np.nan,
                sharpe=rsw.mean() / sd * np.sqrt(n / (days_span / 365.0)) if sd > 0 else np.nan, max_dd_rs=dd, total_rs=rsw.sum())

def span(df): return max((max(df.day) - min(df.day)).days, 1)

def run_set(name, Y):
    rows = []
    for r in SETS[name][Y(SETS[name])].itertuples():
        x = process(r, None)
        if x: rows.append(x)
    return pd.DataFrame(rows).sort_values("day").reset_index(drop=True)

# ============ Stage 1: Year 1 only
is_y1 = lambda d: d.day <= Y1_END
def y1(n):
    fn = OUT + f"/v3_year1_paths_{n}.csv"
    if os.path.exists(fn):   # cache of this same script's Year-1 engine pass
        d = pd.read_csv(fn); d["day"] = pd.to_datetime(d["day"]).dt.date; return d
    d = run_set(n, is_y1); d.to_csv(fn, index=False); return d
D = {n: y1(n) for n in SETS}
F, G, C = D["G1F"], D["G1"], D["G1C"]
Gx = G[~G.day.isin(G1F_DAYS)]
print("Year 1 trades: G1-F %d, G1 %d (outside G1-F %d), G1-C %d" % (len(F), len(G), len(Gx), len(C)))
print("engine vs recorded net pct on G1-F Year 1: max abs diff %.2f points" % (F.net_pct - F.recorded_net_pct).abs().max())

# ---- Step 1 audit (G1-F Year 1)
print("\n=== STEP 1: Year-1 audit, G1-F (descriptive) ===")
win, los = F[F.net_pct > 0], F[F.net_pct <= 0]
q = lambda s: " ".join(f"p{p}={np.percentile(s, p):.0f}" for p in (10, 25, 50, 75, 90))
print(f"winners {len(win)}, losers {len(los)} (stops {int((F.reason=='stop').sum())})")
print("MAE %  winners:", q(win.mae), "| losers:", q(los.mae))
Lv = np.percentile(win.mae, 10)
print(f"MAE level sparing >=90% of winners: {Lv:.1f} %  -> catches {(los.mae <= Lv).mean()*100:.0f}% of losers, {(win.mae <= Lv).mean()*100:.0f}% of winners "
      f"(note: the live 50% stop on the bid already acts near -50% on the option; this is descriptive, tighter stops are not tested)")
F["giveback"] = F.mfe - F.net_pct
print("MFE %  winners:", q(win.mfe), "| losers:", q(los.mfe))
gw, gl = F[F.net_pct > 0].giveback, F[F.net_pct <= 0].giveback
print(f"giveback (peak minus realised net, points): winners median {gw.median():.0f}, mean {gw.mean():.0f}; losers median {gl.median():.0f}, mean {gl.mean():.0f}")
print("peak above +50%%: %.0f%% of trades; above +100%%: %.0f%%; of those at +100%%, realised median %.0f%%" % ((F.mfe >= 50).mean() * 100, (F.mfe >= 100).mean() * 100, F[F.mfe >= 100].net_pct.median()))
for th in ("t20", "t50"):
    a, b = win[th], los[th]
    print(f"minutes to first {th[1:]}% unrealised: winners reached {a.notna().mean()*100:.0f}% (median {a.median():.0f} min), losers reached {b.notna().mean()*100:.0f}% (median {b.median():.0f} min)")

# ---- Step 2: grid, Year 1
def row_for(df, label, pct, rs, w=None):
    m = metrics(pct, rs, w, span(df)); m["cell"] = label; return m
def tabs(df, cell=None, w=None):
    if cell is None: return metrics(df.net_pct, df.net_rs, w, span(df))
    return metrics(df[cell + "_pct"], df[cell + "_rs"], w, span(df))
medIV = round(F.atm_iv.median()); print(f"\nYear-1 median ATM IV (G1-F) {F.atm_iv.median():.2f} -> IV reference {medIV}")
def mult(df, kind, R):
    x = df.vix if kind == "vix" else df.atm_iv
    return np.clip(R / x, 0.5, 1.5).fillna(1.0).to_numpy()
cells = [("base", None, None)] + [(f"T{N}_{int(g*100)}", f"T{N}_{int(g*100)}", None) for N in NS for g in GS] + \
        [("S_vix13", None, ("vix", 13)), ("S_vix15", None, ("vix", 15)), (f"S_iv{medIV}", None, ("iv", medIV))]
def eval_cell(df, tcell, s):
    w = mult(df, *s) if s else None
    return tabs(df, tcell, w)
res = []
for lab, tc, s in cells:
    for nm, df in (("G1-F", F), ("G1 outside G1-F", Gx), ("G1 pooled", G), ("G1-C (info)", C)):
        m = eval_cell(df, tc, s); m.update(cell=lab, set=nm); res.append(m)
R = pd.DataFrame(res); R.to_csv(OUT + "/v3_year1_grid.csv", index=False)
pd.set_option("display.width", 250, "display.max_columns", 30)
for nm in ("G1-F", "G1 outside G1-F"):
    print(f"\n--- Year-1 grid, {nm} ---")
    print(R[R.set == nm][["cell", "trades", "win_rate", "mean_pct", "wins_mean_pct", "expectancy_rs", "profit_factor", "sharpe", "max_dd_rs", "total_rs"]].round(2).to_string(index=False))
fired = {c: int(F[c + "_fired"].sum()) for _, c, _ in cells if c}
print("\ntime-stop fired on (G1-F Year 1):", fired)

# ---- selection (pre-registered gate)
def get(nm, c): return R[(R.set == nm) & (R.cell == c)].iloc[0]
passers = []
for lab, tc, s in cells[1:]:
    ok = True
    for nm in ("G1-F", "G1 outside G1-F"):
        b, c = get(nm, "base"), get(nm, lab)
        ok &= (c.sharpe > b.sharpe) and (c.profit_factor > b.profit_factor) and (c.mean_pct >= b.mean_pct - 1e-9)
    if ok: passers.append(lab)
print("\nPASSERS of the Year-1 gate (Sharpe and PF up on G1-F and on G1 outside G1-F, mean not lower):", passers or "none")
chosen = None
if passers:
    order = lambda l: (0 if l.startswith("S_") else 1, -(get("G1-F", l).sharpe - get("G1-F", "base").sharpe))
    chosen = sorted(passers, key=order)[0]; print("CHOSEN (fewest parameters, then largest G1-F Sharpe gain):", chosen)

# ---- Stage 2: Year 2 once
if not chosen:
    print("\nNo candidate passed on Year 1: Year 2 NOT opened.")
else:
    print("\n=== STAGE 2: Year 2 opened once for", chosen, "===")
    is_y2 = lambda d: d.day > Y1_END
    D2 = {n: run_set(n, is_y2) for n in ("G1F", "G1")}
    cell = next(c for c in cells if c[0] == chosen)
    out = []
    for yr, FF, GG in (("Year 1", F, G), ("Year 2", D2["G1F"], D2["G1"])):
        GGx = GG[~GG.day.isin(G1F_DAYS)]
        for nm, df in (("G1-F", FF), ("G1 outside G1-F", GGx)):
            for lab, tc, s in (cells[0], cell):
                m = eval_cell(df, tc, s); m.update(year=yr, set=nm, rule="Baseline" if lab == "base" else "Optimized: " + lab); out.append(m)
    O = pd.DataFrame(out); O.to_csv(OUT + "/v3_selected_comparison.csv", index=False)
    print(O[["year", "set", "rule", "trades", "win_rate", "mean_pct", "wins_mean_pct", "profit_factor", "sharpe", "max_dd_rs", "total_rs"]].round(2).to_string(index=False))
