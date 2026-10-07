#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_enumchk.py --- `_r1_selfac2.py` 里**核级枚举**逻辑的独立单元自检。

为什么要单独测
--------------
枚举"把标签多重集分给各核的全部不重复方案"是修正量具的**核心**。
它若多算/少算，后面的"排名/精确 p"全错，而且**不会报错**（只是数字不对）。
⇒ 用**已知组合数**做正对照：k 个标签分别有 n_i 个核时的方案数
   必须等于多项式系数 `N! / Π n_i!`。

判据
----
  E-1 3+3 于 6 核 ⇒ 20 = C(6,3)          （**正是 `e7_selfac` / `e7c_badpair` 的工况**）
  E-2 2+2+2 于 6 核 ⇒ 90
  E-3 1+1+1 于 3 核 ⇒ 6 = 3!
  E-4 4+2 于 6 核 ⇒ 15 = C(6,2)
  E-5 所有方案**互不相同**（无重复）
  E-6 每个方案里各标签的核数恒等于多重集（约束不被破坏）
  E-7 观测方案必在枚举集合内（否则排名 undefined）
"""
import itertools
from collections import Counter
from math import factorial


def enum_assign(labels):
    """与 `_r1_selfac2.py` **同一份逻辑**：返回全部不重复的核级指派。"""
    sig = list(range(len(labels)))
    mult = Counter(labels)
    keys = sorted(mult)
    out = []

    def rec(k, remaining, acc):
        if k == len(keys):
            out.append(tuple(acc))
            return
        need = mult[keys[k]]
        for comb in itertools.combinations(sorted(remaining), need):
            cs = set(comb)
            rec(k + 1, [x for x in remaining if x not in cs], acc + [comb])
    rec(0, sig, [])
    cfgs = []
    for acc in out:
        assign = [0] * len(sig)
        for ki, comb in enumerate(acc):
            for p in comb:
                assign[p] = keys[ki]
        cfgs.append(assign)
    return cfgs


def expect(labels):
    """多项式系数 N! / Π n_i!"""
    n = len(labels)
    d = 1
    for c in Counter(labels).values():
        d *= factorial(c)
    return factorial(n) // d


CASES = [
    ([1, 1, 1, 2, 2, 2], '3+3 于 6 核（= e7 两变体臂的工况）'),
    ([1, 1, 2, 2, 3, 3], '2+2+2 于 6 核'),
    ([1, 2, 3], '1+1+1 于 3 核'),
    ([1, 1, 1, 1, 2, 2], '4+2 于 6 核'),
    ([1, 1, 1, 1, 2, 2, 2, 2], '4+4 于 8 核'),
]

print('=' * 92)
print('核级枚举的正对照（方案数必须 = 多项式系数）')
print('=' * 92)
allok = True
for labels, tag in CASES:
    cfgs = enum_assign(labels)
    uniq = len(set(map(tuple, cfgs)))
    exp = expect(labels)
    # E-6：每个方案里各标签核数不变
    ok_counts = all(Counter(c) == Counter(labels) for c in cfgs)
    # E-7：观测方案在集合内
    ok_obs = list(labels) in [list(c) for c in cfgs]
    good = (len(cfgs) == exp) and (uniq == len(cfgs)) and ok_counts and ok_obs
    allok &= good
    print('%-34s 方案数=%-5d 期望=%-5d 去重=%-5d 计数不变=%s 含观测=%s  %s'
          % (tag, len(cfgs), exp, uniq, '✅' if ok_counts else '❌',
             '✅' if ok_obs else '❌', '✅' if good else '⛔'))
print('=' * 92)
print('⇒ %s' % ('✅ 枚举逻辑通过全部正对照' if allok else '⛔ 枚举逻辑有错，不得用于判决'))
print('   注：`e7_selfac` 的 3+3 于 6 核只有 **20** 个方案 ⇒')
print('       由它算出的 `z` 可达上界只有 √(n−1) 量级、实测 **1.792 < 2**')
print('       ⇒ 「z ≤ −2」在该臂上**结构性不可达**（见台账 B-13）。')
print('=' * 92)
