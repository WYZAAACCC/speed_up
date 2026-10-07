#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r89_npfchk.py —— **`NPF`（惯习面法向表）与 `EPS0`（转变应变）的自洽性检查**。

## 为什么（**P1-40 的追查**）

`_r88_sextuple.py` 用**纯组合**方法（只吃 `EPS0`）定出：64 个自协调六元组
**唯一地**对应一个完美匹配

    配对 = (1,2) (3,4) (5,6) (7,8) (9,10) (11,12)

而 `BLOCK_SELFAC.md §3.4` 说这 6 对就是「**同 `{110}β` 惯习面**」的两个变体
（面内 60° 旋转对，`r = 0.996`）—— 与 `EPS0` 的 `r_pair = 0.9958` **完全吻合** ✅。

**但** `_r78_pairselfac.py` 表 4 用 `NPF`（`T16_verify_rve` 的惯习面法向）
按 `|cos| ≥ 1−1e-6` 分组，得到的是 **12 组各 1 个**；而且 6 对里有 3 对
（`(5,6)`、`(9,10)`、`(11,12)`）的 `NPF` 夹角是 **88°**，不是 ~0°/180°。

⇒ 两者必有一处不对。本脚本用**晶体学判据**直接判定 `NPF` 对不对：

    不变平面（惯习面）法向 `n` 的定义：**`F` 保持该平面的法向不变**，
    即 @@F^{\\mathsf T}n=\\lambda n@@ 且 **`λ = 1`**
    （等价：`n` 不被拉伸。对 IPS `F = I + ½(a nᵀ + n aᵀ)` 可验证 `Fᵀn = n`。）
    ——与 `_chk_habit5.py` 同一判据。

对每个变体 `v`：`F = I + eps0[v−1]`，算 `Fᵀ` 的左特征向量，取 `|λ−1|` 最小者，
与 `NPF[v]` 比夹角。**12/12 都该 ≈ 0°**（在 `n` 的定义下）。

## 与"对"的关系

两个变体 `k,l` 若**共享**惯习面，则它们各自的不变平面法向应满足 `|n_k·n_l| ≈ 1`。
`EPS0` 的配对结构说共享的是上面那 6 对 ⇒ 逐对检查。
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from T16_verify_rve import EPS0, NPF                         # noqa: E402

# `_r88` 用纯组合（只吃 EPS0）定出的**唯一**完美匹配
PAIRS = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)]


def npf(v):
    try:
        a = np.asarray(NPF[v], float)
    except (KeyError, IndexError):
        a = np.asarray(NPF[v - 1], float)
    return a / np.linalg.norm(a)


def unit(x):
    x = np.asarray(x, float)
    return x / (np.linalg.norm(x) + 1e-300)


def angle(u, v):
    return float(np.degrees(np.arccos(np.clip(abs(float(unit(u) @ unit(v))), -1, 1))))


def main():
    print('=' * 108)
    print('_r89_npfchk —— `NPF` vs `Fᵀn = n`（不变平面法向的定义）')
    print('=' * 108)
    print('  %-4s %-10s %-12s %-34s %-10s %s'
          % ('变体', '最小|λ-1|', 'λ 最小时的角度', 'NPF[v] 与解析不变平面法向的夹角',
             'NPF 模', '判定'))
    worst = 0.0
    for v in range(1, 13):
        F = np.eye(3) + np.asarray(EPS0[v - 1], float)
        ev, evec = np.linalg.eig(F.T)                # Fᵀ n = λ n
        ev = np.real(ev)
        evec = np.real(evec)
        i = int(np.argmin(np.abs(ev - 1.0)))
        n_an = unit(evec[:, i])
        dl = float(abs(ev[i] - 1.0))
        ang_l = angle(n_an, npf(v))
        ok = ang_l < 1.0
        worst = max(worst, ang_l)
        print('  V%-3d %-10.2e %-12s %-34.2f %-10.4f %s'
              % (v, dl, '%.4f' % ev[i], ang_l, float(np.linalg.norm(npf(v))),
                 '✅' if ok else '❌ **不符**'))
    print()
    print('  ⇒ **最大夹角 = %.2f°**' % worst)
    if worst < 1.0:
        print('     ⇒ `NPF` **逐变体**都是正确的解析不变平面法向 ✅')
        print('     ⇒ 那么问题只可能在"哪些对共享惯习面"这一层（见下）。')
    else:
        print('     ⇒ ⚠⚠ `NPF` 与解析不变平面法向**不一致** ⇒ 表本身有问题。')

    # ---- 对级：共享惯习面？ ----
    print()
    print('=' * 108)
    print('  对级：`EPS0` 的组合配对 vs `NPF` 的夹角（共享惯习面 ⇒ |n_k·n_l| ≈ 1）')
    print('=' * 108)
    print('  %-10s %-12s %-12s %-10s %s'
          % ('对（EPS0）', '|n_k·n_l|', '夹角(°)', 'r_pair', '共享惯习面？'))
    E = [np.asarray(e, float) - np.trace(e) / 3.0 * np.eye(3) for e in EPS0]
    scale = float(np.mean([np.linalg.norm(e) for e in E]))
    nshare = 0
    for a, b in PAIRS:
        ca = float(npf(a) @ npf(b))
        rp = (float(np.linalg.norm(E[a - 1] + E[b - 1]))
              / (np.linalg.norm(E[a - 1]) + np.linalg.norm(E[b - 1])))
        sh = abs(abs(ca) - 1.0) < 1e-3
        nshare += int(sh)
        print('  (%2d,%2d)     %+-12.4f %-12.2f %-10.4f %s'
              % (a, b, ca, angle(npf(a), npf(b)), rp,
                 '✅ 是' if sh else '❌ **不是**'))
    print()
    print('  ⇒ %d/6 对在 `NPF` 下共享惯习面。' % nshare)
    if nshare < 6:
        print('     ⚠ **P1-40 成立**：`EPS0` 的组合配对（唯一解，且 `r_pair` 全为 0.9958）')
        print('       与 `NPF` 的晶体学配对**不一致** ⇒ 两张表里至少有一张是错的。')
        print('       （`NPF` 逐变体单独看是对的 ⇒ 嫌疑落在"变体编号的对应关系"上：')
        print('         `EPS0[i]` 与 `NPF[i]` 可能不是同一个变体。）')
    print()
    print('  参考：全部 66 对的 `NPF` 夹角分布（看有没有 6 对扎堆在 0°/180°）')
    angs = []
    for i in range(1, 13):
        for j in range(i + 1, 13):
            angs.append((angle(npf(i), npf(j)), i, j))
    angs.sort()
    for a, i, j in angs[:8]:
        print('     (%2d,%2d)  %6.2f°' % (i, j, a))
    return 0


if __name__ == '__main__':
    sys.exit(main())
