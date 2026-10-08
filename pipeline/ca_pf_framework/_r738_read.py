#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r738_read.py <root> —— 多种子 A/B 的读数与 `K-1…K-6` 判定。

判据（`_r738_multiseed.py` docstring **先登记**）：
  K-1（主） f_tip 中位：开 > 关，且 **3/3 种子同向**
  K-2（辅） PCA-D（全体胞并起来算一次）同向，≥2/3 种子
  K-3       全程 nslab == 1（单场阶段成立）
  K-4       β_h^eff 同向
  K-5       内存 < 12 GB（由 watchdog 保证）
  K-6       --eng-seed 真的改变结果（3 个种子的**关臂**读数不全同）

⚠ 主判据 `f_tip` 是**直接量**（端面胞占比），**不是**"逐场取最大" ⇒ 无 `R737 §3` 的
   "由偶然大场决定"的自由度。
"""
import csv
import os
import sys

import numpy as np

COS25 = float(np.cos(np.radians(25.0)))
BETA_H, BETA_W = 6.477, 2.3
SEEDS = [11, 23, 37]


def series(p):
    with open(p, newline='') as f:
        return {int(r['step']): r for r in csv.DictReader(f) if r.get('step')}


def gauges(sp):
    """返回 dict(f_tip, pcaD, pca_max, bh, nslab_fields, nif)."""
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
    # ⚠ 必须在 `with` 块**内**读完所有键 —— 第一版把 `z['w_ax']` 写在块外 ⇒
    #   `AttributeError: 'NoneType' object has no attribute 'open'`（文件已关）。
    nref = nref / (np.linalg.norm(nref) + 1e-300)
    wref = wref / (np.linalg.norm(wref) + 1e-300)
    nd, nif, mx, bodies = [], 0, 0.0, []
    bh_n = bh_d = 0.0
    nf = 0
    for k in sorted(int(v) for v in np.unique(fld) if v > 0):
        m = (fld == k)
        g = np.full(N ** 3, 1e3)
        g[idx[m]] = val[m]
        nb = int((g < 0).sum())
        if nb < 200:
            continue
        nf += 1
        gr = np.gradient(g.reshape(N, N, N), dx, edge_order=2)
        gn = np.sqrt(sum(x ** 2 for x in gr)) + 1e-300
        iface = (np.abs(g) <= 0.5 * dx).reshape(N ** 3)
        if int(iface.sum()) < 50:
            continue
        _n = np.stack([x / gn for x in gr], -1).reshape(N ** 3, 3)[iface]
        nd.append(_n); nif += int(iface.sum())
        bodies.append(P[g < 0])
        c2b = np.clip((_n @ nref) ** 2, 0, 1)
        c2w = np.clip((_n @ wref) ** 2, 0, 1)
        mm = np.exp(-BETA_H * c2b - BETA_W * c2w)
        wide = c2b >= 0.90
        if wide.any():
            bh_n += -np.log(max(float(mm[wide].mean()), 1e-300)) * int(wide.sum())
            bh_d += int(wide.sum())
        pts = P[g < 0]
        cen = pts - pts.mean(0)
        _, V = np.linalg.eigh(cen.T @ cen / max(len(cen), 1))
        pr = cen @ V
        s = np.sort(pr.max(0) - pr.min(0))[::-1]
        mx = max(mx, float(s[0] / max(s[2], 1e-30)))
    ftip = float((np.abs(np.concatenate(nd) @ a_ax) > COS25).mean()) if nd else float('nan')
    pcaD = float('nan')
    if bodies:
        allp = np.concatenate(bodies)
        cen = allp - allp.mean(0)
        _, V = np.linalg.eigh(cen.T @ cen / max(len(cen), 1))
        pr = cen @ V
        s = np.sort(pr.max(0) - pr.min(0))[::-1]
        pcaD = float(s[0] / max(s[2], 1e-30))
    return dict(ftip=ftip, pcaD=pcaD, pca_max=mx,
                bh=(bh_n / bh_d if bh_d else float('nan')),
                nf=nf, nif=nif)


def main():
    root = sys.argv[1]
    print('=' * 104)
    print('多种子 A/B（root=%s）—— 主判据 `f_tip`（直接量）' % root)
    print('=' * 104)
    R = {}
    for sd in SEEDS:
        for arm in ('off', 'on'):
            t = 'sd%d_%s' % (sd, arm)
            d = os.path.join(root, 'dry_%s' % t)
            sp0 = os.path.join(d, 'series.csv')
            if not os.path.isfile(sp0):
                print('  ⚠ 缺 %s' % t)
                continue
            S = series(sp0)
            for st in (50, 75, 100):
                sn = os.path.join(d, 'snap_%05d.npz' % st)
                if not os.path.exists(sn) or str(S.get(st, {}).get('box_touch', '?')) != '0':
                    continue
                g = gauges(sn)
                g['nslab'] = S[st].get('nslab_n')
                g['Vt'] = float(S[st].get('Vt') or 'nan')
                R[(sd, arm, st)] = g
    print('  %-6s %-4s %5s %7s %8s %10s %10s %10s'
          % ('seed', '臂', 'step', 'nslab', '场数', 'f_tip', 'PCA-D', 'b_h^eff'))
    for k in sorted(R):
        v = R[k]
        print('  %-6d %-4s %5d %7s %8d %10.4f %10.3f %10.4f'
              % (k[0], k[1], k[2], v['nslab'], v['nf'], v['ftip'], v['pcaD'], v['bh']))
    print()
    # K-3
    ns = {v['nslab'] for v in R.values()}
    print('  K-3 单场阶段（`nslab` 应恒为 1）：实测取值集合 = %s ⇒ %s'
          % (sorted(ns), '✅ PASS' if ns == {'1'} else '⛔ FAIL'))
    # K-6
    offs = [R[(sd, 'off', 100)]['ftip'] for sd in SEEDS if (sd, 'off', 100) in R]
    print('  K-6 `--eng-seed` 有效（关臂 @100 的 f_tip 不全同）：%s ⇒ %s'
          % (np.array2string(np.array(offs), precision=4),
             '✅ PASS' if len(set(np.round(offs, 9))) > 1 else '⛔ FAIL（种子是空操作）'))
    print()
    # K-1（主）
    for st in (50, 75, 100):
        d = []
        for sd in SEEDS:
            a = R.get((sd, 'off', st)); b = R.get((sd, 'on', st))
            if a and b and a['ftip'] == a['ftip'] and b['ftip'] == b['ftip']:
                d.append(b['ftip'] / a['ftip'] - 1)
        if not d:
            continue
        dd = np.array(d)
        npos = int((dd > 0).sum())
        print('  K-1 @%3d  f_tip(开/关−1) 逐种子 = %s  ⇒ 中位 %+.2f%%，%d/%d 同向 %s'
              % (st, np.array2string(dd * 100, precision=2),
                 100 * float(np.median(dd)), npos, len(dd),
                 '✅' if npos == len(dd) else '🟡' if npos >= len(dd) / 2 else '⛔'))
    # K-2
    for st in (100,):
        d = []
        for sd in SEEDS:
            a = R.get((sd, 'off', st)); b = R.get((sd, 'on', st))
            if a and b and a['pcaD'] == a['pcaD'] and b['pcaD'] == b['pcaD']:
                d.append(b['pcaD'] / a['pcaD'] - 1)
        if d:
            dd = np.array(d)
            npos = int((dd > 0).sum())
            print('  K-2 @%3d  PCA-D(开/关−1) 逐种子 = %s ⇒ 中位 %+.2f%%，%d/%d 同向 %s'
                  % (st, np.array2string(dd * 100, precision=2),
                     100 * float(np.median(dd)), npos, len(dd),
                     '✅' if npos >= 2 * len(dd) / 3 else '⛔'))
    # K-4
    for st in (100,):
        d = []
        for sd in SEEDS:
            a = R.get((sd, 'off', st)); b = R.get((sd, 'on', st))
            if a and b and a['bh'] == a['bh'] and b['bh'] == b['bh']:
                d.append(b['bh'] / a['bh'] - 1)
        if d:
            dd = np.array(d)
            npos = int((dd > 0).sum())
            print('  K-4 @%3d  β_h^eff(开/关−1) 逐种子 = %s ⇒ %d/%d 同向 %s'
                  % (st, np.array2string(dd * 100, precision=3), npos, len(dd),
                     '✅' if npos == len(dd) else '🟡'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
