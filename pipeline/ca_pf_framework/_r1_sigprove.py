#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_sigprove.py --- 证明"逐分量中位量必须只在**显著分量**上取"（修复前 vs 修复后）。

背景（`_r1_exp.py` 自查第 6 个 bug）
------------------------------------
`comps` 的门槛只有 8 胞 ⇒ 一旦**碎屑液滴**在**个数**上超过主板，中位量就被碎屑接管。
实测 `e5_equi6` step 485：`ncomp`=25、`nsig`=1，而 `align_deg`（全分量中位）= **85.89°**。

本脚本**直接从快照重算**三种口径，看它们差多少：
  (a) **全部**分量（旧口径）
  (b) 只保留**显著**分量（≥1% 胞，新口径 = `nsig` 口径）
  (c) 只取**最大**分量
若 (a) 与 (b) 差很多而 (b)≈(c)，则修复是必要的，且新口径正确。

用法：`python3 _r1_sigprove.py <算例目录> [快照序号，默认最后一个]`
"""
import glob
import json
import os
import sys

import numpy as np
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


d = sys.argv[1] if len(sys.argv) > 1 else 'e5_equi6'
DIR = os.path.join(HERE, '_exp', d)
snaps = sorted(glob.glob(os.path.join(DIR, 'snap_*.npz')))
if not snaps:
    print('✗ 没有快照：%s' % DIR); sys.exit(1)
snap = snaps[-1]
print('=' * 96)
print('算例 %s ；快照 %s' % (d, os.path.basename(snap)))
z = np.load(snap)
reg = z['region']
print('   region 形状 %s dtype %s ；变体标签取值 %s'
      % (reg.shape, reg.dtype, np.unique(reg)[:8]))
mp = os.path.join(DIR, 'meta.json')
dx = 125.0
if os.path.exists(mp):
    dx = json.load(open(mp)).get('dx_nm') or dx
print('   Δx = %g nm' % dx)

# 目标变体 K0：取占有胞数最多的那个非零标签（与 `--kv` 一致的用法）
vals, cnts = np.unique(reg[reg > 0], return_counts=True)
K0 = int(vals[np.argmax(cnts)])
print('   目标变体 K0 = %d（占 %d 胞）' % (K0, int(cnts.max())))

try:
    # ★ 与 `_r1_exp.py:axes_of` **逐字相同**的定义：
    #   `n_hab = NPF[K]`、`a_ax = g.atab[K]` 再对 `n_hab` 正交化。
    #   `atab`/`wtab` 只由 (C, eps0) 决定、**与 N 无关** ⇒ 用一个极小盒子(N=8)
    #   构造引擎即可拿到（构造含 12 次 `argmin_normal`，代价很小）。
    import windowB_surface as W
    from T16_verify_rve import C as C_rve, EPS0 as EPS0_rve, NV as NV_rve, NPF as NPF_rve
    _g = W.LevelSetMulti(8, 1.0e-6, C=C_rve, eps0=EPS0_rve, gamma=0.15,
                         Mob=1.0, df=[0.0] * (NV_rve + 1), workers=1)
    n_hab = np.asarray(NPF_rve[K0], float)
    n_hab = n_hab / np.linalg.norm(n_hab)
    a_ax = np.asarray(_g.atab[K0], float)
    a_ax = a_ax - (a_ax @ n_hab) * n_hab
    a_ax = a_ax / (np.linalg.norm(a_ax) + 1e-300)
    print('   a 轴（与 `_r1_exp.axes_of` 同一定义）= [%+.4f %+.4f %+.4f]'
          % tuple(a_ax))
except Exception as e:                                                   # noqa: BLE001
    print('   ⛔ 取不到 `a` 轴（%s: %s）⇒ **本脚本结论无效**，不得引用'
          % (type(e).__name__, e))
    sys.exit(2)

m = (reg == K0)
lab, ncomp = nd.label(m)
sizes = nd.sum(m, lab, range(1, ncomp + 1))
tot = int(m.sum())
thr = 0.01 * tot
print('   连通分量：ncomp=%d ；显著（≥1%%=%.0f 胞）：%d ；碎屑体积占比 %.4f'
      % (ncomp, thr, int((sizes >= thr).sum()),
         1.0 - float(sizes[sizes >= thr].sum()) / max(tot, 1)))


def align_of(ci):
    mc = (lab == ci)
    if int(mc.sum()) < 8:
        return None
    ici = np.argwhere(mc).astype(np.float64)
    cm = ici.mean(0)
    try:
        _, _, vt = np.linalg.svd(ici - cm, full_matrices=False)
        u0 = vt[0] / (np.linalg.norm(vt[0]) + 1e-300)
        return float(np.degrees(np.arccos(min(1.0, abs(float(u0 @ a_ax))))))
    except Exception:                                                    # noqa: BLE001
        return None


allc, sig, big = [], [], None
for ci in range(1, ncomp + 1):
    al = align_of(ci)
    if al is None:
        continue
    allc.append((int(sizes[ci - 1]), al))
    if sizes[ci - 1] >= thr:
        sig.append((int(sizes[ci - 1]), al))
    if big is None or sizes[ci - 1] > big[0]:
        big = (int(sizes[ci - 1]), al)

print('-' * 96)
print('   %-34s %6s %10s' % ('口径', 'n', 'align_deg'))
if allc:
    print('   %-34s %6d %10.2f' % ('(a) **全部**分量（旧口径）', len(allc),
                                   float(np.median([x[1] for x in allc]))))
if sig:
    print('   %-34s %6d %10.2f' % ('(b) 只留**显著**分量（新口径）', len(sig),
                                   float(np.median([x[1] for x in sig]))))
if big:
    print('   %-34s %6d %10.2f' % ('(c) 只取**最大**分量', 1, big[1]))
print('-' * 96)
if allc and sig:
    d_ab = abs(float(np.median([x[1] for x in allc]))
               - float(np.median([x[1] for x in sig])))
    print('   (a) 与 (b) 之差 = **%.2f°**  ⇒ %s'
          % (d_ab, '✅ **修复必要且有效**（旧口径被碎屑接管）' if d_ab > 20
             else '差异不大（本快照碎屑不多）'))
print('=' * 96)
