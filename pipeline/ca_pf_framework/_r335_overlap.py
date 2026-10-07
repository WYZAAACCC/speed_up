#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r335_overlap.py —— ★★ 直接测：引擎的 φ 场到底是不是**多相 SDF**（负区互斥）？

## 由来（`_r334` 的结论把问题逼到这里）

`_r334` 已确立两件事：
* 旧 C-1 掩码 `any(0)` 的 0.806–0.933 是**我的掩码错**（100% 的不符胞都满足
  「`region` 那个场自己没存」）；
* 但**严格掩码 R** 在**早期快照上 = 1.0000**（`sgG`/`t1N112L800` step=20），
  在**晚期快照上 0.936–0.982**（step 400/600）⇒ **有时间依赖的信号**。

逻辑推演（**这是纯推理，本脚本的任务就是把它变成实测**）：
设严格掩码里某胞 `argmin_stored = m`、`φ_m < 0`，但归档 `region = t ≠ m`。
  * 若 `t` **存了** ⇒ 存下来的最小值应是 `φ_t`（因为 `t` 是真 argmin）⇒ 与 `m` 矛盾
    ⇒ **`t` 必未存**；
  * `t` 未存 ⇒ `|φ_t| > BΔx`；又要 `φ_t < φ_m < 0` ⇒ **`φ_t < −BΔx`**。
  ⇒ 该胞上 **`φ_m < 0` 与 `φ_t < 0` 同时成立**（`m ≠ t`）
  ⇒ **不同场的负区（"内部"）重叠** ⇒ **φ 不是多相 SDF**。

## 为什么这件事**必须**单独定案（影响面很大）

`φ_k < 0 ⟺ 在区域 k 内` 是**大量测量工具与物理判断的隐含前提**：
`§132`/`§134` 的法向与 `c2p`、`_bk_measure` 的界面/面积口径、
`band_*` 能重建什么、乃至「`region` 与 `phi` 谁是真值」。
**前提若不成立，凡是依赖它的结论都要重新标注。**

## 判据（**先写死**）

* **M-1 直接观测（不依赖任何假设）**：存下来的 φ 里，
  `φ_k < 0` 而 `region ≠ k` 的**胞占比**。⇒ 这就是"负区重叠"的**直接证据**。
* **M-2 重叠层厚度**：把 `φ_k < 0 但 region ≠ k` 的胞按 `|φ_k|/Δx` 分桶
  ⇒ 若全部挤在 `|φ| ≲ 1Δx`（界面平滑层），性质**良性**；
  若伸到 `≈ BΔx`（6），性质**严重**。
* **M-3 双负胞**：有多少胞**同时**有两个存下来的场 `φ < 0`。
* **M-4 严格掩码的不符胞中，`t` 存了的占多少**：
  ⇒ 若 = 0，**完全**符合上面那条"未存 ⇒ φ_t < −BΔx"的推理（自洽）；
  ⇒ 若 > 0，则是**硬矛盾**（存下来的 argmin 不是 region，且 region 的场也存着）
    ⇒ 那是**代码级**问题，另行立案。
