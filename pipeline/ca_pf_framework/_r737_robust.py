#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r737_robust.py <root> <tag> ... —— **形状量具的鲁棒性对照**（判 `J-8b` 的量具是否可信）。

## 问题
`J-8b` 用 **`PCA-max`**（"逐场算主轴比，取最大"）。但两臂的**场集合不同**
（形核/合并事件不同）⇒ `max` 可能**由一个偶然的大场决定** ⇒ 不是稳定的形状指标。

## 四个候选口径（同一次快照上并排）
| # | 口径 | 定义 |
|---|---|---|
| **A** | `PCA-max`（`J-8b` 现在用的） | 逐场 `sp0/sp2`，取**最大** |
| **B** | `PCA-体积加权` | 逐场按体胞数加权平均 |
| **C** | `PCA-主分量` | **只取最大场**（体胞最多者）的 `sp0/sp2` |
| **D** | `PCA-全体胞` | 把**所有场**的体胞**并起来**算一次主轴比 |

## 判据（**先登记，可 FAIL**）
**R-1**：四个口径给出的**两臂差异方向一致** ⇒ 该结论对口径稳健。
**R-2**：若四个口径方向不一致 ⇒ **`J-8b` 的结论不可信**，须换口径或换指标。
"""
import csv
import os
import sys

import numpy as np


def per_field(sp):
    with np.load(sp, allow_pickle=False) as z:
        N = int(np.asarray(z['N']).ravel()[0])
        L = float(np.asarray(z['L']).ravel()[0])
        dx = L / N
        ii = (np.arange(N) + 0.5) * dx
        P = np.stack(np.meshgrid(ii, ii, ii, indexing='ij'), -1).reshape(-1, 3)
        idx = np.asarray(z['band_idx']); val = np.asarray(z['band_val'], float)
        fld = np.asarray(z['band_fld'])
    out = []
    for k in sorted(int(v) for v in np.unique(fld) if v > 0):
        m = (fld == k)
        g = np.full(N ** 3, 1e3)
        g[idx[m]] = val[m]
        body = g < 0
        nb = int(body.sum())
        if nb < 200:
            continue
        pts = P[body]
        cen = pts - pts.mean(0)
        _, V = np.linalg.eigh(cen.T @ cen / max(len(cen), 1))
        pr = cen @ V
        s = np.sort(pr.max(0) - pr.min(0))[::-1]
        out.append((k, nb, float(s[0] / max(s[2], 1e-30)), pts))
    return out


def main():
    root = sys.argv[1]
    tags = sys.argv[2:]
    steps = [50, 75, 100, 125, 150, 175]
    print('=' * 104)
    print('形状量具鲁棒性对照（root=%s）' % root)
    print('=' * 104)
    tab = {}
    for t in tags:
        d = os.path.join(root, 'dry_%s' % t)
        sp0 = os.path.join(d, 'series.csv')
        if not os.path.isfile(sp0):
            print('⚠ 缺 %s' % sp0)
            continue
        with open(sp0, newline='') as f:
            S = {int(r['step']): r for r in csv.DictReader(f) if r.get('step')}
        for st in steps:
            sn = os.path.join(d, 'snap_%05d.npz' % st)
            if not os.path.exists(sn) or str(S.get(st, {}).get('box_touch', '?')) != '0':
                continue
            pf = per_field(sn)
            if not pf:
                continue
            A = max(p[2] for p in pf)
            wsum = sum(p[1] for p in pf)
            B = sum(p[2] * p[1] for p in pf) / max(wsum, 1)
            C = max(pf, key=lambda p: p[1])[2]
            allpts = np.concatenate([p[3] for p in pf])
            cen = allpts - allpts.mean(0)
            _, V = np.linalg.eigh(cen.T @ cen / max(len(cen), 1))
            pr = cen @ V
            s = np.sort(pr.max(0) - pr.min(0))[::-1]
            D = float(s[0] / max(s[2], 1e-30))
            tab[(t, st)] = dict(A=A, B=B, C=C, D=D, n=len(pf))
    print('  %-8s %5s %5s %10s %10s %10s %10s'
          % ('臂', 'step', '场数', 'A:PCA-max', 'B:体积加权', 'C:主分量', 'D:全体胞'))
    for (t, st), v in sorted(tab.items()):
        print('  %-8s %5d %5d %10.3f %10.3f %10.3f %10.3f'
              % (t, st, v['n'], v['A'], v['B'], v['C'], v['D']))
    print()
    # 逐口径判方向
    print('  ## 两臂差异方向（开 / 关 − 1）：')
    print('  %-6s %10s %10s %10s %10s   %s'
          % ('step', 'A', 'B', 'C', 'D', '四口径方向一致?'))
    for st in steps:
        keys = [k for k in tab if k[1] == st]
        if len(keys) < 2:
            continue
        a = tab[(tags[0], st)] if (tags[0], st) in tab else None
        b = tab[(tags[1], st)] if (tags[1], st) in tab else None
        if a is None or b is None:
            continue
        ds = [(b[k] / a[k] - 1) * 100 for k in 'ABCD']
        same = all(d > 0 for d in ds) or all(d < 0 for d in ds)
        print('  %-6d %9.1f%% %9.1f%% %9.1f%% %9.1f%%   %s'
              % (st, ds[0], ds[1], ds[2], ds[3], '✅ 一致' if same else '⛔ **不一致**'))
    print()
    print('  ⇒ R-2：若某些步四口径方向不一致 ⇒ **`J-8b` 的单点 PCA-max 结论不可信**')
    return 0


if __name__ == '__main__':
    sys.exit(main())
