#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r733_longread.py <root> —— 长 A/B 的读数 + `J-5b/J-8b/J-9b/J-10b/J-11` 判定。

判据（`_r733_longab.py` docstring **先登记**）：
  J-8b  两臂在各自 `box_touch=0` 的**公共最长步**上比 PCA → 开 > 关（方向）
  J-5b  `β_h^eff` 兑现率**多个步的中位** ≥ 0.98
  J-9b  `f_flat` 不劣化
  J-10b 同 `Vt` 的步数比 ∈ [0.8, 1.25]
  J-11  开关生效性（至少一个可观测标量不同）

⚠ 全部读数**只取 `box_touch=0` 的步**（`R720 §1`）；`β_h` 用硬编码（快照不落盘，G-3 缺口仍在）。
"""
import csv
import os
import sys

import numpy as np

COS25 = float(np.cos(np.radians(25.0)))
BETA_H, BETA_W = 6.477, 2.3


def series(p):
    with open(p, newline='') as f:
        return {int(r['step']): r for r in csv.DictReader(f) if r.get('step')}


def gauges(sp):
    with np.load(sp, allow_pickle=False) as z:
        N = int(np.asarray(z['N']).ravel()[0])
        L = float(np.asarray(z['L']).ravel()[0])
        dx = L / N
        ii = (np.arange(N) + 0.5) * dx
        P = np.stack(np.meshgrid(ii, ii, ii, indexing='ij'), -1).reshape(-1, 3)
        idx = np.asarray(z['band_idx']); val = np.asarray(z['band_val'], float)
        fld = np.asarray(z['band_fld'])
        a_ax = np.asarray(z['a_ax'], float)
        nref = np.asarray(z['n_hab'], float)
        wref = np.asarray(z['w_ax'], float)
    nref = nref / (np.linalg.norm(nref) + 1e-300)
    wref = wref / (np.linalg.norm(wref) + 1e-300)
    nd, nif, mx = [], 0, 0.0
    bh_n = bh_d = bw_n = bw_d = 0.0
    for k in sorted(int(v) for v in np.unique(fld) if v > 0):
        m = (fld == k)
        g = np.full(N ** 3, 1e3)
        g[idx[m]] = val[m]
        if int((g < 0).sum()) < 200:
            continue
        gr = np.gradient(g.reshape(N, N, N), dx, edge_order=2)
        gn = np.sqrt(sum(x ** 2 for x in gr)) + 1e-300
        iface = (np.abs(g) <= 0.5 * dx).reshape(N ** 3)
        if int(iface.sum()) < 50:
            continue
        _n = np.stack([x / gn for x in gr], -1).reshape(N ** 3, 3)[iface]
        nd.append(_n); nif += int(iface.sum())
        c2b = np.clip((_n @ nref) ** 2, 0, 1)
        c2w = np.clip((_n @ wref) ** 2, 0, 1)
        mm = np.exp(-BETA_H * c2b - BETA_W * c2w)
        wide = c2b >= 0.90
        side = c2w >= 0.90
        if wide.any():
            bh_n += -np.log(max(float(mm[wide].mean()), 1e-300)) * int(wide.sum())
            bh_d += int(wide.sum())
        if side.any():
            bw_n += -np.log(max(float(mm[side].mean()), 1e-300)) * int(side.sum())
            bw_d += int(side.sum())
        pts = P[g < 0]
        cen = pts - pts.mean(0)
        _, V = np.linalg.eigh(cen.T @ cen / max(len(cen), 1))
        pr = cen @ V
        sp_ = np.sort(pr.max(0) - pr.min(0))[::-1]
        mx = max(mx, float(sp_[0] / max(sp_[2], 1e-30)))
    ff = float((np.abs(np.concatenate(nd) @ a_ax) > COS25).mean()) if nd else float('nan')
    return ff, (bh_n / bh_d if bh_d else float('nan')), \
        (bw_n / bw_d if bw_d else float('nan')), mx, nif


def main():
    root = sys.argv[1]
    tA, tB = 'L_off', 'L_on'
    print('=' * 104)
    print('F-1 长 A/B（N=128、6 µm、300 步）：%s（关） vs %s（开）' % (tA, tB))
    print('=' * 104)
    R = {}
    for t in (tA, tB):
        d = os.path.join(root, 'dry_%s' % t)
        sp = os.path.join(d, 'series.csv')
        if not os.path.isfile(sp):
            print('  ⚠ 缺 %s' % sp); continue
        S = series(sp)
        for st in sorted(S):
            snap = os.path.join(d, 'snap_%05d.npz' % st)
            if not os.path.exists(snap):
                continue
            bt = str(S[st].get('box_touch', '?'))
            if bt != '0':
                continue
            ff, bh, bw, mx, nc = gauges(snap)
            R[(t, st)] = dict(ff=ff, bh=bh, bw=bw, pca=mx, nc=nc,
                              Vt=float(S[st].get('Vt') or 'nan'),
                              nslab=S[st].get('nslab_n'))
    print('  %-8s %6s %8s %11s %10s %10s %9s %9s'
          % ('臂', 'step', 'nslab', 'Vt', 'f_flat', 'b_h^eff', '兑现率', 'PCA'))
    for (t, st), v in sorted(R.items()):
        print('  %-8s %6d %8s %11.4g %10.4f %10.4f %9.3f %9.3f'
              % (t, st, v['nslab'], v['Vt'], v['ff'], v['bh'], v['bh'] / BETA_H, v['pca']))
    both = sorted({s for (t, s) in R if t == tA} & {s for (t, s) in R if t == tB})
    print()
    if not both:
        print('  ⚪ **无法判定**：没有两臂都 `box_touch=0` 的公共步')
        return 0
    print('  公共安全步 = %s（最长 %d）' % (both, max(both)))
    s = max(both)
    A, B = R[(tA, s)], R[(tB, s)]
    print('  ★ 最长公共安全步 = %d' % s)
    print('  J-8b PCA：%.3f → %.3f  ⇒ %s'
          % (A['pca'], B['pca'], '✅ 上升' if B['pca'] > A['pca'] else '⛔ 未上升'))
    r5 = [R[(tB, x)]['bh'] / R[(tA, x)]['bh'] for x in both
          if R[(tA, x)]['bh'] == R[(tA, x)]['bh'] and R[(tB, x)]['bh'] == R[(tB, x)]['bh']]
    if r5:
        print('  J-5b 兑现率（开/关）逐公共步 = %s' % np.array2string(
            np.array([R[(tB, x)]['bh'] / BETA_H for x in both]), precision=4))
        print('        中位 = %.4f  ⇒ 靶 ≥0.98：%s'
              % (float(np.median([R[(tB, x)]['bh'] / BETA_H for x in both])),
                 '✅' if float(np.median([R[(tB, x)]['bh'] / BETA_H for x in both])) >= 0.98
                 else '⛔'))
    print('  J-9b f_flat：%.4f → %.4f  ⇒ %s'
          % (A['ff'], B['ff'], '✅ 不劣化' if B['ff'] >= A['ff'] else '⛔ 劣化'))
    print('  J-11 开关生效：PCA %s / f_flat %s / β_h^eff %s'
          % ('变' if A['pca'] != B['pca'] else '不变',
             '变' if A['ff'] != B['ff'] else '不变',
             '变' if A['bh'] != B['bh'] else '不变'))
    # J-10b：同 Vt 步数比（用最近的两个公共点估）
    if len(both) >= 2:
        s1, s2 = both[0], both[-1]
        print('  J-10b 同 Vt 步数比：Vt@%d = %.4g vs %.4g ； Vt@%d = %.4g vs %.4g'
              % (s1, R[(tA, s1)]['Vt'], R[(tB, s1)]['Vt'],
                 s2, R[(tA, s2)]['Vt'], R[(tB, s2)]['Vt']))
        print('        （真正的"同 Vt 配对"需要插值，本脚本只报端点）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
