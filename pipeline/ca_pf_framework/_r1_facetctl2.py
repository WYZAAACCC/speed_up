#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_facetctl2.py --- 用**连续量**（而非离散的 `region` 标签）复查 `facet_lam` 是否生效。

为什么需要
----------
`_r1_facetctl.py` 用快照里的 `region`（= `argmin_k φ_k`，**离散标签场**）做对照，
结果两档**逐位相同**。但这**不足以**判定"参数没生效"：
  * `region` 是离散量 ⇒ 刚度的小变化在 6 步内可能**一个标签都没翻** ⇒ 观察不到；
  * 快照里可能**没有** `phi`（连续场）。
⇒ 必须换**连续、敏感**的观察量：
  * `series.csv` 的 `L_cal`/`W_cal`/`T_cal`（浮点，逐位可比较）；
  * 快照里可用的所有键（先列出 `npz.files`）。
"""
import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ARMS = [('facet_lam=0.0', '_facetctl_00'), ('facet_lam=0.4', '_facetctl_04'),
        ('facet_lam=0.4(重跑)', '_facetctl_04b')]

print('=' * 96)
print('① 快照里到底存了哪些键（决定能用什么做对照）')
for tag, d in ARMS:
    p = os.path.join(HERE, '_exp', d)
    if not os.path.isdir(p):
        print('   %-20s 目录不存在' % tag); continue
    sn = sorted(f for f in os.listdir(p) if f.endswith('.npz'))
    if not sn:
        print('   %-20s 无快照' % tag); continue
    z = np.load(os.path.join(p, sn[-1]))
    print('   %-20s %s  keys=%s' % (tag, sn[-1], list(z.files)))
print()
print('=' * 96)
print('② 连续量对照：`series.csv` 的 `L_cal`/`W_cal`/`T_cal`（浮点全精度）')
data = {}
for tag, d in ARMS:
    p = os.path.join(HERE, '_exp', d, 'series.csv')
    if not os.path.exists(p):
        print('   %-20s 无 series.csv' % tag); continue
    rows = list(csv.DictReader(open(p)))
    data[tag] = rows
    print('   %-20s 行数=%d' % (tag, len(rows)))
if len(data) >= 2:
    tags = list(data)
    a, b = data[tags[0]], data[tags[1]]
    n = min(len(a), len(b))
    for col in ('L_cal', 'W_cal', 'T_cal', 'V', 'LW_cal'):
        try:
            va = np.array([float(a[i][col]) for i in range(n)])
            vb = np.array([float(b[i][col]) for i in range(n)])
        except (ValueError, KeyError):
            print('   %-10s （列不可用）' % col); continue
        bit = np.array_equal(va, vb)
        rel = float(np.max(np.abs(va - vb) / np.maximum(np.abs(va), 1e-300)))
        print('   %-10s %-18s max相对差 = %.3e' % (col, tags[0] + ' vs ' + tags[1], rel))
        if col == 'L_cal':
            print('        ⇒ %s' % ('⛔ **逐位相同**' if bit else
                                    '✅ **不同 ⇒ 参数生效**'))
print('=' * 96)
print('判读（**已由 `_r1_stiffunit.py` 定案，勿按本脚本的初判下结论**）：')
print('  * 本脚本测到**连续量也逐位相同**。但**这仍不足以**说参数没生效 ——')
print('    真正的分诊在 `_r1_stiffunit.py`：它**直接调 `_stiff_of`**，')
print('    k=1 时 facet_lam 0.0→0.4 让刚度从 0.090–0.270 变成 **0.150–1.349**（4 倍）')
print('    ⇒ ✅ **cusp 分支生效**。')
print('  * 本脚本看不见效果的原因是**功效不足**（教训 14「先问这个测试能不能看到目标现象」）：')
print('    `stk·κ/Δf` 在 R=750 nm 的种子上只有 **0.2%**（cusp 后 ~1.8%），')
print('    6 步位移 ~112 nm ⇒ 1.8% = **2 nm，远小于 1 个胞**，而所有读数量都是**胞量化**的。')
print('  ⇒ 正确的 A-3 对照必须用**薄板 + 长跑 + 非量化观察量**（`fill_cal`/长时程 aspect）。')
print('=' * 96)
