#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_stiffunit.py --- **单元级**正对照：`_stiff_of` 在 `facet_lam=0` 与 `0.4` 下是否真的不同？

背景
----
端到端冒烟（`_r1_facetctl.py`）显示 `--facet-lam 0.0` 与 `0.4` 的
`region`、`L_cal`、`W_cal`、`T_cal`、`V` **全部逐位相同**。但端到端有太多环节
（CLI → KW → advance → _geom_k → _stiff_of），**无法定位**是哪一环断了。

本脚本直接调 `_stiff_of`，逐环节查：
  S-0 `NPF` 是什么类型、键是什么（`_stiff_of` 的门是 `npref.get(k) is not None`）；
  S-1 对 k=1 与 k=0 各调一次 `_stiff_of`，比较 `facet_lam=0` vs `0.4` 的输出；
  S-2 若 k=1 不同而 k=0 相同 ⇒ 门在 `npref.get(k)`，且**只对变体场**生效（设计如此）；
  S-3 若 **k=1 也相同** ⇒ cusp 分支根本没进去 ⇒ 继续查（打印每个分支的条件）。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import windowB_surface as W                                            # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                            # noqa: E402

print('=' * 96)
print('S-0 `NPF` 的类型与键')
print('   type(NPF) = %s' % type(NPF))
try:
    ks = sorted(NPF.keys())
    print('   键 = %s （共 %d 个）' % (ks, len(ks)))
    print('   `NPF.get(0)` = %s' % ('None' if NPF.get(0) is None else '有值'))
    print('   `NPF.get(1)` = %s' % ('None' if NPF.get(1) is None else '有值'))
except AttributeError:
    print('   ⚠ `NPF` 没有 `.keys()` ⇒ 它是 %s，而 `_stiff_of` 里用的是 `npref.get(k)`'
          % type(NPF))

# 造一个小引擎
g = W.LevelSetMulti(24, 24 * 125e-9, C=C, eps0=EPS0, gamma=0.15,
                    Mob=1.0, df=[0.0] * (NV + 1), workers=1)
# 造一个非平凡的 φ（球）以便有非零梯度
X, Y, Z = np.meshgrid(*[np.arange(24) for _ in range(3)], indexing='ij')
c = 12.0
r = np.sqrt((X - c) ** 2 + (Y - c) ** 2 + (Z - c) ** 2)
g.phi[1] = r - 6.0
grad = g.par.gradient(g.phi[1], g.dx, edge_order=2)
gn = np.sqrt(sum(gi ** 2 for gi in grad)) + 1e-30

print('\nS-1/S-2 `_stiff_of` 逐档对照（同一输入场）')
out = {}
for k in (0, 1):
    for fl in (0.0, 0.4):
        try:
            v = g._stiff_of(k, grad, gn, NPF, 0.4, None, True, fl, 0.05)
            v = np.asarray(v, float)
            out[(k, fl)] = v
            print('   k=%d facet_lam=%.1f ⇒ shape=%s  min=%.6f max=%.6f mean=%.6f'
                  % (k, fl, v.shape, np.nanmin(v), np.nanmax(v), np.nanmean(v)))
        except Exception as e:                                       # noqa: BLE001
            print('   k=%d facet_lam=%.1f ⇒ ⛔ 抛错：%s: %s'
                  % (k, fl, type(e).__name__, e))

print('\nS-3 判读')
for k in (0, 1):
    a, b = out.get((k, 0.0)), out.get((k, 0.4))
    if a is None or b is None:
        continue
    same = np.array_equal(a, b)
    rel = float(np.nanmax(np.abs(a - b) / np.maximum(np.abs(a), 1e-300)))
    print('   k=%d ：逐位相同？ %s ；最大相对差 %.3e  ⇒ %s'
          % (k, '是' if same else '**否**', rel,
             '⛔ cusp 分支没生效' if same else '✅ **cusp 分支生效**'))
print('=' * 96)
