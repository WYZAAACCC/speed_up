#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_ab_beta.py <tagA> <tagB> [...] —— 两/三臂的**厚度与速度比**并排（(3) 的 A/B）。

判据：`β_h` 越大 ⇒ 厚度越小、`v_a/v_厚` 越大（B4/B5）。
口径：基无关回转张量 `R1 ≥ R2 ≥ R3`；只用**最大连通分量**（`P22`）；
**同时报 `Vt` 以判生长阶段是否可比**（`P8`）。
"""
import csv
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _t11_shape2 import ncomp, shape_metrics  # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9


def vts(tag):
    p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
    d = {}
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            try:
                d[int(r['step'])] = float(r['Vt'])
            except (TypeError, ValueError):
                pass
    return d


def per_field(tag):
    """{step: {field: (R1,R2,R3, ncell)}}"""
    out = {}
    for sp in sorted(glob.glob(os.path.join(ROOT, "dry_%s" % tag, "snap_*.npz"))):
        with np.load(sp, allow_pickle=False) as z:
            reg = np.asarray(z['region']).astype(np.int32)
            a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
            st = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
        d = {}
        for k in sorted(int(v) for v in np.unique(reg) if v > 0):
            m = (reg == k)
            if m.sum() < 20:
                continue
            nc, lab = ncomp(m)
            if lab is not None and nc > 1:
                szs = np.bincount(lab.ravel()); szs[0] = 0
                m = (lab == int(np.argmax(szs)))
            met = shape_metrics(np.argwhere(m).astype(np.float64) * DX, a, w, nh)
            d[k] = (met['R1'], met['R2'], met['R3'], int(m.sum()),
                    met['thick_nm'], met['elong_lt'])
        out[st] = d
    return out


tags = sys.argv[1:] or ["fW0", "fB10"]
data = {t: per_field(t) for t in tags}
vt = {t: vts(t) for t in tags}
print("=" * 104)
print("(3) A/B：%s" % "  vs  ".join(tags))
print("=" * 104)
for t in tags:
    sts = sorted(data[t])
    print("\n【%s】快照 step = %s ；Vt(末) = %.4g m³"
          % (t, sts, vt[t].get(sts[-1], float('nan')) if sts else float('nan')))
    print("   %-6s %-6s %-8s %-10s %-10s %-9s %-9s %s"
          % ('step', '场', '胞数', 'R1(nm)', 'R3(nm)', '厚(nm)', 'R1/R3', 'Vt(m³)'))
    for st in sts:
        for k, v in sorted(data[t][st].items()):
            print("   %-6d %-6d %-8d %-10.0f %-10.0f %-9.0f %-9.2f %.4g"
                  % (st, k, v[3], v[0] * 1e9, v[2] * 1e9, v[4], v[5],
                     vt[t].get(st, float('nan'))))

# 速度比（用各自"首末快照"区间；并报两臂生长量以便判可比性）
print("\n" + "=" * 104)
print("速度比与厚度对比（判据 B4/B5）")
print("=" * 104)
res = {}
for t in tags:
    sts = sorted(data[t])
    if len(sts) < 2:
        continue
    s0, s1 = sts[0], sts[-1]
    ds = max(s1 - s0, 1)
    rows = []
    for k in sorted(set(data[t][s0]) & set(data[t][s1])):
        r0, r1 = data[t][s0][k], data[t][s1][k]
        va = (r1[0] - r0[0]) / ds
        vw = (r1[1] - r0[1]) / ds
        vt_ = (r1[2] - r0[2]) / ds
        rows.append((k, va, vw, vt_, r1[4]))
    res[t] = (s0, s1, rows, vt[t].get(s1, float('nan')))
    print("\n【%s】step %d→%d   Vt(末)=%.4g m³" % (t, s0, s1, res[t][3]))
    print("   %-6s %-13s %-13s %-13s %-11s %s"
          % ('场', 'v_a(nm/步)', 'v_w(nm/步)', 'v_厚(nm/步)', 'v_a/v_厚', '末态厚(nm)'))
    for k, va, vw, vt_, tk in rows:
        print("   %-6d %-13.4f %-13.4f %-13.4f %-11.2f %.0f"
              % (k, va * 1e9, vw * 1e9, vt_ * 1e9,
                 (va / vt_) if vt_ > 0 else float('nan'), tk))
if len(res) >= 2:
    ts = list(res)
    a, b = ts[0], ts[-1]
    med = {}
    for t in ts:
        vs = [r[3] for r in res[t][2] if r[3] > 0]
        med[t] = float(np.median(vs)) if vs else float('nan')
    print("\n  ⇒ **末态厚度中位**：%s"
          % "  ".join("%s = %.0f nm" % (t, float(np.median([r[4] for r in res[t][2]])))
                      for t in ts))
    print("  ⇒ **v_a/v_厚 中位**：%s"
          % "  ".join("%s = %.2f" % (t, float(np.median(
              [(r[1] / r[3]) for r in res[t][2] if r[3] > 0] or [float('nan')])))
              for t in ts))
    print("  ⚠ **可比性检查（`P8`）**：Vt(末) %s"
          % "  ".join("%s = %.4g" % (t, res[t][3]) for t in ts))
