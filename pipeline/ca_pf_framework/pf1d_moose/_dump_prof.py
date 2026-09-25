#!/usr/bin/env python3
"""Dump one profile CSV around the phi=0.5 interface: xi(nm), c, phi."""
import io, os, re, sys
import numpy as np

H = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
d = sys.argv[1]
C0, DL, V = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
tag = "profile_line_"
fs = [f for f in os.listdir(os.path.join(H, d)) if f.startswith(tag) and f.endswith(".csv")]
f = max(fs, key=lambda s: int(re.search(r"_(\d+)\.csv$", s).group(1)))
rows = io.open(os.path.join(H, d, f), encoding="utf-8").read().strip().splitlines()
hdr = [h.strip() for h in rows[0].split(",")]
ix = {h: i for i, h in enumerate(hdr)}
a = np.array([[float(v) for v in r.split(",")] for r in rows[1:]])
a = a[np.argsort(a[:, ix["x"]])]
ref = "phi" if "phi" in ix else "gr0"
x, c, p = a[:, ix["x"]], a[:, ix["c"]], a[:, ix[ref]]
idx = np.where((p[:-1] >= 0.5) & (p[1:] < 0.5))[0]
k = int(idx[-1])
x_if = x[k] + (0.5 - p[k]) * (x[k + 1] - x[k]) / (p[k + 1] - p[k])
xi = (x - x_if) * 1e9
ld = DL / V
print("file=%s  x_if=%.4f um  (xmax=%.3f um, solid side length %.3f um)" %
      (f, x_if * 1e6, x[-1] * 1e6, x_if * 1e6))
print("%10s %14s %14s %10s" % ("xi[nm]", "c", "c_ana", "phi"))
grid = [-400, -300, -250, -200, -150, -120, -100, -80, -60, -40, -20, -10, 0,
        10, 20, 40, 60, 80, 100, 120, 150, 200, 250, 300, 400, 500]
ana_all = C0 * (1.0 + (1.0 - 0.6303) / 0.6303 * np.exp(-np.maximum(xi, 0) * 1e-9 / ld))
for g in grid:
    i = int(np.argmin(np.abs(xi - g)))
    print("%10.1f %14.6f %14.6f %10.4f" % (xi[i], c[i], ana_all[i], p[i]))
# residual of a log-linear fit in several windows
for lo, hi in [(0.5, 1.5), (0.5, 3), (1, 3), (1, 5), (2, 5)]:
    m = (xi > lo * ld * 1e9) & (xi < hi * ld * 1e9) & (c > C0)
    if m.sum() > 4:
        s = np.polyfit(xi[m] * 1e-9, np.log(np.maximum(c[m] - C0, 1e-12)), 1)[0]
        print("  fit window [%.1f,%.1f] l_D : %6.1f nm  (n=%d, %+6.1f%%)" %
              (lo, hi, -1 / s * 1e9, m.sum(), 100 * (-1 / s / ld - 1)))