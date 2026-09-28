#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_habit5.py --- ★★★ 定案：`n*` 的**解析真值** = `F` 的不变平面法向

为什么这条路对
--------------
`windowB_ti64_variants.variants()` 已经返回了每个变体的**形变梯度 `F`**（`EPS0,_F,_M`）。
不变平面（惯习面）的定义是：**`F` 保持该平面的法向不变**，即
    `Fᵀ n = λ n`，且 `λ = 1`   ⇔   `n` 是 `Fᵀ` 的特征向量、特征值 **恰为 1**
（等价说法：该法向不被拉伸。对不变平面应变 `F = I + ½(a nᵀ + n aᵀ)` 可验证 `Fᵀn = n`。）

⇒ **这是解析判据，不依赖任何搜索**，也不依赖 `n·a` 是否为零。

而现行代码用的是「`argmin_n 0.5·eps:Lam(C,n):eps`，在 **400 个随机法向**里取最小」——
`_chk_habit2` 实测该泛函的极小**极窄**：40,000 点 Fibonacci 仍比精修值高 **3–9 倍**，
400 点则高 **21–654 倍**（`E(NPF)/E_min`）。
且两个 rank-1 解的 `E` 只差 **8.6%**（6.757e3 vs 7.342e3）⇒ **能量判据对"选哪个解"几乎没有分辨力**
⇒ 抽样一抖就翻支。

判据（先定判据再看数）
--------------------
  H-9  **`Fᵀ` 是否有特征值 1**：`|λ−1|` 应 `< 1e-9`（构造保证）。不成立 ⇒ 本判据不适用。
  H-10 **`n*_inv` 是不是 {3 3 4}_β 型**：β 笛卡尔系 = 立方晶轴系
       ⇒ 与 12 个 {3 3 4} 极的夹角应 `< 2°`。
  H-11 **现行三组轴离解析真值多远**：`NPF` / `n_eng`(=w×a) / `a_eng` / 精修最小。

用法：python3 _chk_habit5.py
"""
import os
import sys
import itertools

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, FV, _M = variants()
NV = len(EPS0)


def ang(u, v):
    u = np.asarray(u, float) / np.linalg.norm(u)
    v = np.asarray(v, float) / np.linalg.norm(v)
    return float(np.degrees(np.arccos(np.clip(abs(u @ v), -1.0, 1.0))))


H334 = []
for pos in range(3):
    for s1, s2 in itertools.product((+1, -1), repeat=2):
        v = [0.0, 0.0, 0.0]
        oth = [i for i in range(3) if i != pos]
        v[pos], v[oth[0]], v[oth[1]] = 4.0, 3.0 * s1, 3.0 * s2
        u = np.array(v)
        if not any(abs(u @ w) > 1 - 1e-9 for w in H334):
            H334.append(u / np.linalg.norm(u))
H334 = np.array(H334)
near = lambda u: min(ang(u, h) for h in H334)

print('=' * 108)
print('_chk_habit5 —— `n*` 的解析真值：`Fᵀ n = n`（不变平面法向）')
print('=' * 108)

g = W.LevelSetMulti(16, 16 * 50e-9, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                    df=[0.0] + [3.5e8] * NV, workers=1, reinit_every=0)
_rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', np.asarray(EPS0[v], float),
                                    _lam_full(C, n), np.asarray(EPS0[v], float)))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn

print('\n  %-4s %-10s | %-13s | %8s %8s %8s | %8s' %
      ('变体', '|λ−1|', 'n*_inv→{334}', '<NPF,n*>', '<neng,n*>', '<aeng,n*>', 'neng→{334}'))
worst_lam = 0.0
worst_334 = 0.0
dNPF, dneng = [], []
for k in range(1, NV + 1):
    F = np.asarray(FV[k - 1], float)
    ev, evec = np.linalg.eig(F.T)                     # 左特征向量：Fᵀ n = λ n
    j = int(np.argmin(np.abs(ev - 1.0)))
    lam = ev[j]
    n_inv = np.real(evec[:, j])
    n_inv /= np.linalg.norm(n_inv)
    worst_lam = max(worst_lam, abs(lam - 1.0))
    d334 = near(n_inv)
    worst_334 = max(worst_334, d334)
    w_ = np.asarray(g.wtab[k], float); w_ /= np.linalg.norm(w_)
    a_ = np.asarray(g.atab[k], float); a_ /= np.linalg.norm(a_)
    neng = np.cross(w_, a_); neng /= np.linalg.norm(neng)
    d1, d2, d3 = ang(NPF[k], n_inv), ang(neng, n_inv), ang(a_, n_inv)
    dNPF.append(d1); dneng.append(d2)
    print('  %-4d %-10.2e | %-13s | %7.2f° %7.2f° %7.2f° | %7.2f°'
          % (k, abs(lam - 1.0), '%.2f°' % d334, d1, d2, d3, near(neng)))

print('\n  H-9  `|λ−1|` 最大 = %.2e（判据 <1e-9）⇒ %s'
      % (worst_lam, 'PASS：不变平面存在，判据适用' if worst_lam < 1e-9 else 'FAIL'))
print('  H-10 `n*_inv` 到最近 {3 3 4}_β 的最大夹角 = %.2f°（判据 <2°）⇒ %s'
      % (worst_334, 'PASS：解析真值就是 {334} 型惯习面' if worst_334 < 2.0 else 'FAIL'))
print('  H-11 `NPF`  离解析真值：max %.2f°  mean %.2f°  （>20° 的变体数 %d/12）'
      % (max(dNPF), np.mean(dNPF), sum(1 for d in dNPF if d > 20)))
print('       `n_eng`离解析真值：max %.2f°  mean %.2f°  （>20° 的变体数 %d/12）'
      % (max(dneng), np.mean(dneng), sum(1 for d in dneng if d > 20)))
print('=' * 108)
