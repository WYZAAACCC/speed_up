#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_lath_final.py --- 板条级组织的**鲁棒口径**综合测定（中位数，不用 mean/extent）。

按连通块（=单根/单束板条）测：
  * 三主轴半轴长度的**中位数**（用惯性张量特征向量当主轴，不用任意正交基）
  * 主轴与 n_hab / w / a 的夹角（判定"板条是否沿长轴 a 排列、薄方向是否 n_hab"）
  * 长/厚、宽/厚 的**中位数**（不用均值）
判据：长/厚 应显著 >1；主轴-最短 应与 n_hab 小夹角（薄方向 = 惯习面法向）。
用法：python3 _chk_lath_final.py results_lathrve_LR1_final.npz [...]
"""
import sys
import numpy as np
from scipy import ndimage as ndi

C_cub = None
for P in (sys.argv[1:] or ['results_lathrve_LR1_final.npz']):
    d = np.load(P)
    reg = d['reg']; N = int(d['N']); dx = float(d['dx']); L = N * dx
    npref = d['npref'] if 'npref' in d.files else None
    nv = 12
    print('=== %s  N=%d dx=%.1f nm L=%.2f um f=%.4f' %
          (P.split('/')[-1], N, dx * 1e9, L * 1e6, float(d['f'])))
    X, Y, Z = np.meshgrid(*(np.arange(N) for _ in range(3)), indexing='ij')
    pts_all = np.stack([X, Y, Z], -1).astype(float) * dx
    MIN = max(60, int(0.02 * (N ** 3) / 12))
    rows = []
    for v in range(1, nv + 1):
        m = (reg == v)
        if m.sum() < MIN:
            continue
        lab, nb = ndi.label(m, structure=np.ones((3, 3, 3)))
        sz = np.bincount(lab.ravel())
        idxs = np.argwhere(m)
        for bi in range(1, nb + 1):
            if sz[bi] < MIN:
                continue
            sel = lab[tuple(idxs.T)] == bi
            p = pts_all[tuple(idxs[sel].T)]
            p = p - p.mean(0)
            Cv = np.cov(p.T)
            ev, evec = np.linalg.eigh(Cv)
            o = np.argsort(ev)[::-1]
            ev = ev[o]; evec = evec[:, o]
            # 沿三个主轴的真实 extent
            ext = []
            for j in range(3):
                e = p @ evec[:, j]
                ext.append(e.max() - e.min())
            nm = {'V%d' % v: dict(long=ext[0], mid=ext[1], thick=ext[2], n=sz[bi])}
            if npref is not None:
                # 最短轴（厚方向）与 n_hab 的夹角
                dshort = np.abs(evec[:, 2] @ npref[v - 1])
                nm['V%d' % v]['ang_short_nhab'] = float(np.degrees(np.arccos(np.clip(dshort, 0, 1))))
            rows.append(nm['V%d' % v])
    if not rows:
        print('   无满足门槛的块'); continue
    lo = np.array([r['long'] for r in rows]); mi = np.array([r['mid'] for r in rows])
    th = np.array([r['thick'] for r in rows])
    print('   块数 %d（每块 >=%d 胞）' % (len(rows), MIN))
    print('   中位数： 长 %.3f um  宽 %.3f um  厚 %.3f um' %
          (np.median(lo) * 1e6, np.median(mi) * 1e6, np.median(th) * 1e6))
    print('   **长/厚 中位 %.2f**   **宽/厚 中位 %.2f**   长/宽 中位 %.2f'
          % (np.median(lo / th), np.median(mi / th), np.median(lo / mi)))
    print('   参考：板条 长 1-20 um / 宽 0.25-0.9 um / 厚 0.1-0.3 um；长/厚 ~10-30')
    if 'ang_short_nhab' in rows[0]:
        a = np.array([r['ang_short_nhab'] for r in rows])
        print('   厚方向主轴 vs n_hab 夹角 中位 %.1f deg（越小 = 薄方向越对准惯习面法向；随机 57.3）'
              % np.median(a))
