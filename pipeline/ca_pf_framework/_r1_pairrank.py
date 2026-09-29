#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_pairrank.py --- ★ 验证实验 7 的设计：**V1–V2 是不是一对"好"的自协调对？**

为什么必须查
------------
实验 7 让 6 个核用 packet-1 的两个变体 `{V1,V2}` **随机分配**，然后问
"末态构型是不是比随机指派能量更低"。这个问题的前提是：
**V1–V2 这一对在晶体学上确实比"随便挑一对"更相容**（残余失配更小）。
若 V1–V2 恰好是最**差**的一对，那实验 7 的 S-1 判据就失去意义。

判据（先写死）
--------------
两变体间的**失配应变** `Δε = ε_i − ε_j` 的**最佳 rank-1 逼近**残余：
  `r = min_{a,n} ‖Δε − ½(a nᵀ + n aᵀ)‖_F / ‖Δε‖_F`
（`r = 0` ⟺ 存在不变平面 ⟺ 完全相容；文献说真实 Burgers 变体对**都不是**精确 rank-1）
  * P-1 报出 **66 对**的 `r` 分布；
  * P-2 报出 **V1–V2 的 `r` 排名**（在 66 对里第几小）；
  * P-3 判定：若 V1–V2 落在**前 25%** ⇒ 它是"好对"，实验 7 的设计成立；
    若落在后 25% ⇒ **设计无效，必须换对**。

做法（纯线性代数，秒级，不跑仿真）
----------------------------------
`½(a nᵀ + n aᵀ)` 的**最优**对称 rank-1 逼近 = 对**对称**矩阵 `S = sym(Δε)` 取
绝对值最大的特征值对应的部分（Eckart–Young）：
  `S = Σ λ_k v_k v_kᵀ` ⇒ 取 `|λ_max|` 那一项 ⇒ `a = n = sign(λ)·sqrt(|λ|)·v`。
残余用**完整** `Δε`（含反对称部分）算，因为反对称部分无法被 `½(a nᵀ + n aᵀ)` 表示。
"""
import os
import sys
import itertools

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from T16_verify_rve import EPS0, NV                            # noqa: E402


def rank1_resid(dE):
    S = 0.5 * (dE + dE.T)
    w, V = np.linalg.eigh(S)
    k = int(np.argmax(np.abs(w)))
    lam = w[k]
    v = V[:, k]
    a = np.sign(lam) * np.sqrt(abs(lam)) * v
    approx = np.outer(a, a)
    return float(np.linalg.norm(dE - approx) / max(np.linalg.norm(dE), 1e-300)), lam


E = {k: np.asarray(EPS0[k - 1], float) for k in range(1, NV + 1)}
print('=' * 92)
print('实验 7 设计验证：66 个变体对的 rank-1（不变平面）相容性')
print('=' * 92)

rows = []
for i, j in itertools.combinations(range(1, NV + 1), 2):
    r, lam = rank1_resid(E[i] - E[j])
    rows.append((r, i, j, lam))
rows.sort()
rs = np.array([r[0] for r in rows])
print('\nP-1 `r` 分布（n=%d）：min %.3e  中位 %.3e  max %.3e'
      % (len(rows), rs.min(), np.median(rs), rs.max()))
print('   最好 8 对：')
for r, i, j, lam in rows[:8]:
    print('      V%-2d–V%-2d   r = %.4e   (λ_max = %+.3e)' % (i, j, r, lam))
print('   最差 4 对：')
for r, i, j, lam in rows[-4:]:
    print('      V%-2d–V%-2d   r = %.4e   (λ_max = %+.3e)' % (i, j, r, lam))

# P-2 V1–V2 的排名
target = [(k, r) for k, (r, i, j, lam) in enumerate(rows) if {i, j} == {1, 2}]
print('\nP-2 **V1–V2 的排名**：')
if target:
    k, r = target[0]
    pct = 100.0 * (k + 1) / len(rows)
    print('   r = %.4e  ⇒ 在 66 对里排第 **%d 小**（前 %.0f%%）' % (r, k + 1, pct))
    print('P-3 判定：%s'
          % ('✅ **好对**（前 25%）⇒ 实验 7 的设计成立'
             if pct <= 25 else
             ('⚠ 中等（25–75%）⇒ 实验 7 可用但对比不够强' if pct <= 75 else
              '⛔ **差对（后 25%）⇒ 实验 7 的设计无效，必须换对**')))
else:
    print('   ✗ 没找到 V1–V2')

# 同一 packet 内的对（同 c 轴）—— 实验 7 真正关心的
print('\n（附）同一 packet（同 c 轴）内的对：')
try:
    from windowB_ti64_variants import variants as _vars
    _e0, _Fs, _meta = _vars()
    cax = {k: np.asarray(_meta[k - 1]['n'], float) for k in range(1, NV + 1)}
    for i, j in itertools.combinations(range(1, NV + 1), 2):
        c = abs(cax[i] @ cax[j]) / (np.linalg.norm(cax[i]) * np.linalg.norm(cax[j]))
        if c > 0.99:
            r = [x[0] for x in rows if {x[1], x[2]} == {i, j}][0]
            rk = [k for k, x in enumerate(rows) if {x[1], x[2]} == {i, j}][0] + 1
            print('   V%-2d–V%-2d（同 c 轴）  r = %.4e   排名 %d/66' % (i, j, r, rk))
except Exception as e:
    print('   （读 c 轴失败：%s）' % e)
print('=' * 92)
