#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_growth_rate.py <tag> —— **长厚比的增长率 vs 尺度**（判"若盒子足够大，能否到 9"）。

## 论证（为什么这个量能替代"跑更大盒"）
"撞盒"发生在**形状长到 ~0.9·L** 时。若长厚比 `Λ` 随 `Vt` 单调增长（无饱和迹象），
则 **更大盒 ⇒ 更大 `Vt` ⇒ 更大 `Λ`**，可用**现有 4 µm 数据外推**。
⇒ 判据：`Λ` vs `Vt` 在有效区间内是否**单调**且**未见饱和**。

## 做法
对 `box_touch=0` 的 step，取该场**最大连通分量**的 `Λ = R1/R3`，
按 `Vt` 排序，报逐点值与**局部斜率** `dΛ/dVt`。
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
from _t11_shape2 import ncomp, shape_metrics  # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
tags = sys.argv[1:] or ["L1"]

for tag in tags:
    t = tag[4:] if tag.startswith('dry_') else tag
    d = os.path.join(ROOT, "dry_%s" % t)
    p = os.path.join(d, "series.csv")
    if not os.path.exists(p):
        print("【%s】无 CSV" % t)
        continue
    vt, touch = {}, {}
    for r in csv.DictReader(open(p, encoding="utf-8")):
        try:
            st = int(r['step'])
            vt[st] = float(r['Vt'])
            touch[st] = int(r.get('box_touch') or 0)
        except (KeyError, ValueError):
            pass
    rows = []
    for f in sorted(os.listdir(d)):
        if not f.startswith("snap_"):
            continue
        with np.load(os.path.join(d, f), allow_pickle=False) as z:
            st = int(np.asarray(z['step']).ravel()[0])
            reg = np.asarray(z['region']).astype(np.int32)
            a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
        if touch.get(st, 0):
            continue                     # **只用未撞盒的 step**
        nc, lab = ncomp(reg > 0)
        if lab is None:
            continue
        s = np.bincount(lab.ravel()); s[0] = 0
        m = (lab == int(np.argmax(s)))
        if m.sum() < 50:
            continue
        met = shape_metrics(np.argwhere(m).astype(np.float64) * DX, a, w, nh)
        rows.append((st, vt.get(st, np.nan), met['elong_lt'], int(m.sum())))
    print("=" * 96)
    print("【%s】长厚比 vs `Vt`（**只用 `box_touch=0` 的 step**）" % t)
    print("=" * 96)
    print("  %-7s %-13s %-10s %-9s %s" % ('step', 'Vt(m³)', '胞数', 'Λ=R1/R3', 'dΛ/dVt(×1e18)'))
    prev = None
    for st, v, lam, n in rows:
        sl = ''
        if prev and np.isfinite(v) and np.isfinite(prev[1]) and v > prev[1]:
            sl = '%.2f' % ((lam - prev[2]) / ((v - prev[1]) * 1e18))
        print("  %-7d %-13.4g %-10d %-9.2f %s" % (st, v, n, lam, sl))
        prev = (st, v, lam)
    if rows:
        print("\n  ⇒ 末点：step %d  `Vt`=%.4g  **Λ=%.2f**（胞数 %d）"
              % (rows[-1][0], rows[-1][1], rows[-1][2], rows[-1][3]))
        lams = [r[2] for r in rows]
        print("  ⇒ Λ 序列是否单调：%s" % ('✅ 单调' if all(
            lams[i] <= lams[i + 1] for i in range(len(lams) - 1)) else '⚠ 有回落'))
