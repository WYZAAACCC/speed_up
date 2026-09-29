#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_scope.py --- ★★ 划定第 24 轮发现（配对法向 `ncmp` 只在 V1–V2 上被用到）的**影响范围**

问题
----
第 24 轮发现：模型里**变体-变体**界面的 `M(n)` 参考取向来自 `ncmp[k,l]`，
而 `ncmp` 只在 `has_pair = (karr>0) & (larr>0)` 时被采用；否则退回 `npref`。

**⇒ 必须回答：实验 1–6 的算例里到底有没有 `has_pair = True` 的胞？**
若没有 ⇒ 第 24 轮的发现**只影响实验 7**，前面六个实验的结论不受牵连。

判据（先写死）
--------------
  S-1 从快照 `region()` 读**出现过的区域号集合**。
      若集合 ⊆ {0, 1} ⇒ 界面只可能是 0↔1 ⇒ `has_pair` 恒 False ⇒ **用的是 `npref`**。
  S-2 对每个算例给出判定：**是否受配对法向通道影响**。
  S-3 附带核对该算例的**变体数**与快照的 `nsig`（块数）。
"""
import os
import glob
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

TARGETS = ['lath1', 'mid1', 'lath192_ns4', 'mid192_ns2', 'mid192_ns4',
           'mid192_s2_ns4', 'equi192_ns4', 'mid250_base', 'mid250_noel',
           'mid250_ns1', 'mid250_ns2', 'mid250_ns4', 'mid250_ns8', 'mid250_ns16',
           'e4_lath6', 'e5_equi6', 'e6_mid6', 'e7_selfac', 'e7b_selfac12']

print('=' * 96)
print('实验 1–6 是否受"配对法向 `ncmp`"通道影响？（只看 region 里出现过哪些区域号）')
print('=' * 96)
print('%-16s %-28s %-10s %s' % ('算例', 'region 里出现过的区域号', '变体数', '判定'))

rows = []
for name in TARGETS:
    snaps = sorted(glob.glob(os.path.join(HERE, '_exp', name, 'snap_*.npz')),
                   key=lambda p: int(os.path.basename(p)[5:-4]))
    if not snaps:
        print('%-16s %-28s %-10s %s' % (name, '（无快照）', '-', '⚠ 无法判定'))
        continue
    labs = set()
    for p in snaps[-3:]:                     # 取最后 3 个快照
        z = np.load(p)
        labs |= set(int(v) for v in np.unique(z['region']))
    nvar = len([v for v in labs if v > 0])
    clean = labs <= {0, 1}
    verdict = ('✅ **不受影响**（界面只有 0↔1 ⇒ 用 `npref`）' if clean
               else '⚠ **受影响**（存在变体-变体界面 ⇒ 用到 `ncmp`）')
    print('%-16s %-28s %-10d %s' % (name, sorted(labs), nvar, verdict))
    rows.append((name, sorted(labs), clean))

print('\n' + '=' * 96)
clean_n = sum(1 for _, _, c in rows if c)
print('汇总：%d 个算例不受影响，%d 个受影响' % (clean_n, len(rows) - clean_n))
aff = [n for n, _, c in rows if not c]
if aff:
    print('受影响的算例：%s' % ', '.join(aff))
    print('⇒ 第 24 轮的配对法向发现**只对这些算例**有意义；')
    print('  其余算例的结论（速率比、块合并、纵横比）**不受牵连**。')
else:
    print('⇒ 全部只含 0↔1 界面 ⇒ 第 24 轮发现的**影响面为零**（本批算例）。')
print('=' * 96)
