"""Agent 4: sha256 prefixes (16 hex) of every input read and every output/script written. Run last: python -W ignore make_hashes.py"""
import glob, hashlib, os
R = "C:/Users/sherw/project-f-0"; RI = R + "/index_context_research/regime_investigation"; O = RI + "/interim/agent4_external"
def h(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
lines = ["# sha256 first 16 hex chars; agent 4; inputs are read-only; paths relative to repo root"]
inputs = [R + "/index_context_research/results/context_dataset.csv", R + "/scanner/s3_buy4.py", R + "/data/nse_holidays.json",
          R + "/data/parents/yf_BZ_F.csv", R + "/data/parents/yf_BZ_F_1h.csv"]
inputs += sorted(glob.glob(RI + "/external_data/*.csv")) + sorted(glob.glob(RI + "/external_data/yahoo/*.csv"))
inputs += sorted(glob.glob(R + "/g1_research/data/external/gdelt/timelinetone_*.json"))
inputs += [RI + "/PREREG_REGIME.md", RI + "/DOWNLOAD_QUALITY_CHECKS.md", RI + "/DATA_DOWNLOAD_MANIFEST.json"]
for p in inputs: lines.append(f"{h(p)}  {os.path.relpath(p, R).replace(os.sep, '/')}")
oi = sorted(glob.glob(R + "/g1_research/data/external/participant_oi/*.csv"))
lines.append(f"{hashlib.sha256(''.join(h(p) for p in oi).encode()).hexdigest()[:16]}  g1_research/data/external/participant_oi/*.csv ({len(oi)} files; hash of per-file hashes in name order); first {os.path.basename(oi[0])} {h(oi[0])}, last {os.path.basename(oi[-1])} {h(oi[-1])}")
lines.append("# outputs and scripts (this folder)")
for p in sorted(glob.glob(O + "/*")):
    if os.path.isfile(p) and os.path.basename(p) != "hashes.txt": lines.append(f"{h(p)}  {os.path.relpath(p, R).replace(os.sep, '/')}")
open(O + "/hashes.txt", "w").write("\n".join(lines) + "\n"); print(len(lines), "lines")
