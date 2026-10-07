#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_fflat.py <tag> [...] —— **A1：量 `f_flat` / `f_tip`**（仓库权威口径）。

## 口径（**逐字照抄** `R30_AUDIT_LEDGER.md §56` 的"一、量具"）
从 `snap_*.npz` 的**带内稀疏 φ** 取界面点（`|φ| ≤ 0.5·Δx`），
法向 `n = ∇φ/|∇φ|`（`edge_order=2`）：
* **`f_flat`** = 全体界面点里 `|n·a| > cos25°` 的比例 —— **"平坦端面还剩多少"**
  （解析长方体应 ≈ 端面面积/总面积）
* **`f_tip`** = 沿 `a` **最靠前 10%** 的界面点里、法向在 `a` 的 25° 内的比例 ——
  **"尖端还是不是一张平面"**

## 判据（可 FAIL，先登记）
| 参照 | `f_flat` |
|---|---|
| 解析长方体（首值） | **0.146 / 0.172** |
| 圆化后（600 步） | **0.004** |
| **验收阈值**（`BLOCK_SELFAC.md:872` W-1，界面走过 20Δx 后） | **≥ 0.10** |

**预登记预期**：`L0`（`facet_proj=0`）应 ≈ **0.004–0.02**；
`B40`（`facet_proj=1`）**若保面有效**应显著更高（≥0.10 才算达标）。

## ⚠ 记账（与 §56 的差异，必须并列）
§56 的 `dry_single` 是**单根孤立板条**（只有场 1）。
`B40`/`L0` 有**多个场** ⇒ 本工具**对全部 `band_fld>0` 的胞**算（含所有变体），
并**另报"最大场"一列**以便与 §56 直接对照。
"""
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
COS25 = float(np.cos(np.radians(25.0)))
TAGS = sys.argv[1:] or ["L0", "B40"]


def load(tag, st):
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % st)
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        N = int(np.asarray(z['N']).ravel()[0])
        L = float(np.asarray(z['L']).ravel()[0])
        return dict(
            N=N, dx=L / N,
            idx=np.asarray(z['band_idx']),
            val=np.asarray(z['band_val'], float),
            fld=np.asarray(z['band_fld']),
            a=np.asarray(z['a_ax'], float),
            reg=np.asarray(z['region']).astype(np.int32))


def metrics(c, only_field=None):
    N, dx = c['N'], c['dx']
    sel = (c['fld'] > 0)
    if only_field is not None:
        sel = sel & (c['fld'] == only_field)
    if int(sel.sum()) < 30:
        return None
    # 界面点：|φ| ≤ 0.5Δx
    g = np.full(N ** 3, 1e3)
    g[c['idx'][sel]] = c['val'][sel]
    iface = np.abs(g) <= 0.5 * dx
    if int(iface.sum()) < 20:
        return None
    G = g.reshape(N, N, N)
    gr = np.gradient(G, dx, edge_order=2)
    gn = np.sqrt(sum(x ** 2 for x in gr)) + 1e-300
    nrm = np.stack([x / gn for x in gr], -1)
    nd = nrm.reshape(N ** 3, 3)[iface]
    pos = np.argwhere(iface.reshape(N, N, N)).astype(float)
    na = np.abs(nd @ c['a'])
    f_flat = float((na > COS25).mean())
    # f_tip：沿 a 最靠前 10% 的点
    pa = (pos @ c['a'])
    thr = np.quantile(pa, 0.90)
    sel2 = pa >= thr
    f_tip = float((na[sel2] > COS25).mean()) if int(sel2.sum()) >= 5 else float('nan')
    return dict(f_flat=f_flat, f_tip=f_tip, n_iface=int(iface.sum()))


print("=" * 104)
print("A1：`f_flat` / `f_tip`（口径逐字照 `R30_AUDIT_LEDGER §56`）")
print("  参照: 解析长方体 f_flat≈0.146–0.172 ; 圆化后 0.004 ; 验收阈值 ≥0.10")
print("=" * 104)
for tag in TAGS:
    d = os.path.join(ROOT, "dry_%s" % tag)
    if not os.path.isdir(d):
        print("【%s】目录不存在" % tag)
        continue
    sts = []
    for f in sorted(os.listdir(d)):
        if f.startswith("snap_"):
            sts.append(int(f[5:10]))
    sts.sort()
    print("\n【%s】%d 个快照" % (tag, len(sts)))
    print("  %-7s %-12s %-12s %-11s %-12s %s"
          % ('step', 'f_flat(全带)', 'f_tip(全带)', '界面点数', 'f_flat(最大场)', '场数'))
    for st in sts:
        c = load(tag, st)
        if c is None:
            continue
        m = metrics(c)
        if m is None:
            continue
        fl = [int(v) for v in np.unique(c['fld']) if v > 0]
        big = None
        for k in fl:
            mk = metrics(c, only_field=k)
            if mk and (big is None or mk['n_iface'] > big[1]):
                big = (mk['f_flat'], mk['n_iface'], k)
        print("  %-7d %-12.4f %-12.4f %-11d %-12s %d"
              % (st, m['f_flat'], m['f_tip'], m['n_iface'],
                 ('%.4f(场%d)' % (big[0], big[2])) if big else '—', len(fl)))
