#!/usr/bin/env python3
"""T1.1c -- criterion 3: planar-front steady solute profile vs analytic solution.

Analytic (frozen gradient, moving frame xi = x - x_if, no back diffusion):
    liquid : c_l(xi) = c0*[1 + (1-k)/k * exp(-V*xi/D_L)]   (xi > 0),  c_l(0) = c0/k
    solid  : c_s    = c0                                    (xi < 0)

Criteria
  (a) decay length from ln(c-c0) vs xi over [0.5,3]*l_D  ==  l_D = D_L/V   (< 5 %)
  (b) max |c - c_ana| / (c0/k - c0)  over 0 < xi < 3*l_D                  (< 10 %)
  (b2) liquid-side SPIKE: max (c - c_ana)/(c0/k - c0) over the same window (< 5 %)
       (the analytic profile decays monotonically; any excess is an artefact)
  (c) solid flatness measured in the STEADY window  -6 l_D < xi < -2 l_D   (< 1e-3)
       NB: the far solid (xi << -6 l_D) keeps the START-UP history and is
       physically allowed to differ -- that is not a defect (this was a bug
       of the first version of this script, fixed 2026-09-25).
  (d) c_l(0) vs c0/k
"""
import io
import os
import re
import sys
import numpy as np

H = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
THIN = dict(C0=0.036, K=0.6303, DL=9.5e-9, V=0.1)
PROD = dict(C0=0.036, K=0.6303, DL=1.2e-6, V=0.6)

CASES = []
for a in ["A0", "A1", "A2", "A4", "A8"]:
    CASES.append(("thin W10 %s" % a, "ak3_thin_W10_" + a, THIN))
for a in ["A0", "A0.5", "A1", "A2", "A4"]:
    CASES.append(("kcw  W10 %s" % a, "ak3_p1c_kcw_W10_" + a, THIN))
for a in ["A1", "A2", "A4"]:
    CASES.append(("kcw  W20 %s" % a, "ak3_p1c_kcw_W20_" + a, THIN))
# --- production instrument, FIXED dt = 4.1667e-8 s (2026-09-25 clean re-run) ---
for tag, d in [("PROD L150 A0 W2", "prod1d_A0_W2_kc1e-14_L150"),
               ("PROD L150 A2 W2", "prod1d_A2_W2_kc1e-14_L150"),
               ("PROD L150 A4 W2", "prod1d_A4_W2_kc1e-14_L150"),
               ("PROD L150 A2 W4", "prod1d_A2_W4_kc1e-14_L150"),
               ("PROD L150 A2 Wc", "prod1d_A2_W0.105_kc1e-14_L150"),
               ("PROD L150 A4 Wc", "prod1d_A4_W0.105_kc1e-14_L150"),
               ("PROD L150 A8 Wc", "prod1d_A8_W0.105_kc1e-14_L150"),
               ("PROD L300 A0 W2", "prod1d_A0_W2_kc1e-14_L300"),
               ("PROD L300 A2 W2", "prod1d_A2_W2_kc1e-14_L300"),
               ("PROD L300 A4 W2", "prod1d_A4_W2_kc1e-14_L300"),
               ("PROD A2 W2 dt/4", "prod1d_A2_W2_kc1e-14_L150dt4")]:
    CASES.append((tag, d, PROD))


def load(d):
    if not os.path.isdir(d):
        return None
    tag = "profile_line_"
    fs = [f for f in os.listdir(d) if f.startswith(tag) and f.endswith(".csv")]
    if not fs:
        return None
    f = max(fs, key=lambda s: int(re.search(r"_(\d+)\.csv$", s).group(1)))
    rows = io.open(os.path.join(d, f), encoding="utf-8").read().strip().splitlines()
    hdr = [h.strip() for h in rows[0].split(",")]
    ix = {h: i for i, h in enumerate(hdr)}
    a = np.array([[float(v) for v in r.split(",")] for r in rows[1:]])
    a = a[np.argsort(a[:, ix["x"]])]
    ref = "phi" if "phi" in ix else ("gr0" if "gr0" in ix else None)
    if ref is None:
        return None
    return a[:, ix["x"]], a[:, ix["c"]], a[:, ix[ref]]


def report(tag, d, P, out):
    pr = load(os.path.join(H, d))
    if pr is None:
        return
    x, c, p = pr
    P = dict(P)
    ld = P["DL"] / P["V"]
    tgt = P["C0"] / P["K"]
    amp = tgt - P["C0"]
    idx = np.where((p[:-1] >= 0.5) & (p[1:] < 0.5))[0]
    if len(idx) == 0:
        return
    k = int(idx[-1])
    x_if = x[k] + (0.5 - p[k]) * (x[k + 1] - x[k]) / (p[k + 1] - p[k])
    xi = x - x_if
    ana = P["C0"] + amp * np.exp(-np.maximum(xi, 0.0) / ld)
    m = (xi > 0.5 * ld) & (xi < 3 * ld) & (c - P["C0"] > 1e-6)
    ld_m = np.nan
    if m.sum() >= 5:
        ld_m = -1.0 / np.polyfit(xi[m], np.log(c[m] - P["C0"]), 1)[0]
    mw = (xi > 0) & (xi < 3 * ld)
    dev = np.max(np.abs(c[mw] - ana[mw])) / amp if mw.sum() > 3 else np.nan
    spike = np.max(c[mw] - ana[mw]) / amp if mw.sum() > 3 else np.nan
    ms = (xi < -2 * ld) & (xi > -6 * ld)
    flat = np.max(np.abs(c[ms] - P["C0"])) / P["C0"] if ms.sum() > 3 else np.nan
    c_int = np.interp(0.0, xi, c)
    out.append("%-18s l_D %6.1f nm(%+6.1f%%) | dev %5.1f%% | spike %+6.1f%% | "
               "solid %7.1e | c_int %.5f(%+6.2f%%)" %
               (tag, ld_m * 1e9, 100 * (ld_m / ld - 1), 100 * dev, 100 * spike,
                flat, c_int, 100 * (c_int / tgt - 1)))


if __name__ == "__main__":
    out = []
    for tag, d, P in CASES:
        report(tag, d, P, out)
    print("criteria: (a) l_D dev <5% ; (b) dev <10% ; (b2) spike <5% ; "
          "(c) solid(steady window) <1e-3 ; (d) c_int vs c0/k")
    print("")
    for l in out:
        print(l)
    with io.open(os.path.join(H, "_chk_profile3.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")