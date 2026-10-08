#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r737_read.py <root> <tagA> <tagB> —— 200 步 A/B 的读数与判据判定。

判据（`_r736_ab2.py` docstring **先登记**）：
  M-0   内存 < 12 GB（由 watchdog 保证；本脚本只读归档，不复查）
  J-11  开关生效（至少一个可观测量不同）
  J-8b  公共安全步上 PCA 上升（开 > 关）
  J-5b  β_h^eff 兑现率的**多步中位** ≥ 0.98
  J-9b  f_flat 不劣化
  J-10b 同 Vt 的步数比 ∈ [0.8, 1.25]

⚠ 只取 `box_touch = 0` 的步（`R720 §1`）；β 用硬编码（快照不落盘，G-3 缺口仍在）。
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
    root, tA, tB = sys.argv[1], sys.argv[2], sys.argv[3]
    print('=' * 104)
    print('200 步 A/B：%s（NDIR_LSQ 关） vs %s（开）' % (tA, tB))
    print('=' * 104)
    R = {}
    for t in (tA, tB):
        d = os.path.join(root, 'dry_%s' % t)
        sp = os.path.join(d, 'series.csv')
        if not os.path.isfile(sp):
            print('  ⚠ 缺 %s' % sp)
            continue
        S = series(sp)
        for st in sorted(S):
            snap = os.path.join(d, 'snap_%05d.npz' % st)
            if not os.path.exists(snap):
                continue
            if str(S[st].get('box_touch', '?')) != '0':
                continue
            ff, bh, bw, mx, nc = gauges(snap)
            R[(t, st)] = dict(ff=ff, bh=bh, bw=bw, pca=mx, nc=nc,
                              Vt=float(S[st].get('Vt') or 'nan'),
                              nslab=S[st].get('nslab_n'))
    print('  %-8s %6s %8s %12s %10s %10s %9s %9s'
          % ('臂', 'step', 'nslab', 'Vt', 'f_flat', 'b_h^eff', '兑现率', 'PCA'))
    for (t, st), v in sorted(R.items()):
        print('  %-8s %6d %8s %12.4g %10.4f %10.4f %9.4f %9.3f'
              % (t, st, v['nslab'], v['Vt'], v['ff'], v['bh'], v['bh'] / BETA_H, v['pca']))
    both = sorted({s for (t, s) in R if t == tA} & {s for (t, s) in R if t == tB})
    print()
    if not both:
        print('  ⚪ **无法判定**：没有两臂都 `box_touch=0` 的公共步')
        return 0
    print('  公共安全步 = %s' % both)
    # J-11
    diff = any(R[(tA, s)]['pca'] != R[(tB, s)]['pca']
               or R[(tA, s)]['ff'] != R[(tB, s)]['ff'] for s in both)
    print('  J-11 开关生效：%s' % ('✅ 有可观测量不同' if diff else '⛔ 全部相同 ⇒ 开关可能失效'))
    # J-8b：最长公共安全步
    s = max(both)
    A, B = R[(tA, s)], R[(tB, s)]
    print('  ★ 最长公共安全步 = %d' % s)
    print('  J-8b PCA：%.3f → %.3f（%+.1f%%） ⇒ %s'
          % (A['pca'], B['pca'], 100 * (B['pca'] / A['pca'] - 1),
             '✅ 上升' if B['pca'] > A['pca'] else '⛔ 未上升'))
    # J-8b 逐公共步
    print('      逐公共步 PCA（关→开）:', end='')
    for x in both:
        print(' %d:%.2f→%.2f' % (x, R[(tA, x)]['pca'], R[(tB, x)]['pca']), end='')
    print()
    # J-5b
    # ⚠ 修（2026-10-08）：`np.median` 对含 nan 的数组返回 nan（step 0/25 无界面 ⇒ nan）
    #   ⇒ 第一版报出"中位 = nan ⇒ 靶 ≥0.98 ⛔"，**是量具 bug 不是引擎结论**。
    #   正解用 `np.nanmedian`，并**显式报出被剔除的 nan 个数**。
    q_all = [R[(tB, x)]['bh'] / BETA_H for x in both]
    q = [v for v in q_all if v == v]
    print('  J-5b 兑现率（开）逐公共步 = %s' % np.array2string(np.array(q_all), precision=4))
    print('      （其中 %d 个 step 无界面 ⇒ nan，已剔除）' % (len(q_all) - len(q)))
    if q:
        med = float(np.nanmedian(q))
        print('      中位 = %.4f ⇒ 靶 ≥0.98：%s' % (med, '✅' if med >= 0.98 else '⛔'))
        base = [R[(tA, x)]['bh'] / BETA_H for x in both if R[(tA, x)]['bh'] == R[(tA, x)]['bh']]
        print('      对照：关的中位 = %.4f ⇒ 提升 %+.4f'
              % (float(np.nanmedian(base)), med - float(np.nanmedian(base))))
    else:
        print('      ⚪ 无可判步')
    # J-9b
    print('  J-9b f_flat：%.4f → %.4f ⇒ %s'
          % (A['ff'], B['ff'], '✅ 不劣化' if B['ff'] >= A['ff'] else '⛔ 劣化'))
    # J-10b
    if len(both) >= 2:
        print('  J-10b 同 Vt：')
        for x in both:
            print('      step %d  Vt 关=%.6g  开=%.6g  比=%.4f'
                  % (x, R[(tA, x)]['Vt'], R[(tB, x)]['Vt'],
                     R[(tB, x)]['Vt'] / max(R[(tA, x)]['Vt'], 1e-300)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
