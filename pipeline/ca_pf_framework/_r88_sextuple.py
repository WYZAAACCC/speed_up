#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r88_sextuple.py —— **复核 `BLOCK_SELFAC.md §3.2` 的"64 个自协调六元组"结构**。

## 文档的断言（`BLOCK_SELFAC.md:151-152`）

> ★★ **64 个自协调六元组的结构恰好是「6 个 `{110}β` 惯习面各取一个变体」**
> （`2^6 = 64`，**实测吻合**；"每个惯习面各取正好一个"对全部 64 个成立 ✅）。

**`2^6 = 64` 这个数只有在"12 个变体可以分成 6 对、每对取一个"时才成立。**
但 `_r78_pairselfac.py` 表 4 用 `NPF`（`T16_verify_rve` 的惯习面法向）
按 `|cos| ≥ 1−1e-6` 分组，得到的是 **12 组各 1 个**，不是 6 组各 2 个。

⇒ 两者必有一处不对。本脚本**不靠 `NPF`**，直接从**组合结构本身**判定：
   是否存在一个**完美匹配**（12 个变体分成 6 对），使得
   **每一个自协调六元组恰好从每对里取一个**。
   若存在 ⇒ §3.2 的结构断言**成立**（且给出这 6 对是谁）；
   若不存在 ⇒ §3.2 的"每个惯习面各取一个"**表述有误**（`k*=6` 与"64 个"仍成立）。

⚠ 这是纯粹的**组合验证**，只吃 `EPS0`，**与 `NPF` 的解释无关** ⇒ 能把
   "应变侧的数学"与"惯习面的晶体学解释"两件事**分开**判。
"""
from __future__ import annotations

import itertools
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _r78_pairselfac as R78                               # noqa: E402
from T16_verify_rve import EPS0, NPF                        # noqa: E402

TOL = 1e-6


def matchings(items):
    """枚举 `items` 的**所有完美匹配**（两两配对，与对内顺序、对间顺序无关）。"""
    items = list(items)
    if not items:
        yield []
        return
    a = items[0]
    for i in range(1, len(items)):
        b = items[i]
        rest = items[1:i] + items[i + 1:]
        for m in matchings(rest):
            yield [(a, b)] + m


def main():
    E = [e - np.trace(e) / 3.0 * np.eye(3) for e in EPS0]
    VEC = np.array([e.reshape(-1) for e in E])
    scale = float(np.mean([np.linalg.norm(e) for e in E]))
    print('=' * 104)
    print('_r88_sextuple —— 复核「64 个自协调六元组 = 6 对里各取一个」')
    print('=' * 104)
    # ---- 穷举 924 个六元组 ----
    zero = []
    for G in itertools.combinations(range(12), 6):
        if R78._simplex_r(VEC[list(G)], scale) < TOL:
            zero.append(frozenset(i + 1 for i in G))
    print('  `r_min < %.0e` 的六元组个数 = **%d**（文档断言 64）  ⇒ %s'
          % (TOL, len(zero), '✅' if len(zero) == 64 else '**不符**'))
    zset = set(zero)
    # ---- 找完美匹配：每个六元组恰好从每对取一个 ----
    found = []
    for m in matchings(list(range(1, 13))):
        ok = True
        for G in zero:
            if any((a in G) == (b in G) for a, b in m):
                ok = False
                break
        if ok:
            found.append(m)
    print()
    print('  满足「每个自协调六元组恰好从每对取一个」的**完美匹配**个数：**%d**'
          % len(found))
    for m in found[:6]:
        print('     配对：%s' % '  '.join('(%d,%d)' % p for p in m))
    print()
    if found:
        print('  ⇒ **§3.2 的结构断言成立**（在组合意义下）：12 个变体确可分成 6 对，')
        print('     每个自协调六元组恰好每对取一个 ⇒ `2^6 = 64` 解释得通。')
    else:
        print('  ⇒ ⚠⚠ **找不到这样的匹配** ⇒ §3.2 的「6 个惯习面各取一个」**表述有误**。')
        print('     （`k* = 6` 与"恰好 64 个"本身仍成立 —— 那两条已被 `_r78` 独立复现。）')
    # ---- 与 `NPF` 分组对照 ----
    print()
    print('  ---- 与 `NPF`（惯习面法向）的分组对照 ----')
    nrml, grp = [], {}
    for v in range(1, 13):
        nv = np.asarray(NPF[v], float)
        nv = nv / np.linalg.norm(nv)
        hit = None
        for gi, u in enumerate(nrml):
            if abs(abs(float(nv @ u)) - 1.0) < 1e-6:
                hit = gi
                break
        if hit is None:
            nrml.append(nv)
            hit = len(nrml) - 1
        grp.setdefault(hit, []).append(v)
    print('  `NPF` 按 `|cos| ≥ 1−1e-6` 分组：%d 组 → %s'
          % (len(nrml), '   '.join(str(sorted(g)) for g in grp.values())))
    if found:
        m0 = sorted(tuple(sorted(p)) for p in found[0])
        npf_pairs = sorted(tuple(sorted(g)) for g in grp.values() if len(g) == 2)
        print('  组合匹配给出的 6 对：%s' % (m0,))
        print('  `NPF` 给出的 2 元组：%s' % (npf_pairs,))
        for a, b in m0:
            nv = np.asarray(NPF[a], float); nv /= np.linalg.norm(nv)
            nw = np.asarray(NPF[b], float); nw /= np.linalg.norm(nw)
            print('     (%d,%d)：`n*·n*` = %+.4f  ⇒ 夹角 %6.2f°（|cos| 口径）'
                  % (a, b, float(nv @ nw),
                     np.degrees(np.arccos(np.clip(abs(float(nv @ nw)), -1, 1)))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
