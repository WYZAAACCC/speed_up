#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_pairemin.py --- ★ 用**模型真正在最小化的量**给 6 个同 packet 对排序

为什么不用 `γ_el`
-----------------
`_r1_pairgel.py` 报的 `γ_el = E/A` 里，**A 是"键测度"的界面面积**，
对**斜法向**的平面界面它会包含**阶梯面积** ⇒ A 在 6 对之间差 **2 倍**，
而 E 只差 **0.6%** ⇒ **`γ_el` 的差异主要来自阶梯面积这个网格产物**。

**⇒ 模型真正用的量是**：`ncmp[k,l] = argmin_n E(n)`，
其中 `E(n) = 0.5·Δε:Lam(C,n):Δε`（`_argmin_normal` 的目标函数）。
它的**最小值 `E_min`** 才是"这一对的界面有多不相容"的量度 —— 与面积无关。

判据（先写死）
--------------
  M-1 报出 6 个同 packet 对的 `E_min`（单位 J/m³）。
  M-2 判定：若 `E_min(V1,V2) < E_min(V5,V6)` ⇒ **模型自己的能量支持"好/差对照"** ⇒
      `e7c`（用 V5–V6 做负对照）设计成立。
  M-3 **正对照**：`argmin_normal` 的收敛证书 `E_scan/E_min` 必须接近 1（=收敛）。
      若某对的证书很大 ⇒ 该对的法向没收敛，结论作废。
"""
import os
import sys
import itertools

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from windowB_surface import _argmin_normal                     # noqa: E402
from T16_verify_rve import C, EPS0, NV                         # noqa: E402

PAIRS = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)]
E = [np.asarray(e, float) for e in EPS0]

print('=' * 92)
print('用**模型真正在最小化的量** `E_min(ncmp)` 给同 packet 的 6 对排序')
print('=' * 92)
rows = []
for (k, l) in PAIRS:
    de = E[k - 1] - E[l - 1]
    n_p, E_min, cert = _argmin_normal(C, de)
    rows.append((E_min, k, l, cert, n_p))
    print('   V%-2d–V%-2d   **E_min = %.6e J/m³**   收敛证书 E_scan/E_min = %.4f   ncmp = [%+.4f %+.4f %+.4f]'
          % ((k, l) + (E_min, cert) + tuple(n_p)), flush=True)

print('\n★ 按 E_min 升序：')
for E_min, k, l, cert, n_p in sorted(rows):
    tag = ''
    if (k, l) == (1, 2):
        tag = '  ← **e7 用（好对）**'
    if (k, l) == (5, 6):
        tag = '  ← **e7c 负对照（差对）**'
    print('   V%-2d–V%-2d   E_min = %.6e%s' % (k, l, E_min, tag))

d = {p: em for em, k, l, _, _ in rows for p in [(k, l)]}
e12, e56 = d[(1, 2)], d[(5, 6)]
print('\n★ M-2 判定：E_min(V1,V2) = %.6e ； E_min(V5,V6) = %.6e ； 比 = %.3f'
      % (e12, e56, e12 / e56))
if e12 < e56:
    print('   ⇒ ✅ **模型自己的能量支持"好/差对照"** ⇒ `e7c` 设计成立')
else:
    print('   ⇒ ⛔ **相反** ⇒ `e7c` 的"差对"前提不成立，**须撤回**')
badcert = [p for em, k, l, c, _ in rows for p in [(k, l)] if c > 1.05]
print('\n★ M-3 收敛证书：%s'
      % ('✅ 全部 ≤1.05（收敛）' if not badcert else '⚠ 未收敛的对：%s' % badcert))
print('=' * 92)
