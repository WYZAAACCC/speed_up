#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_thick_arrest.py —— 判据：**"厚度停止"是靠能量平衡，还是靠迁移率压制？**

## 物理背景
真实马氏体板条停止增厚的机制是**能量判据**：
  `ΔG_chem − ΔG_el(t) = 0`，其中弹性能**随厚度增长**（`ΔG_el ∝ t`）
⇒ 厚度会**自动停在一个有限值**（自限制），**不需要任何"把迁移率调小"的假设**。

## 本判据怎么做（用已有产物，不需要跑新算例）
对 `dry_t5AB_B`（跑到 1120 步、已知厚度稳定在 ~150 nm）逐快照取：
  · 该场的**厚度 `t`**（回转张量口径）
  · 引擎记的**驱动 `dG`**（`series.csv` 的 `dG_max_Jm3` / `dG_p999` 等列）
  · **有效速度** `v = Δt/Δt_step`
判据：
  · 若 `dG` 随厚度**显著下降** ⇒ 停止来自**能量平衡** ✅ 物理正确；
  · 若 `dG` **基本不变**而厚度仍停 ⇒ 停止来自**迁移率压制**（`Mfac`）⇒ 是动力学假设。
"""
import glob
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _t11_shape2 import shape_metrics  # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
tag = sys.argv[1] if len(sys.argv) > 1 else "t5AB_B"
field = int(sys.argv[2]) if len(sys.argv) > 2 else 8

# ① CSV 里的驱动列
csvp = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
dG = {}
if os.path.exists(csvp):
    for r in csv.DictReader(open(csvp, encoding="utf-8")):
        try:
            dG[int(r['step'])] = dict(
                dG_max=float(r.get('dG_max_Jm3') or 'nan'),
                dG_p999=float(r.get('dG_p999') or 'nan'),
                tip=float(r.get('dG_tip') or 'nan'),
                side=float(r.get('dG_side') or 'nan'),
                wide=float(r.get('dG_wide') or 'nan'),
                ed_tip=float(r.get('ed_tip') or 'nan'),
                ed_wide=float(r.get('ed_wide') or 'nan'),
            )
        except (TypeError, ValueError):
            pass
print("CSV 驱动列可用 step 数 = %d" % len(dG))

# ② 逐快照量厚度
rows = []
for sp in sorted(glob.glob(os.path.join(ROOT, "dry_%s" % tag, "snap_*.npz"))):
    with np.load(sp, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
        st = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
    m = (reg == field)
    if m.sum() < 20:
        continue
    met = shape_metrics(np.argwhere(m).astype(np.float64) * DX, a, w, nh)
    rows.append((st, met['thick_nm'], met['elong_lt'], dG.get(st, {})))

print("=" * 100)
print("【%s】场 %d：厚度 vs 驱动（判『停止靠什么』）" % (tag, field))
print("=" * 100)
print("  %-7s %-9s %-8s %-12s %-12s %-12s %-12s"
      % ('step', '厚度(nm)', 'R1/R3', 'dG_max', 'dG_wide', 'dG_side', 'dG_tip'))
for st, tk, lt, dd in rows:
    print("  %-7d %-9.0f %-8.2f %-12.4g %-12.4g %-12.4g %-12.4g"
          % (st, tk, lt, dd.get('dG_max', float('nan')),
             dd.get('wide', float('nan')), dd.get('side', float('nan')),
             dd.get('tip', float('nan'))))
if len(rows) >= 3:
    t0, t1 = rows[0][1], rows[-1][1]
    g0 = rows[0][3].get('dG_max', float('nan'))
    g1 = rows[-1][3].get('dG_max', float('nan'))
    print("\n  ⇒ 厚度 %.0f → %.0f nm（%+.1f%%）；驱动 dG_max %.4g → %.4g（%+.1f%%）"
          % (t0, t1, 100 * (t1 - t0) / max(t0, 1e-9), g0, g1,
             100 * (g1 - g0) / max(abs(g0), 1e-30)))
    if abs(t1 - t0) / max(t0, 1e-9) < 0.10 and abs(g1 - g0) / max(abs(g0), 1e-30) < 0.10:
        print("  ⇒ ★ **厚度几乎不变、驱动也几乎不变** ⇒ 停止**不是**能量平衡造成的，")
        print("     而是**方向性迁移率压制（`Mfac`）**造成的 ⇒ **属动力学假设**。")
    elif abs(t1 - t0) / max(t0, 1e-9) < 0.10:
        print("  ⇒ 厚度几乎不变、但驱动变化明显 ⇒ 可能是能量平衡（需进一步看趋势）")
    else:
        print("  ⇒ 厚度仍在显著变化 ⇒ 未达稳态，本判据不适用")
