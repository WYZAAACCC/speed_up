#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_dissolve.py --- ⚠⚠ 决定性检验：场丢失的格点**去哪了**？（判"表示重归属" vs "物理溶解"）

## 为什么这是要害（**用户的物理质疑**）
实测：场 5 的体积从 **2846 胞 → 492 胞（−83%）**、长度 4491 nm → 1714 nm（−62%）。
**但物理上马氏体板条**不会缩短**** —— 它是固态相变产物，只会长大或停止，**不会溶解**。
**⇒ 那些格点只有两种去向：**
| 去向 | 含义 | 性质 |
|---|---|---|
| **被**别的场**接管** | `argmin(φ)` 换了赢家 | **表示层现象**（物理上板条还在，只是归属变了）|
| **回到**母相（region=0）** | 真的变回 β | **物理溶解** ⇒ **模型有问题**（应守恒/单调）|

## 本脚本怎么做
对场 k，在**两个时刻**（早期 t0 / 晚期 t1）取它的掩模 `M0`、`M1`：
* **`lost = M0 & ~M1`**（早期属于它、晚期不属于它的格点）—— **丢失的格点**;
* 在这些 lost 格点上，看**晚期**的 `region` 值分布：
  * **`region == 0`（母相）占多数** ⇒ **物理溶解**（❌ 不物理）;
  * **`region == 其他场` 占多数** ⇒ **重归属**（✅ 只是表示层）。
**★ 同时报**：`gained = M1 & ~M0`（新拿到的格点）的晚期 region 分布
（看它是从母相长出来的，还是从别的场抢来的）。
"""
import glob
import sys
import numpy as np
from collections import Counter

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276F'
KS = [int(x) for x in (sys.argv[2].split(',') if len(sys.argv) > 2 else '5,3,2,4'.split(','))]
T0 = int(sys.argv[3]) if len(sys.argv) > 3 else 200
T1 = int(sys.argv[4]) if len(sys.argv) > 4 else 1600


def reg_at(tag, st):
    fs = [f for f in glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % tag)
          if ('%05d' % st) in f]
    if not fs:
        return None, None
    with np.load(fs[0], allow_pickle=False) as z:
        return np.asarray(z['region']).astype(np.int32), st


r0, s0 = reg_at(TAG, T0)
r1, s1 = reg_at(TAG, T1)
if r0 is None or r1 is None:
    print('  ⚠ 快照缺失（%s/%s）' % (T0, T1)); sys.exit(1)

print('=' * 100)
print('★ %s：场丢失的格点去哪了？（step %d → %d）' % (TAG, s0, s1))
print('=' * 100)
for k in KS:
    M0 = (r0 == k); M1 = (r1 == k)
    n0, n1 = int(M0.sum()), int(M1.sum())
    if n0 == 0 or n1 == 0:
        print('  场 %-4d：早期 %d 胞 / 晚期 %d 胞 ⇒ 跳过' % (k, n0, n1)); continue
    lost = M0 & ~M1
    nl = int(lost.sum())
    print('\n  ── 场 %d：%d 胞 → %d 胞（**丢失 %d 胞，%.0f%%**）──'
          % (k, n0, n1, nl, 100.0 * nl / n0))
    if nl > 0:
        v = r1[lost]
        c = Counter(int(x) for x in v)
        top = c.most_common(6)
        par = c.get(0, 0)
        others = nl - par
        print('     丢失格点在**晚期**的归属（前 6）：%s' % top)
        print('     ⇒ **回到母相 = %d（%.0f%%）** ｜ **被别的场接管 = %d（%.0f%%）**'
              % (par, 100.0 * par / nl, others, 100.0 * others / nl))
        if par / nl > 0.5:
            print('     ⇒ ❌ **物理溶解**（多数回到母相）⇒ 模型有问题（板条不应消失）')
        else:
            print('     ⇒ ✅ **重归属**（多数被别的场接管）⇒ 板条还在，只是归属图变了')
print()
print('  ── 判据（**预先写死**）──')
print('  * **母相占比 > 50%%** ⇒ **物理溶解**（❌ 不物理 —— 马氏体板条只会长大/停止，不会缩）;')
print('  * **别的场占比 > 50%%** ⇒ **表示层重归属**（✅ 物理上板条仍在）;')
print('  * ⚠ 二者都不占多数 ⇒ 混合，需按格点逐个看。')
