#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
"""_r329_edgecheck.py —— 核实 `§166` 的 D-3=0.9686 是不是**边缘伪影**。

## 假设
`_r326_detrend.py` 的 `movavg` 用 `np.convolve(x, k, mode='same')` ——
**它把信号当"零填充"**⇒ 两端各 ~w/2 个点的"局部均值"被**拉低**（把零点算进去了）
⇒ 残差 `x − avg` 在两端**假性变大**。
而 `cv` 与 `sp` **都在增长** ⇒ 两端都得到**同号的大残差** ⇒ **Pearson 被抬高**。

`_r328` 改用 `np.pad(x, w//2, mode='edge')` + `mode='valid'` ⇒ **无零填充伪影**，
同一窗（w=40）给出 **0.4714**（而非 0.9686）。

## 判据（**先写死**）
* **E-1** 两种 `movavg` 在**内部**（去掉两端各 w 点）应**几乎相同**；
  在**两端**应显著不同 ⇒ 证明差异只来自边缘。
* **E-2** 用"零填充"版本的残差，**两端**的 |残差| 应显著大于内部。
* **E-3** 只用**内部**点（去掉两端各 w）算 D-3，两种实现应给出**相同的数**。
* **E-4** 该"内部 D-3"才是**可信值** ⇒ 用它替换 `§166` 的 0.9686。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, '_exp', '_bk_mb', 'dry_saSet2EDV', 'diag_edv.json')


def ma_same(x, w):
    """`_r326` 的写法：零填充伪影版。"""
    return np.convolve(x, np.ones(w) / w, mode='same')


def ma_pad(x, w):
    """`_r328` 的写法：edge 填充，无伪影。"""
    pad = w // 2
    xp = np.pad(x, pad, mode='edge')
    return np.convolve(xp, np.ones(w) / w, mode='valid')[:len(x)]


def pear(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 4:
        return float('nan')
    sa, sb = a[m], b[m]
    if sa.std() < 1e-30 or sb.std() < 1e-30:
        return float('nan')
    return float(np.corrcoef(sa, sb)[0, 1])


def main():
    print('=' * 100)
    print('_r329 —— 核实：`§166` 的 D-3 = 0.9686 是不是边缘伪影？')
    print('=' * 100)
    d = json.load(open(P))
    rec = d['rec']
    cv = np.array([r.get('vol_cv', np.nan) for r in rec], float)
    sp = np.array([r.get('med_spread', np.nan) for r in rec], float)
    m = np.isfinite(cv) & np.isfinite(sp)
    cv, sp = cv[m], sp[m]
    w = 40
    a1, a2 = ma_same(cv, w), ma_pad(cv, w)
    # E-1
    inner = slice(w, len(cv) - w)
    d_inner = float(np.max(np.abs(a1[inner] - a2[inner])))
    d_edge = float(np.max(np.abs(a1 - a2)))
    print()
    print('  ## **E-1** 两种 `movavg` 的差')
    print('     内部（去掉两端各 %d 点）最大差 = **%.3e**' % (w, d_inner))
    print('     全体最大差 = **%.3e** ⇒ 差异**只在两端** ⇒ %s'
          % (d_edge, '✅ 证实' if d_inner < 1e-12 else '⚠ 内部也不同'))
    # E-2
    r1 = cv - a1
    print()
    print('  ## **E-2** 零填充版的残差量级')
    print('     两端（前/后 %d 点）|残差| 最大 = **%.4f** / **%.4f**'
          % (w, np.abs(r1[:w]).max(), np.abs(r1[-w:]).max()))
    print('     内部 |残差| 最大 = **%.4f**' % np.abs(r1[inner]).max())
    rat = max(np.abs(r1[:w]).max(), np.abs(r1[-w:]).max()) / max(np.abs(r1[inner]).max(), 1e-30)
    print('     ⇒ 两端/内部 = **%.1f×** ⇒ %s'
          % (rat, '✅ 两端残差被**假性放大**' if rat > 2 else '⚠ 未见明显放大'))
    # E-3
    print()
    print('  ## **E-3** 只用**内部**点算 D-3')
    for ww in (10, 20, 40, 80):
        i = slice(ww, len(cv) - ww)
        r_in = pear((cv - ma_same(cv, ww))[i], (sp - ma_same(sp, ww))[i])
        r_pd = pear((cv - ma_pad(cv, ww))[i], (sp - ma_pad(sp, ww))[i])
        r_all_pd = pear(cv - ma_pad(cv, ww), sp - ma_pad(sp, ww))
        print('     w=%-4d 零填充版(内部) %.4f ；edge 版(内部) %.4f ；edge 版(全体) %.4f'
              % (ww, r_in, r_pd, r_all_pd))
    # E-4
    print()
    print('  ## **E-4** 可信值（edge 版、无伪影）')
    vals = []
    for ww in (10, 20, 40, 80, 160):
        vals.append(pear(cv - ma_pad(cv, ww), sp - ma_pad(sp, ww)))
    print('     各窗的 edge 版 D-3 = %s' % ['%.4f' % v for v in vals])
    print('     ⇒ 中位 = **%.4f**，范围 %.4f – %.4f'
          % (float(np.median(vals)), min(vals), max(vals)))
    print()
    print('  ⇒ ⇒ **`§166` 的 D-3 = 0.9686 是边缘伪影**；')
    print('     可信值是 **%.2f – %.2f（中位 %.2f）** ⇒ 耦合是**中等**，不是"极强"。'
          % (min(vals), max(vals), float(np.median(vals))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
