#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_svcheck.py --- 补一个数：同 packet 对的 ΔU **奇异值谱**。

`_r1_paircorr.py` 测到：6 个同 packet 对的 `σ₂/σ₁ = 1.0000000000`（10 位）。
这说明它们 **rank ≥ 2**。但"是不是 rank-1"要三个奇异值一起看，
所以这里把 `σ₁ σ₂ σ₃`（及 `σ₃/σ₁`）打出来。

科学含义
--------
经典马氏体晶体学（Hadamard 跳跃条件）要求两变体的 `ΔF = F_j − F_i`
是 **rank-1**（`det ΔF = 0`）才存在**不变平面**（无应力）界面。
如果同 packet 对的 `σ₂/σ₁ = 1` 且 `σ₃/σ₁` 不小，则**经典判据直接否掉它们**；
而本模型给 V5–V6 的 `E_min = 4.19e-04` 却是全 66 对里**最小**的。
⇒ 本模型的"最相容"与经典几何的"最相容"是**两回事**。
"""
import os
import sys
import itertools

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from T16_verify_rve import EPS0, NV                                   # noqa: E402

E = [np.asarray(e, float) for e in EPS0]


def sv3(dU):
    s = np.linalg.svd(dU, compute_uv=False)
    return float(s[0]), float(s[1]), float(s[2])


print('=' * 88)
print('同 packet 6 对的 ΔU 奇异值谱（`EPS0` 来自 T16_verify_rve）')
print('=' * 88)
print('   %-10s %12s %12s %12s %10s %10s   %s'
      % ('对', 'σ₁', 'σ₂', 'σ₃', 'σ₂/σ₁', 'σ₃/σ₁', '判定'))
SAME = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)]
for k, l in SAME:
    s1, s2, s3 = sv3(E[k - 1] - E[l - 1])
    if s3 / s1 < 1e-8:
        verdict = 'rank-1 ✅'
    elif s2 / s1 > 0.99:
        verdict = 'rank-2 ❌ 非 rank-1'
    else:
        verdict = 'rank-3 ❌ 非 rank-1'
    print('   V%-2d–V%-2d %12.6f %12.6f %12.6f %10.6f %10.6f   %s'
          % (k, l, s1, s2, s3, s2 / s1, s3 / s1, verdict))

# 全 66 对里有没有一对真的是 rank-1？
print('\n全 66 对里 `σ₃/σ₁ < 1e-6`（真 rank-1）的对：')
hit = [(k, l) for k, l in itertools.combinations(range(1, NV + 1), 2)
       if sv3(E[k - 1] - E[l - 1])[2] / sv3(E[k - 1] - E[l - 1])[0] < 1e-6]
print('   %s' % (hit if hit else '**一对都没有**'))
print('=' * 88)
