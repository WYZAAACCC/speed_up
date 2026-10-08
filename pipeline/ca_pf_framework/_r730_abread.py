#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r730_abread.py <root> <tagA> <tagB> —— R730 的 A/B 读数 + 判据判定。

判据（`R727 §3`，**先登记**）：
  **J-1** 默认关 ⇒ 归档逐位一致（由 `_r30_regress.sh` 单独判，本脚本不重复）
  **J-5** `beta_h^eff` 兑现率上升（基线 **0.953**，靶 **≥0.98**）
  **J-9** `f_flat` 不劣化（`R720 §2`：它是**衰减量** ⇒ **必须报步数**）
  **J-10** 步数比 ∈ **[0.8, 1.25]**（同 `Vt` 下）
  ⚪ 「无法判定」：`box_touch=1`（`R720 §1`）或界面胞 < 50

本脚本**只读快照 + series.csv**。
"""
import csv
import os
import sys

import numpy as np

COS25 = float(np.cos(np.radians(25.0)))
BETA_H = 6.477
BETA_W = 2.3


def read_series(p):
    with open(p, newline='') as f:
        rd = csv.DictReader(f)
        return list(rd)


def gauges(snappath):
    """返回 (f_flat, beta_h_eff, beta_w_eff, pca_max, ncell, box_touch_unknown)"""
    with np.load(snappath, allow_pickle=False) as z:
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
    nd, nif, mx, ncell = [], 0, 0.0, 0
    bh_num = bh_den = bw_num = bw_den = 0.0
    for k in sorted(int(v) for v in np.unique(fld) if v > 0):
        m = (fld == k)
        g = np.full(N ** 3, 1e3)
        g[idx[m]] = val[m]
        nb = int((g < 0).sum())
        if nb < 200:
            continue
        ncell += nb
        gr = np.gradient(g.reshape(N, N, N), dx, edge_order=2)
        gn = np.sqrt(sum(x ** 2 for x in gr)) + 1e-300
        iface = (np.abs(g) <= 0.5 * dx).reshape(N ** 3)
        ni = int(iface.sum())
        if ni < 50:
            continue
        _n = np.stack([x / gn for x in gr], -1).reshape(N ** 3, 3)[iface]
        nd.append(_n); nif += ni
        c2b = np.clip((_n @ nref) ** 2, 0, 1)
        c2w = np.clip((_n @ wref) ** 2, 0, 1)
        mm = np.exp(-BETA_H * c2b - BETA_W * c2w)
        wide = c2b >= 0.90
        side = c2w >= 0.90
        if wide.any():
            bh_num += -np.log(max(float(mm[wide].mean()), 1e-300)) * int(wide.sum())
            bh_den += int(wide.sum())
        if side.any():
            bw_num += -np.log(max(float(mm[side].mean()), 1e-300)) * int(side.sum())
            bw_den += int(side.sum())
        pts = P[g < 0]
        cen = pts - pts.mean(0)
        _, V = np.linalg.eigh(cen.T @ cen / max(len(cen), 1))
        pr = cen @ V
        sp = np.sort(pr.max(0) - pr.min(0))[::-1]
        mx = max(mx, float(sp[0] / max(sp[2], 1e-30)))
    ff = (float((np.abs(np.concatenate(nd) @ a_ax) > COS25).mean()) if nd else float('nan'))
    bh = bh_num / bh_den if bh_den else float('nan')
    bw = bw_num / bw_den if bw_den else float('nan')
    return ff, bh, bw, mx, ncell


def main():
    root, tA, tB = sys.argv[1], sys.argv[2], sys.argv[3]
    print('=' * 100)
    print('R730 A/B：`NDIR_LSQ` 关(%s) vs 开(%s)' % (tA, tB))
    print('=' * 100)
    res = {}
    for t in (tA, tB):
        d = os.path.join(root, 'dry_%s' % t)
        ser = read_series(os.path.join(d, 'series.csv'))
        for r in ser:
            st = int(r['step'])
            sp = os.path.join(d, 'snap_%05d.npz' % st)
            if not os.path.exists(sp):
                continue
            ff, bh, bw, mx, nc = gauges(sp)
            res[(t, st)] = dict(ff=ff, bh=bh, bw=bw, pca=mx, nc=nc,
                                bt=r.get('box_touch'), Vt=float(r.get('Vt') or 'nan'),
                                nslab=r.get('nslab_n'))
    print('  %-10s %6s %8s %9s %10s %10s %9s %9s' %
          ('tag', 'step', 'box', 'nslab', 'f_flat', 'b_h^eff', '兑现率', 'PCA'))
    for (t, st), v in sorted(res.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        print('  %-10s %6d %8s %9s %10.4f %10.4f %9.3f %9.3f'
              % (t, st, v['bt'], v['nslab'], v['ff'], v['bh'],
                 v['bh'] / BETA_H if v['bh'] == v['bh'] else float('nan'), v['pca']))
    print()
    both = [s for s in (25, 50, 75, 100)
            if (tA, s) in res and (tB, s) in res
            and str(res[(tA, s)]['bt']) == '0' and str(res[(tB, s)]['bt']) == '0']
    if not both:
        print('  ⚪ **无法判定**：没有 `box_touch=0` 的公共步（`R720 §1`）')
        return 0
    s = max(both)
    A, B = res[(tA, s)], res[(tB, s)]
    print('  ★ 公共安全步 = %d' % s)
    print('  J-5  beta_h^eff 兑现率：%.3f → %.3f  （靶 ≥0.98） ⇒ %s'
          % (A['bh'] / BETA_H, B['bh'] / BETA_H,
             '✅' if B['bh'] / BETA_H >= 0.98 else '⛔'))
    print('  J-9  f_flat：%.4f → %.4f  ⇒ %s'
          % (A['ff'], B['ff'], '✅ 不劣化' if B['ff'] >= A['ff'] else '⛔ 劣化'))
    print('  （参考）PCA：%.3f → %.3f ； 界面胞数：%d → %d'
          % (A['pca'], B['pca'], A['nc'], B['nc']))
    # J-10：同 Vt 步数比（若无交叉就给当前比值）
    print('  J-10 同 Vt 步数比：本脚本只到 step %d，Vt=%.6g vs %.6g'
          % (s, A['Vt'], B['Vt']))
    print('  ⚠ J-8（长厚比）需要更长的安全窗口 ⇒ 本轮 100 步内**不足以判**')
    return 0


if __name__ == '__main__':
    sys.exit(main())
