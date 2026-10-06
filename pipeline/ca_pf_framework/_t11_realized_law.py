#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_realized_law.py —— ★★★ **从实测形状反推"引擎实际兑现了哪条速度律"**。

## 判据（决定性）
Wulff 形（= 支撑函数 `h(n)` 的极集）的**长/宽比** ≈ `h(a)/h(w)`。
⇒ 若引擎兑现某条速度律，则**该场的跨度比应 ≈ 该速度律的 `h(a)/h(w)`**。

三条候选速度律（`R635`/`_t11_vn_direct.py` 算得）：
  · **设计、未凸化**：`M(a)/M(w) = 9.974`（`β_w=2.3`）
  · **引擎凸化**：     `h(a)/h(w) = 3.536`（`β_w=2.3, dip=0`）
  · **实测**：         `?`

## 用什么形状量
**跨度比**（`extent_max/extent_min`，胞坐标包围盒，**基无关**）——
与回转张量比并列报（两者口径不同，`R628 §23.3` 已记账）。
"""
import glob
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
tags = sys.argv[1:] or ["gW0", "gW1"]
print("=" * 100)
print("引擎**实际兑现**的速度律：用跨度比对照 3 条候选")
print("=" * 100)
print("  候选：设计(未凸化) **9.974** ／ 凸化 **3.536**（dip=0） ／ 凸化+凹陷 **9.854**（dip=4）")
print()
for tag in tags:
    t = tag[4:] if tag.startswith('dry_') else tag
    sns = sorted(glob.glob(os.path.join(ROOT, "dry_%s" % t, "snap_*.npz")))
    if not sns:
        print("【%s】无快照" % t)
        continue
    print("【%s】%d 个快照" % (t, len(sns)))
    print("   %-7s %-6s %-8s %-9s %-9s %-9s %-9s %s"
          % ('step', '场', '胞数', 'spanX', 'spanY', 'spanZ', '跨度比', '最接近哪条'))
    cand = (('设计9.97', 9.974), ('凸化3.54', 3.536), ('凹陷9.85', 9.854))
    for sp in sns[-3:]:
        with np.load(sp, allow_pickle=False) as z:
            reg = np.asarray(z['region']).astype(np.int32)
            st = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
        for k in sorted(int(v) for v in np.unique(reg) if v > 0)[:4]:
            idx = np.argwhere(reg == k)
            if idx.shape[0] < 20:
                continue
            ext = (idx.max(0) - idx.min(0) + 1).astype(float) * DX * 1e9
            r = ext.max() / max(ext.min(), 1e-9)
            best = min(cand, key=lambda c: abs(np.log(r / c[1])))
            print("   %-7d %-6d %-8d %-9.0f %-9.0f %-9.0f %-9.2f %s"
                  % (st, k, idx.shape[0], ext[0], ext[1], ext[2], r, best[0]))
