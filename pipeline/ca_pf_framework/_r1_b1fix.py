#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_b1fix.py --- 按台账 B-17 的修法**重推 B-1**：改用"跨度最大的那条轴"，不用 PCA 主轴。

为什么必须重推
--------------
B-1 判据原本是「各分量长轴与 `a` 的夹角 ≤20°」，而"长轴"取的是
`align_deg` = **PCA 主轴0 与 `a` 的夹角**（`_r1_exp.py:268`）。
但实测 `e5_equi6` 最大分量的奇异值是 **[2631.6, 2456.3, 181.]**
⇒ `σ₂/σ₁ = 0.93`（**近简并**）⇒ 片内两条轴的"谁是第一"是 **SVD 的数值任选**
⇒ 主轴角在物理上**没有定义**（该分量实测主轴0=83.48°、主轴1=6.52°，同一平面）。

改成什么
--------
**跨度最大的那条轴**：对每个显著分量算三向跨度（沿 a / w / n*，与 `measure()` 同一算法），
取 `argmax` 的那条轴，报它与 `a` 的夹角。
  * 这个量**不依赖任何简并**（三向跨度是三个标量，比较大小即可）；
  * 它与 B-1 想表达的"板条长轴是否沿 `a`"**语义一致**（"长轴"= 伸得最长的方向）。
另外记录 `σ₂/σ₁` 作为**简并度指示**，`≥0.9` 标注为 `undetermined`（供对照）。

用法：`python3 _r1_b1fix.py e4_lath6 e6_mid6 e5_equi6`
"""
import csv
import glob
import json
import os
import sys

import numpy as np
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


_AXCACHE = {}


def axes_of(K):
    """与 `_r1_exp.axes_of` **逐字相同**的三轴定义（用极小盒子取 `wtab/atab`）。

    ⚠ 记账（本脚本第一版）：`axes_of(K)` 内部要**构造一次 `LevelSetMulti`**
    （含 12 次 `argmin_normal`），而我在**快照循环里逐个调用**它 ——
    但 `atab/wtab/NPF` **只依赖 K（变体号）**，与快照无关
    ⇒ 每个快照都重建一次引擎，白烧 ~100 倍时间（实测 3 个臂要 30 分钟以上）。
    ⇒ 加**按 K 的缓存**（同一臂里 K0 通常恒为 1，只算一次）。
    """
    if K in _AXCACHE:
        return _AXCACHE[K]
    import windowB_surface as W                                        # noqa: E402
    from T16_verify_rve import C, EPS0, NV, NPF                        # noqa: E402
    g = W.LevelSetMulti(8, 1.0e-6, C=C, eps0=EPS0, gamma=0.15,
                        Mob=1.0, df=[0.0] * (NV + 1), workers=1)
    nh = np.asarray(NPF[K], float); nh /= np.linalg.norm(nh)
    ww = np.asarray(g.wtab[K], float); ww /= np.linalg.norm(ww)
    aa = np.asarray(g.atab[K], float)
    aa = aa - (aa @ nh) * nh
    aa /= (np.linalg.norm(aa) + 1e-300)
    _AXCACHE[K] = (aa, ww, nh)
    return _AXCACHE[K]


def scan(arm):
    DIR = os.path.join(HERE, '_exp', arm)
    snaps = sorted(glob.glob(os.path.join(DIR, 'snap_*.npz')))
    if not snaps:
        print('%-12s ✗ 无快照' % arm); return
    meta = json.load(open(os.path.join(DIR, 'meta.json')))
    nseed = meta.get('nseed') or 1
    rows = []
    for sp in snaps:
        z = np.load(sp)
        reg = z['region']
        step = int(z['step']) if 'step' in z.files else -1
        vals, cnts = np.unique(reg[reg > 0], return_counts=True)
        if vals.size == 0:
            continue
        K0 = int(vals[np.argmax(cnts)])
        a_ax, w_ax, n_hab = axes_of(K0)
        m = (reg == K0)
        lab, ncomp = nd.label(m)
        if ncomp == 0:
            continue
        sizes = np.array(nd.sum(m, lab, range(1, ncomp + 1)), dtype=int)
        thr = 0.01 * int(m.sum())
        keep = [i + 1 for i in range(ncomp) if sizes[i] >= thr] or \
               [int(np.argmax(sizes)) + 1]
        angs, degs = [], []
        for ci in keep:
            ici = np.argwhere(lab == ci).astype(np.float64)
            sp_a = np.ptp(ici @ a_ax)
            sp_w = np.ptp(ici @ w_ax)
            sp_n = np.ptp(ici @ n_hab)
            # ★ 新的"长轴"= 跨度最大的那条轴（不依赖简并）
            k = int(np.argmax([sp_a, sp_w, sp_n]))
            axis = (a_ax, w_ax, n_hab)[k]
            angs.append(float(np.degrees(np.arccos(min(1.0, abs(float(axis @ a_ax)))))))
            # 简并度（对照用）
            c = ici.mean(0)
            sv = np.linalg.svd(ici - c, compute_uv=False)
            degs.append(float(sv[1] / max(sv[0], 1e-30)))
        if angs:
            rows.append((step, float(np.median(angs)), float(np.median(degs)),
                         len(angs)))
    if not rows:
        print('%-12s ✗ 无有效采样' % arm); return
    st = np.array([r[0] for r in rows], float)
    an = np.array([r[1] for r in rows], float)
    dg = np.array([r[2] for r in rows], float)
    print('\n' + '=' * 92)
    print('%s（nseed=%d，%d 个快照）' % (arm, nseed, len(rows)))
    print('   **新判据**（跨度最大轴的夹角，取显著分量的中位）：'
          '起始 %.2f° → 末态 %.2f° ；≤20° 的采样占比 **%.0f%%**'
          % (an[0], an[-1], 100 * float(np.mean(an <= 20))))
    print('   ⇒ B-1（新口径，双条件：末态 ≤20° 且 ≥50%% 采样 ≤20°）：**%s**'
          % ('通过' if (an[-1] <= 20 and np.mean(an <= 20) >= 0.5) else '不通过'))
    print('   简并度 σ₂/σ₁ 中位：起始 %.3f → 末态 %.3f ；'
          '**≥0.9 的采样占比 %.0f%%**（这些点上 PCA 主轴角本无定义）'
          % (dg[0], dg[-1], 100 * float(np.mean(dg >= 0.9))))
    # 与 CSV 里的旧 align_deg 对照
    cp = os.path.join(DIR, 'series.csv')
    if os.path.exists(cp):
        old = []
        for r in csv.DictReader(open(cp)):
            try:
                v = float(r['align_deg'])
                if np.isfinite(v):
                    old.append(v)
            except (TypeError, ValueError, KeyError):
                pass
        if old:
            old = np.array(old)
            print('   （对照）CSV 里的**旧** `align_deg`：起始 %.2f° → 末态 %.2f° ；'
                  '≤20° 占比 %.0f%% ⇒ 旧判据 **%s**'
                  % (old[0], old[-1], 100 * float(np.mean(old <= 20)),
                     '通过' if (old[-1] <= 20 and np.mean(old <= 20) >= 0.5) else '不通过'))


for arm in (sys.argv[1:] or ['e4_lath6', 'e6_mid6', 'e5_equi6']):
    scan(arm)
print('\n' + '=' * 92)
print('口径说明：新判据用**三向跨度取 argmax**定"长轴"，是三标量比大小 ⇒ 不受简并影响；')
print('          旧判据用 PCA 主轴0 ⇒ 在 σ₂/σ₁→1 时是数值任选（台账 B-17）。')
print('=' * 92)
