#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r720_fflat_time.py <root> <tag> [tag ...] —— 逐快照算 `f_flat`（**只读**）。

## 口径（`R30 §56` 原文，与 `_b2_meas.py` 一致）
* `f_flat` = **全体场**的界面胞里 `|n·a| > cos25°` 的占比；
* 界面带 = `|phi| ≤ 0.5·dx`；`n` = `np.gradient(phi, edge_order=2)` 的单位向量；
* 只统计**体胞 ≥ 50** 的场（与 `_b2_meas.py` 同）。

## 为什么单独写它
`_b2_meas.py` 一次只跑一个快照；要判"保面机制是**保持**还是**先高后衰**"必须看时间线。
⚠ 本脚本**不判盒**（盒用 `_r720_touch.py` 另判）—— 两个量必须并读。
"""
import os
import sys

import numpy as np

COS25 = float(np.cos(np.radians(25.0)))


def main():
    root, tags = sys.argv[1], sys.argv[2:]
    print('=' * 96)
    print('`f_flat` 时间线（root=%s）  判据：≥ 0.10' % root)
    print('=' * 96)
    for tag in tags:
        d = os.path.join(root, 'dry_%s' % tag)
        snaps = sorted(f for f in os.listdir(d) if f.startswith('snap_')) \
            if os.path.isdir(d) else []
        if not snaps:
            print('【%s】⚠ 无快照' % tag)
            continue
        print('\n【%s】%d 个快照' % (tag, len(snaps)))
        print('   %-8s %8s %9s %10s %10s' % ('step', '场数', '界面点', 'f_flat', 'PCA最大'))
        for sn in snaps:
            with np.load(os.path.join(d, sn), allow_pickle=False) as z:
                N = int(np.asarray(z['N']).ravel()[0])
                L = float(np.asarray(z['L']).ravel()[0])
                dx = L / N
                ii = (np.arange(N) + 0.5) * dx
                P = np.stack(np.meshgrid(ii, ii, ii, indexing='ij'), -1).reshape(-1, 3)
                idx = np.asarray(z['band_idx']); val = np.asarray(z['band_val'], float)
                fld = np.asarray(z['band_fld'])
                a_ax = np.asarray(z['a_ax'], float)
            fl = [int(v) for v in np.unique(fld) if v > 0]
            nd, nif, mx = [], 0, 0.0
            for k in fl:
                m = (fld == k)
                g = np.full(N ** 3, 1e3)
                g[idx[m]] = val[m]
                nb = int((g < 0).sum())
                if nb < 200:
                    continue
                gr = np.gradient(g.reshape(N, N, N), dx, edge_order=2)
                gn = np.sqrt(sum(x ** 2 for x in gr)) + 1e-300
                iface = (np.abs(g) <= 0.5 * dx).reshape(N ** 3)
                ni = int(iface.sum())
                if ni < 50:
                    continue
                _n = np.stack([x / gn for x in gr], -1).reshape(N ** 3, 3)[iface]
                nd.append(_n); nif += ni
                pts = P[g < 0]
                cen = pts - pts.mean(0)
                _, V = np.linalg.eigh(cen.T @ cen / max(len(cen), 1))
                pr = cen @ V
                sp = np.sort(pr.max(0) - pr.min(0))[::-1]
                mx = max(mx, float(sp[0] / max(sp[2], 1e-30)))
            ff = (float((np.abs(np.concatenate(nd) @ a_ax) > COS25).mean())
                  if nd else float('nan'))
            step = int(sn.split('_')[1].split('.')[0])
            print('   %-8d %8d %9d %10.4f %10.3f%s'
                  % (step, len(fl), nif, ff, mx, '  ✅' if ff >= 0.10 else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
