#!/usr/bin/env python3
"""Per-case profile statistics: where is the solute spike / how flat is the solid."""
import io, os, re
import numpy as np

H = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
CASES = [
    ("kcw W10 A2", "ak3_p1c_kcw_W10_A2", 0.036, 9.5e-9, 0.1),
    ("thin W10 A0", "ak3_thin_W10_A0", 0.036, 9.5e-9, 0.1),
    ("thin W10 A8", "ak3_thin_W10_A8", 0.036, 9.5e-9, 0.1),
    ("PROD A0", "prod1d_A0_W2_kc1e-14", 0.036, 1.2e-6, 0.6),
    ("PROD A2", "prod1d_A2_W2_kc1e-14", 0.036, 1.2e-6, 0.6),
]


def stats(tag, d, C0, DL, V):
    dd = os.path.join(H, d)
    fs = [f for f in os.listdir(dd) if f.startswith("profile_line_") and f.endswith(".csv")] \
        if os.path.isdir(dd) else []
    if not fs:
        print("%-12s  (no profile csv)" % tag); return
    f = max(fs, key=lambda s: int(re.search(r"_(\d+)\.csv$", s).group(1)))
    rows = io.open(os.path.join(dd, f), encoding="utf-8").read().strip().splitlines()
    hdr = [h.strip() for h in rows[0].split(",")]
    ix = {h: i for i, h in enumerate(hdr)}
    a = np.array([[float(v) for v in r.split(",")] for r in rows[1:]])
    a = a[np.argsort(a[:, ix["x"]])]
    ref = "phi" if "phi" in ix else "gr0"
    x, c, p = a[:, ix["x"]], a[:, ix["c"]], a[:, ix[ref]]
    idx = np.where((p[:-1] >= 0.5) & (p[1:] < 0.5))[0]
    k = int(idx[-1])
    x_if = x[k] + (0.5 - p[k]) * (x[k + 1] - x[k]) / (p[k + 1] - p[k])
    xi = (x - x_if) * 1e9          # nm
    ld = DL / V * 1e9              # nm
    print("== %s  (%s)  dx=%.2f nm  l_D=%.0f nm  x_if=%.3f um  xmax=%.3f um" %
          (tag, f, (x[1] - x[0]) * 1e9, ld, x_if * 1e6, x[-1] * 1e6))
    ms = xi < -2.0 * ld
    if ms.sum() > 3:
        j = int(np.argmax(np.abs(c[ms] - C0)))
        print("   solid (xi<%.0f nm): c in [%.6f, %.6f]  worst=%.6f at xi=%.1f nm  -> dev %.3f"
              % (-2 * ld, c[ms].min(), c[ms].max(), c[ms][j], xi[ms][j],
                 abs(c[ms][j] - C0) / C0))
    m = np.abs(xi) < 3 * ld
    j = int(np.argmax(c[m]))
    print("   near-iface |xi|<%.0f nm: peak c=%.6f at xi=%+.1f nm (c0/k=%.5f, ratio %.2f)"
          % (3 * ld, c[m].max(), xi[m][j], C0 / 0.6303, c[m].max() / (C0 / 0.6303)))
    print("   c(xi) at +5/+10/+20/+50/+100 nm: " +
          " ".join("%.5f" % np.interp(g, xi, c) for g in [5, 10, 20, 50, 100]))


for t in CASES:
    stats(*t)