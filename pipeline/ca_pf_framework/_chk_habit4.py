#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_habit4.py --- 定案：`n*` 该取哪一个 rank-1 解？

已知（`_chk_habit2/3` 实测）
---------------------------
* `E(n) = 0.5·eps:Lam(C,n):eps` 的**精修全局最小**对 12 个变体全 = **5.869e3 J/m³**
  （≈0 ⇒ 这就是**不变平面法向**：该法向的板条自能为零）。
* `NPF`（`T16`/探针用的 400 随机 argmin）的能量是全局最小的 **21–654 倍** ⇒ **没收敛**。
* 精修最优点离引擎 rank-1 的 `a` 为 **0.04°**（5 个变体）/ 离 `n` 为 **0.04°**（另 7 个）。
* ⚠ `_chk_habit3` 里"离 `n_eng` 7.29°"是**我自己代理量的伪影**：
  `w × a = (n·a)a − n`，当 `n·a = trace(eps) = 0.127` 时它离真 `n` 恰好
  `arccos(√(1−0.127²)) = 7.29°`。**不是引擎错。**

本探针要回答的**唯一问题**
------------------------
`_rank1_axes` 返回两个解（`n₊ = e1 + r e3` / `n₋ = e1 − r e3`），
**哪一个的 `n` 是不变平面法向**（= 板条厚向 `n*`）？

判据：**`n` 必须满足 `n·eps = 0`**（不变平面的定义：该平面内的向量不被拉伸）。
      两个解的 `n·a` 都 = `trace(eps)`，但 `n·eps` 只有一个为 0
      （`eps·n = 0.5·a(n·n) + 0.5·n(a·n) = 0.5a + 0.5·trace(eps)·n`）。
⇒ **H-8：`|eps·n|` 最小的那一个解才是 `n*`。** 这是解析判据，不依赖任何搜索。

用法：python3 _chk_habit4.py
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)


def Efun(eps, n):
    return 0.5 * float(np.einsum('ij,ijkl,kl->', eps, _lam_full(C, n), eps))


def two_solutions(eps, nref):
    w_, V = np.linalg.eigh(np.asarray(eps, float))
    o = np.argsort(w_)[::-1]
    w_, V = w_[o], V[:, o]
    mu1, mu3 = w_[0], w_[2]
    e1, e3 = V[:, 0], V[:, 2]
    r = np.sqrt(-mu3 / mu1)
    out = []
    for sgn in (+1.0, -1.0):
        n = e1 + sgn * r * e3
        n = n / np.linalg.norm(n)
        a = mu1 * e1 - sgn * np.sqrt(-mu1 * mu3) * e3
        a = a / np.linalg.norm(a)
        out.append((n, a))
    return out


print('=' * 100)
print('_chk_habit4 —— 哪个 rank-1 解是不变平面法向（判据：`|eps·n|` 最小）')
print('=' * 100)
print('  %-4s | %-11s %-11s | %-11s %-11s | %-11s %-11s | %s' %
      ('变体', '|eps·n₊|', '|eps·n₋|', 'E(n₊)', 'E(n₋)', 'E(a₊)', 'E(a₋)',
       'n* = 哪个解'))
cnt = {1: 0, 2: 0}
for k in range(1, NV + 1):
    eps = np.asarray(EPS0[k - 1], float)
    (n1, a1), (n2, a2) = two_solutions(eps, None)
    r1 = float(np.linalg.norm(eps @ n1))
    r2 = float(np.linalg.norm(eps @ n2))
    E1, E2 = Efun(eps, n1), Efun(eps, n2)
    Ea1, Ea2 = Efun(eps, a1), Efun(eps, a2)
    pick = 1 if r1 < r2 else 2
    cnt[pick] += 1
    print('  %-4d | %11.3e %11.3e | %11.3e %11.3e | %11.3e %11.3e | 解%d'
          % (k, r1, r2, E1, E2, Ea1, Ea2, pick))

print('\n  ⇒ H-8：按 `|eps·n|` 判，解1 当选 %d 次、解2 当选 %d 次（共 12）'
      % (cnt[1], cnt[2]))
print('     若两个解的 `|eps·n|` **都** ≈0 ⇒ 判据无分辨力，须换判据（见下）；')
print('     若 `E(n*)` ≈ 5.869e3（本会话已实测的精修全局最小）⇒ 判据与能量一致 ✓')
print('=' * 100)
