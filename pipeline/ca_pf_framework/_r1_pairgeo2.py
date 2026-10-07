#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_pairgeo2.py --- ★ 用**正确的**小应变 Hadamard 判据重做 66 对。

⚠ 动机（自我更正）
------------------
`_r1_svcheck.py` 把"`σ₃ = 0`"标成 "rank-1 ✅"，`_r1_paircorr.py` 用
"对称部分的最佳 rank-1 残余"当几何判据。**两者都不是本问题的正确判据。**

正确的判据推导
--------------
小应变下两变体的**共格（不变平面）界面**要求应变差可写成

    Δε = sym(a ⊗ n)          （a 为跳跃矢量，n 为界面法向）

令 `a = a∥·n + a⊥`（`a∥ = a·n`，`a⊥ ⊥ n`），则右边 = `a∥·n⊗n + sym(a⊥⊗n)`，
其特征值为

    ( a∥ ,  +|a⊥|/2 ,  −|a⊥|/2 )

⇒ **判据：Δε 的三个特征值中，有两个等大反号。** 记
`g3 = min_{i<j} |λ_i + λ_j| / ‖Δε‖_F`，则 `g3 = 0` ⟺ 存在不变平面。

这与"`Δε` 严格 rank-1（`σ₂ = 0`）"**不是**同一件事：
- `a ⊥ n` 时 `sym(a⊗n)` 特征值 `(+q, −q, 0)` ⇒ **秩 2**，但**满足判据**（`g3 = 0`）。
- 同 packet 的 `Δε` 正是这种**纯剪切**（`σ₁ = σ₂ = 1.8378e-02`, `σ₃ = 0`）
  ⇒ 它**满足**不变平面判据，而被我上一版错误地标成"rank-1"。

本脚本对 66 对算 `g3`，并与 `E_min` 交叉制表。
"""
import csv
import os
import sys
import itertools

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from T16_verify_rve import EPS0, NV                                   # noqa: E402

E = [np.asarray(e, float) for e in EPS0]

print('=' * 92)
print('0 前置检查：`EPS0` 是不是对称的？（判据只对对称张量成立）')
asym = max(float(np.abs(e - e.T).max() / max(np.abs(e).max(), 1e-300)) for e in E)
print('   66 个变体应变张量的最大不对称度 = %.3e  ⇒ %s'
      % (asym, '✅ 对称' if asym < 1e-12 else '⚠ 不对称，须先对称化'))

rows = []
for k, l in itertools.combinations(range(1, NV + 1), 2):
    dE = E[k - 1] - E[l - 1]
    S = 0.5 * (dE + dE.T)
    lam = np.linalg.eigvalsh(S)                     # 升序
    nrm = float(np.linalg.norm(S))
    pairs = [abs(lam[0] + lam[1]), abs(lam[0] + lam[2]), abs(lam[1] + lam[2])]
    g3 = float(min(pairs) / max(nrm, 1e-300))
    tr = float(lam.sum())
    rows.append((k, l, g3, lam, tr, nrm))

# 与 E_min 合并
em = {}
for d in csv.DictReader(open(os.path.join(HERE, '_exp', 'paircorr.csv'))):
    em[(int(d['k']), int(d['l']))] = float(d['E_min'])

g3v = np.array([x[2] for x in rows])
ev = np.array([em[(x[0], x[1])] for x in rows])
SAME = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)]
_S = set(SAME)
same = np.array([(x[0], x[1]) in _S for x in rows])

print('\n1 正确判据 `g3` 的分布（`g3 = 0` ⟺ 存在不变平面界面）：')
TOL = 1e-9
ok = g3v < TOL
print('   满足（g3 < 1e-9）：%2d/66 对' % int(ok.sum()))
print('   不满足            ：%2d/66 对' % int((~ok).sum()))
if (~ok).any():
    print('   不满足者的 g3 范围：%.4e … %.4e' % (g3v[~ok].min(), g3v[~ok].max()))
print('   同 packet 6 对的 g3：%s'
      % ['%.2e' % g3v[i] for i in np.where(same)[0]])

print('\n2 交叉制表：几何判据（正确版） × 模型 `E_min`')
print('   %-16s %5s %13s %13s %10s' % ('域', 'n', 'E_min 最小', 'E_min 最大', '跨度'))
for tag, m in (('满足 g3=0', ok), ('不满足 g3>0', ~ok),
               ('满足 ∩ 同 packet', ok & same),
               ('满足 ∩ 跨 packet', ok & ~same),
               ('不满足 ∩ 跨 packet', (~ok) & ~same)):
    n = int(m.sum())
    if n == 0:
        print('   %-16s %5d  —' % (tag, 0)); continue
    lo, hi = ev[m].min(), ev[m].max()
    print('   %-16s %5d %13.4e %13.4e %9.1f×' % (tag, n, lo, hi, hi / max(lo, 1e-300)))

print('\n3 同 packet 6 对的完整特征值谱 + `E_min`：')
print('   %-10s %8s %12s %12s %12s %8s %14s'
      % ('对', 'tr(Δε)', 'λ_min', 'λ_mid', 'λ_max', 'g3', 'E_min'))
for k, l in SAME:
    x = [r for r in rows if (r[0], r[1]) == (k, l)][0]
    lam = x[3]
    print('   V%-2d–V%-2d %8.1e %12.6e %12.6e %12.6e %8.1e %14.4e'
          % (k, l, x[4], lam[0], lam[1], lam[2], x[2], em[(k, l)]))

print('\n4 ⇒ 结论：')
n_ok_same = int((ok & same).sum())
print('   * 同 packet 6 对里 %d/6 满足正确几何判据（g3 ≈ 0）' % n_ok_same)
lo, hi = ev[ok & same].min(), ev[ok & same].max()
print('     而模型给它们的 `E_min` 跨 %.1f 倍（%.4e … %.4e）' % (hi / lo, lo, hi))
print('   * 几何判据在 66 对上仍是**近乎二值**：取值集合大小 = %d'
      % len(np.unique(np.round(g3v, 9))))
print('     ⇒ **判据正确时结论不变**：它把候选分成两大类，')
print('       但对同一类内部（尤其同 packet 的 6 对）**零分辨力**。')
print('   * ⇒ 排序必须用模型自己的 `E_min`。')
print('=' * 92)
