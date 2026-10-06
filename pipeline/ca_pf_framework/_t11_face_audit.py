#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_face_audit.py <tag> —— **对账**：我的量具数出的三档胞数 vs 引擎 CSV 的 `n_tip/n_side/n_wide`。

## 为什么要对账
`R637` 的量具给出 `wide` 档只有 **51 胞**（step 300），而引擎自己每步都在 CSV 里写
`n_tip`/`n_side`/`n_wide`（`windowB_surface.py:5085-5086` 算的）。
两者若差很多 ⇒ **我的量具有问题**（如 `band_val` 的索引还原错了）；
若一致 ⇒ **"几乎没有平坦面"这个结论成立**。
"""
import csv
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
tag = sys.argv[1] if len(sys.argv) > 1 else "kW1"
tag = tag[4:] if tag.startswith('dry_') else tag

# ---- 引擎 CSV ----
p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
rows = list(csv.DictReader(open(p, encoding="utf-8")))
print("=" * 92)
print("【%s】引擎 CSV 的档胞数（`n_tip`/`n_side`/`n_wide`/`n_obl`）" % tag)
print("=" * 92)
print("  %-7s %-8s %-8s %-8s %-8s %s"
      % ('step', 'n_tip', 'n_side', 'n_wide', 'n_obl', '斜向占比'))
for r in rows:
    try:
        t = int(r['n_tip']); s = int(r['n_side'])
        w = int(r['n_wide']); o = int(r['n_obl'])
    except (KeyError, ValueError):
        continue
    tot = t + s + w + o
    print("  %-7s %-8d %-8d %-8d %-8d %.1f%%"
          % (r['step'], t, s, w, o, 100.0 * o / max(tot, 1)))

# ---- 我的量具（同一 step 复算）----
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
from _t11_vface2 import load, faces_and_pos   # noqa: E402

print()
print("=" * 92)
print("【%s】我的量具（引擎 `φ`，带 `|φ|<=1.5dx`，阈值 0.81）" % tag)
print("=" * 92)
print("  %-7s %-8s %-8s %-8s %-8s %s"
      % ('step', 'tip', 'side', 'wide', 'obl', '斜向占比'))
for sp in sorted(os.listdir(os.path.join(ROOT, "dry_%s" % tag))):
    if not sp.startswith("snap_"):
        continue
    with np.load(os.path.join(ROOT, "dry_%s" % tag, sp), allow_pickle=False) as z:
        st = int(np.asarray(z['step']).ravel()[0])
    if st not in (25, 100, 200, 300):
        continue
    C = load(tag, st)
    if C is None:
        continue
    f, c2, obl, tot = faces_and_pos(None, C, st)
    nt, ns, nw = int(f['tip'].sum()), int(f['side'].sum()), int(f['wide'].sum())
    no = int(obl.sum())
    print("  %-7d %-8d %-8d %-8d %-8d %.1f%%"
          % (st, nt, ns, nw, no, 100.0 * no / max(nt + ns + nw + no, 1)))