* **M-5 时间依赖**：step=20 的臂 vs step=400/600 的臂，M-1/M-3 的对比。
"""
from __future__ import annotations

import ast
import glob
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')


def rebuild(z):
    """与 `_r195`/`_r334` 相同的重建；带外 = NaN。"""
    N = int(z['N'])
    nf = int(z['band_fld'].max()) + 1 if z['band_fld'].size else 0
    phi = np.full((nf, N, N, N), np.nan, np.float32)
    flat = phi.reshape(nf, -1)
    flat[z['band_fld'].astype(int), z['band_idx'].astype(int)] = \
        z['band_val'].astype(np.float32)
    return phi


def main():
    print('=' * 108)
    print('_r335 —— 引擎的 φ 是**多相 SDF** 吗？（负区是否互斥）')
    print('=' * 108)
    arms = sys.argv[1:] or ['sgG', 't1N112L800', 'saSet2', 'saOddG',
                            'mb2fp10', 'swN128']
    rows = []
    for arm in arms:
        d = os.path.join(MB, 'dry_' + arm)
        fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
        if not fs:
            print('  %-12s ⚠ 无快照' % arm)
            continue
        for tag in ('first', 'last'):
            f = fs[0] if tag == 'first' else max(
                fs, key=lambda p: int(re.search(r'_(\d+)\.npz$', p).group(1)))
            z = np.load(f, allow_pickle=True)
            if 'band_idx' not in z:
                continue
            N = int(z['N'])
            B = int(z['band_cells'])
            reg = np.asarray(z['region'], np.int64)
            p = rebuild(z)
            nf = p.shape[0]
            fin = np.isfinite(p)
            stored = fin  # (nf,N,N,N)
            nst = stored.sum(0)
            neg = stored & (p < 0.0)
            nneg = neg.sum(0)
            # M-1：存下来的负值里，region ≠ k 的占比
            kk = np.arange(nf)[:, None, None, None]
            wrong = neg & (reg[None] != kk)
            tot_neg = int(neg.sum())
            tot_wrong = int(wrong.sum())
            # M-2：分桶（用该臂真实的 Δx）
            dxx = 62.5e-9
            mf = os.path.join(d, 'meta.json')
            if os.path.exists(mf):
                dxx = float(json.load(open(mf)).get('dx_nm', 62.5)) * 1e-9
            if tot_wrong:
                av = np.abs(p[wrong]) / dxx
                b = np.bincount(np.clip(av.astype(int), 0, 9), minlength=10)
            else:
                b = np.zeros(10, int)
                av = np.zeros(0)
            # M-3 双负胞
            m3 = int((nneg >= 2).sum())
            # M-4 严格掩码不符胞中 t 存了的占比
            full = np.where(fin, p, np.inf)
            am = np.argmin(full, 0)
            minval = np.min(full, 0)
            strict = fin.all(0) | (minval < 0.0)
            bad = strict & (am != reg)
            nb = int(bad.sum())
            if nb:
                ii = np.where(bad)
                t_stored = fin[reg[ii], ii[0], ii[1], ii[2]]
                hard = int(t_stored.sum())
            else:
                hard = 0
            print()
            print('  ### %-12s %-5s step=%-5s nf=%-3d N=%-4d B=%d' %
                  (arm, tag, z['step'], nf, N, B))
            print('      M-1 存下来的负值胞 **%d**，其中 `region ≠ k`（**负区重叠**）'
                  '**%d** ⇒ **%.3f%%**' %
                  (tot_neg, tot_wrong,
                   100.0 * tot_wrong / max(tot_neg, 1)))
            print('      M-2 `|φ|/Δx` 分桶 [0..9] = %s  （中位 %.2f，p90 %.2f）' %
                  (b.tolist(),
                   float(np.median(av)) if av.size else float('nan'),
                   float(np.percentile(av, 90)) if av.size else float('nan')))
            print('      M-3 **双负胞**（两个存下来的场同时 φ<0）= **%d**（%.3f%% of %d）' %
                  (m3, 100.0 * m3 / float(N ** 3), N ** 3))
            print('      M-4 严格掩码不符胞 **%d**，其中 **region 的场也存着** 的 = '
                  '**%d** ⇒ %s' %
                  (nb, hard,
                   '✅ 与"未存 ⇒ φ_t<−BΔx"推理自洽' if hard == 0 else
                   '❌ **硬矛盾**（存下来的 argmin ≠ region）⇒ 代码级问题'))
            rows.append((arm, tag, int(z['step']), tot_neg, tot_wrong, m3, nb, hard))
    print()
    print('  ## 汇总')
    print('  %-12s %-5s %-6s %10s %10s %8s %8s %6s' %
          ('arm', 'which', 'step', 'neg', 'overlap', 'dblneg', 'strictbad', 'hard'))
    for r in rows:
        print('  %-12s %-5s %-6d %10d %10d %8d %8d %6d' % r)
    print()
    print('  ⚠ 记账：`band_*` 只存 `|φ_k| ≤ BΔx` 的胞 ⇒ **带外的 φ 不可观测**。')
    print('     M-1 因此是**下界**：真正的重叠可能更多（`φ_k < −BΔx` 的那些看不见）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
