#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r326_detrend.py —— ⚠ **关键控制**：`vol_cv` 与 `ed` 极差的 r=0.996 是**真耦合**还是**共同随时间上升**？

## 为什么必须做（硬规则 ⑨ 的同类：先问判据在退化输入上给什么）
两个量**都随时间单调上升**时，Pearson **天然**接近 1 —— **这是伪相关**。
⇒ 必须**去掉趋势**再看。

## 三种口径（**先写死**）
* **D-1 原始** Pearson（预期高 ⇒ 但**说明不了耦合**）。
* **D-2 一阶差分**上的 Pearson（`Δvol_cv` vs `Δed`）⇒ **去掉趋势后的耦合**。
* **D-3 去平滑趋势后的残差** Pearson（用移动平均当趋势）。
* **D-4** 负对照：把 `ed` 序列**循环平移 100 步**（破坏同步、保留各自的趋势）
  ⇒ 若 D-2 仍高而 D-4 低 ⇒ 耦合是真的。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, '_exp', '_bk_mb', 'dry_saSet2EDV', 'diag_edv.json')


def pear(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 4:
        return float('nan'), 0
    return float(np.corrcoef(a[m], b[m])[0, 1]), int(m.sum())


def movavg(x, w):
    k = np.ones(w) / w
    return np.convolve(x, k, mode='same')


def main():
    print('=' * 100)
    print('_r326 —— ⚠ 控制检验：`vol_cv` 与 `ed` 的相关是不是"共同随时间上升"的伪相关？')
    print('=' * 100)
    d = json.load(open(P))
    rec = d['rec']
    st = np.array([r['step'] for r in rec], float)
    cv = np.array([r.get('vol_cv', np.nan) for r in rec], float)
    sp = np.array([r.get('med_spread', np.nan) for r in rec], float)
    m = np.isfinite(cv) & np.isfinite(sp)
    cv, sp, st = cv[m], sp[m], st[m]
    print('  有效点 %d（step %d … %d）' % (len(cv), st[0], st[-1]))
    print()
    r1, n1 = pear(cv, sp)
    print('  ## **D-1 原始** Pearson = **%.4f**（%d 点）' % (r1, n1))
    print('     ⚠ 两个量**都单调上升** ⇒ 这个数**高是必然的**，说明不了耦合。')
    print()
    dcv, dsp = np.diff(cv), np.diff(sp)
    r2, n2 = pear(dcv, dsp)
    print('  ## **D-2 一阶差分**（去掉趋势）Pearson = **%.4f**（%d 点）' % (r2, n2))
    print('     ⇒ %s' % ('**仍有强耦合**（不是纯伪相关）' if abs(r2) > 0.5 else
                         '**趋势去掉后耦合很弱** ⇒ 原相关主要是"共同随时间上升"'))
    print()
    w = max(21, len(cv) // 10)
    rcv = cv - movavg(cv, w)
    rsp = sp - movavg(sp, w)
    r3, n3 = pear(rcv, rsp)
    print('  ## **D-3 去平滑趋势残差**（窗 %d）Pearson = **%.4f**' % (w, r3))
    print()
    sh = 100
    r4, n4 = pear(cv, np.roll(sp, sh))
    print('  ## **D-4 负对照**：把 `ed` 极差**循环平移 %d 步** ⇒ Pearson = **%.4f**' % (sh, r4))
    print('     ⇒ 平移破坏同步后应**显著下降**（趋势还在，但时序对不上）。')
    print()
    print('  ## 判定')
    if abs(r2) > 0.5 and abs(r4) < abs(r2):
        print('     ⇒ ✅ **D-2 高、D-4 低** ⇒ 二者的**同步变化**是真的（不只是趋势）')
        print('        ⇒ 支持"体积分化与弹性不均匀性**互相喂养**"的**正反馈**图像。')
    elif abs(r2) <= 0.5:
        print('     ⇒ ⚠ **D-2 弱** ⇒ 原始 r=%.3f **主要是共同趋势**（伪相关）' % r1)
        print('        ⇒ **不能**说二者"互相喂养"；只能说"两者都在随时间增长"。')
    else:
        print('     ⇒ ⚠ 方向不明确（D-2=%.3f，D-4=%.3f）⇒ 如实记录' % (r2, r4))
    print()
    print('  ⚠ 记账：一阶差分对**逐点噪声**敏感（本数据是**每步**记录，400 点）。')
    print('     若噪声占比大，D-2 会**偏低** ⇒ 此时以 D-3（去平滑趋势）为准。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
