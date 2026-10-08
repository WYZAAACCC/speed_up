#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r720_geom.py <snap.npz> —— 逐场的**主轴三尺寸**（长 `L` / 宽 `W` / 厚 `t`）。

## 口径（**与 `_t11_thick3.py:83-89` 逐字一致**，即 `R666 §1.1` 判定"最可信"的那个）
```
cen  = pts − mean(pts)                  # 只用最大连通分量？—— ⚠ 本脚本用**全场体胞**
C    = cen^T cen / n                    # 协方差
w,V  = eigh(C)                          # 主轴
sp   = (cen @ V).max(0) − (cen @ V).min(0)   # 沿主轴的**投影跨度**
L/W/t = sp 降序前三
λ    = sp[0] / sp[2]                     # = `_b2_meas.py` 的 "PCA 长:短"
```
⚠ **记账**：`sp[2]` 是"沿最短主轴的投影跨度"，**不是**几何厚度；
`R666` 之所以选它，是因为它**对倾斜免疫**（三轴跨度口径会把斜放的板条量厚）。

## 用法
    python3 _r720_geom.py _exp/_bk_block/dry_B2P_q0/snap_00400.npz
"""
import sys

import numpy as np


def main():
    p = sys.argv[1]
    z = np.load(p, allow_pickle=False)
    N = int(np.asarray(z['N']).ravel()[0])
    L_box = float(np.asarray(z['L']).ravel()[0])
    dx = L_box / N
    ii = (np.arange(N) + 0.5) * dx
    P = np.stack(np.meshgrid(ii, ii, ii, indexing='ij'), -1).reshape(-1, 3)
    idx = np.asarray(z['band_idx']); val = np.asarray(z['band_val'], float)
    fld = np.asarray(z['band_fld'])
    print('=' * 100)
    print('%s   N=%d  dx=%.2f nm' % (p, N, dx * 1e9))
    print('=' * 100)
    print('  %-4s %8s %10s %10s %10s %10s' %
          ('场', '体胞', 'L(nm)', 'W(nm)', 't(nm)', 'λ=L/t'))
    best = None
    for k in sorted(int(v) for v in np.unique(fld) if v > 0):
        m = (fld == k)
        g = np.full(N ** 3, 1e3, float)
        g[idx[m]] = val[m]
        body = g < 0
        nb = int(body.sum())
        if nb < 200:
            continue
        pts = P[body]
        cen = pts - pts.mean(0)
        C = cen.T @ cen / max(len(cen), 1)
        _, V = np.linalg.eigh(C)
        pr = cen @ V
        sp = np.sort(pr.max(0) - pr.min(0))[::-1]
        lam = float(sp[0] / max(sp[2], 1e-30))
        print('  %-4d %8d %10.1f %10.1f %10.1f %10.3f'
              % (k, nb, sp[0] * 1e9, sp[1] * 1e9, sp[2] * 1e9, lam))
        if best is None or nb > best[1]:
            best = (k, nb, sp[0], sp[1], sp[2], lam)
    if best:
        k, nb, l_, w_, t_, lam = best
        print()
        print('  ★ **最大场**（= 主分量）：场 %d，%d 胞' % (k, nb))
        print('     L = %.1f nm = %.4f µm' % (l_ * 1e9, l_ * 1e6))
        print('     W = %.1f nm = %.4f µm' % (w_ * 1e9, w_ * 1e6))
        print('     t = %.1f nm = %.4f µm' % (t_ * 1e9, t_ * 1e6))
        print('     λ = L/t = %.3f' % lam)
        print()
        print('  ⇒ 喂 S5 标定链的命令（`--t-um`/`--L-um`/`--W-um` 取上面三个数）：')
        print('     python3 _r720_calib_chain.py --t-um %.4f --L-um %.4f --W-um %.4f'
              ' --V-box-um3 %.1f' % (t_ * 1e6, l_ * 1e6, w_ * 1e6, (N * dx) ** 3 * 1e18))
    return 0


if __name__ == '__main__':
    sys.exit(main())
