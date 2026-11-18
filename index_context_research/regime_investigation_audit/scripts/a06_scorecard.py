import pandas as pd
t=pd.read_csv('../regime_investigation/interim/agent5_integrity/consolidated_tests.csv')
lab={'H1':'Direction (20-day return, 5 classes)','H2':'VIX level (low / normal / high)','H3':'VIX direction (falling / flat / rising)',
'H4':'Sudden VIX expansion','H5':'Opening gap (down / flat / up)','H6':'US S&P overnight (down / flat / up)',
'H7':'COMBO direction x VIX level','H8':'COMBO direction x gap','H9':'COMBO VIX level x gap',
'H10':'GIFT overnight class','H11':'GIFT vs actual open (weaker / in line / stronger)','H12':'Asia opening gaps (Nikkei, Hang Seng)',
'H11_samecontract':'GIFT vs actual open (same contract)','H10_samecontract':'GIFT overnight class (same contract)','H12_samecontract':'Asia (same contract run)',
'C1_dir3xGIFT':'COMBO direction x GIFT','C1_dir3xGIFT_samecontract':'COMBO direction x GIFT (same contract)',
'C2_VIXxGIFT':'COMBO VIX x GIFT (column version)','C2_VIXxGIFT_samecontract':'COMBO VIX x GIFT (same contract)',
'H13':'Global risk-on / risk-off','H14':'Breadth (advancers share, low / mid / high)','H15':'FII/DII cash (both buying vs diverging)',
'X01':'S&P 500 previous session','X02':'USD/INR move','X03':'Brent oil','X04':'US VIX spike (+10 %)','X05':'Dollar index','X06':'US 10-year yield',
'X07':'Sector leadership (Bank minus Nifty)','X08':'FII futures long share (level)','X09':'FII futures long share (change)','X10':'DII futures long share (level)',
'X11':'DII futures long share (change)','X12':'FII options stance (level)','X13':'FII options stance (change)','X14':'GDELT news tone','X15':'Scheduled events (RBI/Budget/FOMC/election)'}
thr={'H1':'ret20 edges -1.88 / +0.52 / +2.57 / +4.71 %; 3 groups: bearish (Q1-2), sideways (Q3), bullish (Q4-5)','H2':'VIX below 13.51 low, 13.51 to 19.94 normal, above 19.94 high',
'H3':'VIX 5-day change beyond +/-5 %','H4':'VIX at signal >= 1.10 x previous close','H5':'gap beyond +/-0.3 %','H6':'S&P move beyond +/-0.3 %',
'H7':'direction 3 x VIX 3','H8':'direction 3 x gap 3','H9':'VIX 3 x gap 3','H10':'GIFT return beyond +/-0.3 %','H11':'actual gap minus GIFT return beyond +/-0.2 pts',
'H12':'Asia gap beyond +/-0.3 %','H13':'US up and Asia not down = on; US down and Asia not up = off','H14':'advance share <= 25th / >= 75th percentile',
'X02':'USD/INR hourly change beyond +/-0.2 %','X03':'Brent beyond +/-1 %','X04':'US VIX +10 % or more','X07':'Bank minus Nifty beyond +/-0.3 pts','X01':'beyond +/-0.3 %'}
def key(h): return h.replace('_samecontract','')
out=['# Test scorecard (from `consolidated_tests.csv`, audit 18 Nov 2026)','',
'p = chance that a difference this big appears if the condition does nothing (Kruskal-Wallis across the classes). q = p after the multiple-test correction (Benjamini-Hochberg 10 %). **A test passes only if q < 0.10.** Nominal pass = p < 0.05 before correction. Lower p = better.','']
for s,name in [('G1-F','G1-F (main, 49 rows incl. 13 robustness items not in the correction)'),('G1','G1 puts'),('G1-C','G1-C calls'),('XP','XP straddle')]:
    g=t[t.strategy==s].dropna(subset=['raw_p']).sort_values('raw_p')
    f=g[g.BH_q.notna()]
    out+=[f'## {name}',f'Tests in the correction: {len(f)}. Nominal p<0.05: {(f.raw_p<0.05).sum()} (chance expects {0.05*len(f):.1f}). Passed the correction: {(f.BH_q<0.10).sum()}. Best p {f.raw_p.min():.4f} (q {f.BH_q.min():.3f}). Worst p {f.raw_p.max():.3f}.','']
    show=g if s=='G1-F' else g.head(5)
    out.append('| rank | test | what was cut | p | q | result |'); out.append('|---|---|---|---|---|---|')
    for i,(_,r) in enumerate(show.iterrows(),1):
        k=key(r.hypothesis).split(' ')[0]; l=lab.get(r.hypothesis, lab.get(k, r.definition))
        c=thr.get(k,'')
        res='robustness (outside correction)' if pd.isna(r.BH_q) else ('PASS' if r.BH_q<0.10 else ('nominal only' if r.raw_p<0.05 else 'fail'))
        out.append(f'| {i} | {r.hypothesis}: {l} | {c} | {r.raw_p:.3f} | {"" if pd.isna(r.BH_q) else f"{r.BH_q:.2f}"} | {res} |')
    out.append('')
open('TEST_SCORECARD.md','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out)[:3000])
