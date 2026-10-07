#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r126_anchor.py —— `§93` 的**文献锚定裁决**（`_r125` 的更正版，并**多测一族**）。

## `_r125` 的错（必须先说清楚）

我照抄了 `_chk_habit5.py:51-60` 的 `H334` 构造：
```python
u = np.array(v)                                   # ← **未归一化**（模 √34）
if not any(abs(u @ w) > 1 - 1e-9 for w in H334):  # ← `w` 是**归一化**的
    H334.append(u / np.linalg.norm(u))
```
`u·w ≤ √34 ≈ 5.83` ⇒ `abs(u@w) > 1-1e-9` **几乎恒真** ⇒ 第一个之后**全被拒**
⇒ 实测 `H334` 只有 **2 个元素**（不是 12）——**`_chk_habit5.py` 也带着同一个 bug**，
所以它的 **H-10（"`n*_inv` 到最近 `{334}` 的夹角"）实际上是在量到**一个**矢量的夹角**，
"判据 < 2°" 那份报告**不成立**。
⇒ **`_chk_habit5.py` 的第二个缺陷**（第一个是 §93 第七节的退化特征空间）。

## 本脚本

正确地生成两个族（**归一化后**用 `|u·w| > 1-1e-9` 去重）：
* `{4 3 3}`（= 文献常写的 `{334}` 等价族）
* `{1 1 0}`（`BLOCK_SELFAC.md §3.4` 说的"6 个 `{110}β` 惯习面"）

**正对照**：族内任一元素 `near = 0.00°`；200 个随机方向的最小 `near` 必须 ≫ 0
（否则说明该族在球面上很密、判据没有分辨力）。
"""
from __future__ import annotations

import itertools
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import windowB_surface as WS                                 # noqa: E402
from T16_verify_rve import EPS0, NPF                        # noqa: E402


def family(hkl):
    """`hkl`（含重复/正负）的全部等价**线**方向，去重后返回 `(n,3)`。"""
    out = []
    for p in set(itertools.permutations(hkl)):
        for s in itertools.product((+1, -1), repeat=3):
            v = np.array([p[i] * s[i] for i in range(3)], float)
            nv = v / np.linalg.norm(v)
            if not any(abs(float(nv @ w)) > 1 - 1e-9 for w in out):
                out.append(nv)
    return np.array(out)


F334 = family((4, 3, 3))
F110 = family((1, 1, 0))
F111 = family((1, 1, 1))


def near(u, F):
    u = np.asarray(u, float)
    u = u / np.linalg.norm(u)
    return float(min(np.degrees(np.arccos(np.clip(abs(float(u @ h)), -1, 1)))
                     for h in F))


def npf(v):
    try:
        return np.asarray(NPF[v], float)
    except (KeyError, IndexError):
        return np.asarray(NPF[v - 1], float)


def axes(v):
    e = np.asarray(EPS0[v - 1], float)
    R = WS.LevelSetMulti._rank1_axes(e, npf(v))
    return (npf(v) / np.linalg.norm(npf(v)),
            np.asarray(R[1], float) / np.linalg.norm(R[1]),
            np.asarray(R[2], float) / np.linalg.norm(R[2]))


def main():
    print('=' * 108)
    print('_r126 —— `NPF` 的文献锚定（`{433}` / `{110}` / `{111}`），`_r125` 的更正版')
    print('=' * 108)
    print('  族大小：`{433}` = **%d**、`{110}` = **%d**、`{111}` = **%d**'
          % (len(F334), len(F110), len(F111)))
    rng = np.random.default_rng(0)
    R = rng.normal(size=(400, 3))
    for lab, F in (('{433}', F334), ('{110}', F110), ('{111}', F111)):
        c1 = near(F[0], F)
        c2 = min(near(r, F) for r in R)
        print('  **正对照 %-6s**：族内元素 near=%.4f°（应 0）；'
              '400 个随机方向的最小 near=%.2f°' % (lab, c1, c2))
    print()
    print('  %-4s %-11s %-11s %-11s | %-11s %-11s %-11s | %s'
          % ('变体', 'n*→{433}', 'a→{433}', 'w→{433}',
             'n*→{110}', 'a→{110}', 'w→{110}', '判定'))
    cnt = {('n*', '433'): 0, ('a', '433'): 0, ('w', '433'): 0,
           ('n*', '110'): 0, ('a', '110'): 0, ('w', '110'): 0,
           ('n*', '111'): 0, ('a', '111'): 0, ('w', '111'): 0}
    rows = []
    for v in range(1, 13):
        n, a, w = axes(v)
        d = (near(n, F334), near(a, F334), near(w, F334),
             near(n, F110), near(a, F110), near(w, F110))
        for key, val in zip((('n*', '433'), ('a', '433'), ('w', '433'),
                             ('n*', '110'), ('a', '110'), ('w', '110')), d):
            if val < 2.0:
                cnt[key] += 1
        for nm, u in (('n*', n), ('a', a), ('w', w)):
            if near(u, F111) < 2.0:
                cnt[(nm, '111')] += 1
        rows.append((v, d))
        best = min((('n*', '433'), d[0]), (('a', '433'), d[1]), (('w', '433'), d[2]),
                   (('n*', '110'), d[3]), (('a', '110'), d[4]), (('w', '110'), d[5]),
                   key=lambda t: t[1])
        print('  V%-3d %-11.2f %-11.2f %-11.2f | %-11.2f %-11.2f %-11.2f | 最近：%s %.2f°'
              % (v, d[0], d[1], d[2], d[3], d[4], d[5], best[0], best[1]))
    print()
    print('  ⇒ `near < 2°` 计数：')
    for fam in ('433', '110', '111'):
        print('     `{%s}`：`n*` %d/12、`a` %d/12、`w` %d/12'
              % (fam, cnt[('n*', fam)], cnt[('a', fam)], cnt[('w', fam)]))
    print()
    print('  ---- 裁决 ----')
    best_fam = max(('433', '110', '111'),
                   key=lambda f: cnt[('n*', f)] + cnt[('a', f)] + cnt[('w', f)])
    tot_n = max(cnt[('n*', f)] for f in ('433', '110', '111'))
    tot_a = max(cnt[('a', f)] for f in ('433', '110', '111'))
    if tot_n >= 10:
        print('  ⇒ ✅ 有 **%d/12** 个 `n*` 落在某个低指数族上 ⇒ `NPF` 与文献惯习面**族一致**'
              % tot_n)
        print('     ⇒ `§93` 的"标签疑似互换"**降级**：`rB` 在少数变体上给出另一个方向，')
        print('       是"`F` 非精确 IPS"下两套最优判据的分歧，**不是数据错**。')
    elif tot_a >= 10 and tot_n <= 2:
        print('  ⇒ ⚠⚠ **`a` 才落在文献族上（%d/12）、`n*` 不落（%d/12）**' % (tot_a, tot_n))
        print('     ⇒ `§93` 的 P0 **成立**（标签确实反了）⇒ 修引擎前**先与用户确认**。')
    else:
        print('  ⇒ ⚠ 没有一族能解释（`n*` 最多 %d/12、`a` 最多 %d/12）⇒ **这条锚不适用**。'
              % (tot_n, tot_a))
        print('     可能原因：`NPF` 是**惯习面的面内法向**（`{110}` 面内的某个方向），')
        print('     或与母相的取向关系用的是另一套约定 ⇒ 需要另找锚（不自行发挥）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
