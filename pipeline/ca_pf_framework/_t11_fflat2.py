#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_fflat2.py <tag> —— A1 修订版：**加强口径**，修三个已暴露的量具缺陷。

## 已暴露的三个缺陷（`R652` 记账）
1. **界面点数太少**（step 0/25 只有 22/36 点）⇒ `f_flat` 统计噪声大 ⇒ 需**点数闸门**（≥100）；
2. **多场稀释**：全带把多个场混在一起，而小场（碎片）的形状不代表板条
   ⇒ **必须给"单场"口径**；
3. **需要与解析值直接可比的口径**：仓库 §56 的 `dry_single` 是**单根孤立板条**。

## 本版做法
对**每一个场**分别算 `f_flat` / `f_tip`，然后报：
  · **最大场**（胞数最多）的读数 —— 与"主体板条"对应
  · **各场中位** —— 稳健统计
  · **加权（按界面点数）** —— 全带口径
并**只报界面点数 ≥100 的 step**（并明确标出被闸门挡掉的 step）。
"""
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
COS25 = float(np.cos(np.radians(25.0)))
MINPTS = 100


def load(tag, st):
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % st)
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        N = int(np.asarray(z['N']).ravel()[0])
        L = float(np.asarray(z['L']).ravel()[0])
        return dict(N=N, dx=L / N, idx=np.asarray(z['band_idx']),
                    val=np.asarray(z['band_val'], float),
                    fld=np.asarray(z['band_fld']),
                    a=np.asarray(z['a_ax'], float))


def one(c, k):
    """单场：返回 (f_flat, f_tip, npts)。"""
    N, dx = c['N'], c['dx']
    sel = (c['fld'] == k)
    if int(sel.sum()) < 30:
        return None
    g = np.full(N ** 3, 1e3)
    g[c['idx'][sel]] = c['val'][sel]
    iface = np.abs(g) <= 0.5 * dx
    n = int(iface.sum())
    if n < 20:
        return None
    gr = np.gradient(g.reshape(N, N, N), dx, edge_order=2)
    gn = np.sqrt(sum(x ** 2 for x in gr)) + 1e-300
    nd = np.stack([x / gn for x in gr], -1).reshape(N ** 3, 3)[iface]
    pos = np.argwhere(iface.reshape(N, N, N)).astype(float)
    na = np.abs(nd @ c['a'])
    f_flat = float((na > COS25).mean())
    pa = pos @ c['a']
    s2 = pa >= np.quantile(pa, 0.90)
    f_tip = float((na[s2] > COS25).mean()) if int(s2.sum()) >= 5 else float('nan')
    return (f_flat, f_tip, n, int((c['fld'] == k).sum()))


print("=" * 108)
print("A1（修订）：`f_flat` / `f_tip`，**逐场** + 点数闸门（界面点 ≥%d）" % MINPTS)
print("  参照: 解析长方体 f_flat≈0.146–0.172 ; 圆化后 0.004 ; 验收阈值（20Δx 后）≥0.10")
print("=" * 108)
for tag in (sys.argv[1:] or ["L0", "B40"]):
    d = os.path.join(ROOT, "dry_%s" % tag)
    if not os.path.isdir(d):
        continue
    sts = sorted(int(f[5:10]) for f in os.listdir(d) if f.startswith("snap_"))
    print("\n【%s】%d 个快照" % (tag, len(sts)))
    print("  %-7s %-8s %-24s %-24s %-20s %s"
          % ('step', '场数', '最大场 f_flat / f_tip', '各场中位 f_flat', '加权 f_flat', '总界面点'))
    for st in sts:
        c = load(tag, st)
        if c is None:
            continue
        flds = [int(v) for v in np.unique(c['fld']) if v > 0]
        r = []
        for k in flds:
            o = one(c, k)
            if o:
                r.append((k,) + o)
        if not r:
            continue
        tot = sum(x[3] for x in r)
        big = max(r, key=lambda x: x[4])          # 按该场胞数最大
        med = float(np.median([x[1] for x in r]))
        wgt = sum(x[1] * x[3] for x in r) / max(tot, 1)
        ok = '✅' if tot >= MINPTS else '⚠点数不足'
        print("  %-7d %-8d %-24s %-24s %-20s %d %s"
              % (st, len(flds),
                 '%.4f / %.4f (场%d)' % (big[1], big[2], big[0]),
                 '%.4f' % med, '%.4f' % wgt, tot, ok))
