import io, os, re
import numpy as np
H = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
d = os.path.join(H, "ak3_p1c_kcw_W10_A2")
tag = "profile_line_"
fs = [f for f in os.listdir(d) if f.startswith(tag) and f.endswith(".csv")]
print("n files:", len(fs), sorted(fs, key=lambda s: int(re.search(r"_(\d+)\.csv$", s).group(1)))[-3:])
f = max(fs, key=lambda s: int(re.search(r"_(\d+)\.csv$", s).group(1)))
print("picked", f)
rows = io.open(os.path.join(d, f), encoding="utf-8").read().strip().splitlines()
hdr = [h.strip() for h in rows[0].split(",")]
ix = {h: i for i, h in enumerate(hdr)}
a = np.array([[float(v) for v in r.split(",")] for r in rows[1:]])
a = a[np.argsort(a[:, ix["x"]])]
x, c, p = a[:, ix["x"]], a[:, ix["c"]], a[:, ix["phi"]]
idx = np.where((p[:-1] >= 0.5) & (p[1:] < 0.5))[0]
print("n crossings:", len(idx), "first idx", idx[:3], "last", idx[-3:] if len(idx) else None)