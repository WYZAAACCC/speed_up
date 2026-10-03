#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_cut.py --- ★★★★★★ 定位"一场多块"的**确切来源**：切掉的胞变成了什么？

## 为什么查这一步
场 2 的 φ<0 分量数：**1（step 120）→ 3（step 160）**（一次跃变）。
而 step 101 有 **3 个 `attach` 事件**（场 4, 5, 6）。
**⇒ 判据（二分）：**
| 被切掉的胞在 step 160 的状态 | 结论 |
|---|---|
| **属于某个**新场**（step 101 播的 4/5/6）** | **① `attach` 的种子**压穿/切断**了源场** ⇒ 播种几何问题 |
| **不属于任何场（φ≥0 ⇒ 母相）** | **② 连续回退**（动力学把相推回母相）⇒ 演化方程问题 |
| **属于别的**老场**（2–3 之外的）** | **③ 场间竞争**（`argmin` 转移 + 回退）|

## 做法
1. 取场 2 在 step 120 与 160 的 φ<0 掩模 `M120`、`M160`;
2. `lost = M120 & ~M160`（被切掉的胞）;
3. 在 step 160 上查这些 lost 胞的归属：
   * **哪个场在那里 φ<0**（⇒ 被谁拿走）;
   * **或没有任何场 φ<0**（⇒ 变回母相）。
"""
import glob
import sys
import numpy as np
from collections import Counter

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276F'
K = int(sys.argv[2]) if len(sys.argv) > 2 else 2
SA = int(sys.argv[3]) if len(sys.argv) > 3 else 120
SB = int(sys.argv[4]) if len(sys.argv) > 4 else 160


def load(st):
    fs = [f for f in glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG) if ('%05d' % st) in f]
    if not fs:
        return None
    with np.load(fs[0], allow_pickle=False) as z:
        N = int(np.asarray(z['N']))
        bi = np.asarray(z['band_idx']).ravel().astype(np.int64)
        bv = np.asarray(z['band_val']).ravel()
        bf = np.asarray(z['band_fld']).ravel()
    flat = (bi // (N * N)) * (N * N) + ((bi // N) % N) * N + (bi % N)
    return N, flat, bv, bf


def mask_k(N, flat, bv, bf, k):
    g = np.zeros(N ** 3, bool)
    g[flat[(bf == k) & (bv < 0)]] = True
    return g


def owner_map(N, flat, bv, bf):
    """每个胞 → 拥有它的场（取 φ 最负的那个）"""
    own = np.zeros(N ** 3, np.int32)
    best = np.full(N ** 3, 1e30)
    neg = bv < 0
    for k in np.unique(bf[neg]):
        k = int(k)
        if k == 0:
            continue
        sel = neg & (bf == k)
        c = flat[sel]; v = bv[sel]
        m = v < best[c]
        own[c[m]] = k
        best[c[m]] = v[m]
    return own


A = load(SA); B = load(SB)
if A is None or B is None:
    print('  ⚠ 快照缺失'); sys.exit(1)
N = A[0]
M_A = mask_k(N, A[1], A[2], A[3], K)
M_B = mask_k(N, B[1], B[2], B[3], K)
own_B = owner_map(N, B[1], B[2], B[3])
print('=' * 96)
print('★ %s：场 %d 的切块来源（step %d → %d）' % (TAG, K, SA, SB))
print('=' * 96)
print('  场 %d 的 φ<0 体积：step %d = **%d** 胞 ｜ step %d = **%d** 胞'
      % (K, SA, int(M_A.sum()), SB, int(M_B.sum())))
lost = M_A & ~M_B
nl = int(lost.sum())
print('  **被切掉的胞 = %d**' % nl)
if nl:
    o = own_B[lost]
    c = Counter(int(x) for x in o)
    print()
    print('  被切掉的胞在 step %d 的归属（前 10）：' % SB)
    for kk, n in c.most_common(10):
        tag = ('**母相（无任何场 φ<0）**' if kk == 0 else '场 %d' % kk)
        print('     %-28s %6d 胞（%.1f%%）' % (tag, n, 100.0 * n / nl))
    print()
    par = c.get(0, 0)
    newf = sum(n for kk, n in c.items() if kk in (4, 5, 6))
    print('  ── 判据（**预先写死**）──')
    print('     变回**母相** = %d（**%.0f%%**）' % (par, 100.0 * par / nl))
    print('     被 step 101 新播的场（4/5/6）拿走 = %d（**%.0f%%**）'
          % (newf, 100.0 * newf / nl))
    print('     被其他场拿走 = %d' % (nl - par - newf))
    print()
    if par > nl * 0.5:
        print('  ⇒ **② 连续回退**为主：被切掉的胞**变回了母相** ⇒ 问题在**演化方程**。')
    elif newf > nl * 0.5:
        print('  ⇒ **① `attach` 的种子压穿/切断源场**为主 ⇒ 问题在**播种几何**。')
    else:
        print('  ⇒ **③ 场间竞争/混合** ⇒ 需按胞逐个看。')
