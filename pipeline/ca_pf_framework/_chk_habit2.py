#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_habit2.py --- ★★★ `n*` 的**收敛值**与**物理身份**：`NPF` / 引擎 `_rank1_axes` / 真全局最小

背景（`_chk_axes.py` + `_chk_habit.py` 实测）
--------------------------------------------
1. `NPF`（`T16_verify_rve.py:45-53`，`_probe_shape.py` 用它当**厚向**并当 `npref` 传给 `M(n)`）
   与引擎 `wtab/atab`（`windowB_surface.py:987` 的 `_rank1_axes`，`β_w` 的 `w` 轴）：
      变体 1,4,5,7,9,10 ⇒ 差 **7.3–9.8°**；变体 2,3,6,8,11,12 ⇒ 差 **88.6–89.7°**
2. 两者都来自「**400 个随机法向取能量最小**」，但随机序列不同
   （`T16` 每变体重抽；引擎一次抽样所有变体共用）。
3. 40k 点 Fibonacci 球面上，`NPF` 的能量是全局最小的 **1.11–8.29 倍** ⇒ **`NPF` 不在全局最小**。

⇒ 本探针把三件事定下来：
  * **真全局最小**（Fibonacci 40k + 局部模式搜索精修）在哪；
  * 三组轴（`NPF` / 引擎 `n_eng=w×a` / 引擎 `a_eng`）各自离它多远、能量高多少；
  * 哪一个**是 {3 3 4}_β 型惯习面法向**（Burgers OR 下 β→α′ 的经典惯习面）。

⚠ 上一版 `_chk_habit.py` 的 H-4 正对照**写错了**（我按"立方操作下 `E(n)` 不变"判，
   但正确的协变关系是 `E(Qn; eps) = E(n; Qᵀ eps Q)`，单个变体的 `eps` 并不被立方群稳定）
   ⇒ 那条 FAIL **是我的判据错，不是引擎错**，已更正为 H-4′。

判据（先定判据再看数）
--------------------
  H-4′**正对照·协变关系**：`E(Qn; eps) − E(n; Qᵀ eps Q)` 应 ≈0（相对 <1e-9）。
       不过 ⇒ 本探针的 `_lam_full`/张量缩并写错了，后面结论不可用。
  H-5 **精修收敛**：把 Fibonacci 最优点再局部精修，能量相对下降应 `< 1e-3`
       （否则 40k 点本身也没找到最小）。
  H-6 **`NPF` 是否全局最小**：`E(NPF)/E(glob) − 1` 应 `< 1e-3`。
  H-7 **谁是 {3 3 4} 型**：三组轴各自到最近 {3 3 4}_β 方向的夹角。

用法：python3 _chk_habit2.py [--nsphere 40000]
"""
import os
import sys
import itertools
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--nsphere', type=int, default=40000)
a = ap.parse_args()

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)


def Efun(eps, n):
    return 0.5 * float(np.einsum('ij,ijkl,kl->', eps, _lam_full(C, n), eps))


def Evec(eps, NS):
    return 0.5 * np.einsum('ij,sijkl,kl->s', eps,
                           np.array([_lam_full(C, n) for n in NS]), eps)


def fib(n):
    i = np.arange(n, dtype=float)
    ph = np.pi * (3.0 - np.sqrt(5.0)) * i
    z = 1.0 - 2.0 * (i + 0.5) / n
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    NS = np.stack([r * np.cos(ph), r * np.sin(ph), z], axis=1)
    return NS / np.linalg.norm(NS, axis=1)[:, None]


def refine(eps, n0, rng, iters=60, nsamp=400, r0=0.25):
    """模式搜索：在当前最优点周围的开球里抽样，半径每轮 ×0.85。"""
    best, vb = np.asarray(n0, float), Efun(eps, n0)
    r = r0
    for _ in range(iters):
        d = rng.normal(size=(nsamp, 3))
        d /= np.linalg.norm(d, axis=1)[:, None]
        cand = best[None, :] + r * d
        cand /= np.linalg.norm(cand, axis=1)[:, None]
        v = Evec(eps, cand)
        j = int(np.argmin(v))
        if v[j] < vb:
            best, vb = cand[j], float(v[j])
        r *= 0.85
    return best, vb


def ang(u, v):
    u = np.asarray(u, float) / np.linalg.norm(u)
    v = np.asarray(v, float) / np.linalg.norm(v)
    return float(np.degrees(np.arccos(np.clip(abs(u @ v), -1.0, 1.0))))


# --- {3 3 4}_β 的 12 个极（β 笛卡尔系 = 立方晶轴系，见 windowB_ti64_variants 文档）---
H334 = []
for pos in range(3):
    for s1 in (+1, -1):
        for s2 in (+1, -1):
            v = [0.0, 0.0, 0.0]
            oth = [i for i in range(3) if i != pos]
            v[pos] = 4.0
            v[oth[0]] = 3.0 * s1
            v[oth[1]] = 3.0 * s2
            u = np.array(v)
            if not any(abs(u @ w) > 1 - 1e-9 for w in H334):
                H334.append(u / np.linalg.norm(u))
H334 = np.array(H334)


def near334(u):
    return min(ang(u, h) for h in H334)


print('=' * 112)
print('_chk_habit2 —— `n*` 的收敛值与物理身份    Fibonacci %d 点 + 模式搜索精修' % a.nsphere)
print('=' * 112)

# ---------------- H-4' 正对照：协变关系 E(Qn; eps) = E(n; Qᵀ eps Q) ----------------
rng0 = np.random.default_rng(7)
NS0 = fib(4000)
EPS = np.asarray(EPS0[0], float)
worst = 0.0
for perm in [(0, 1, 2), (0, 2, 1), (2, 1, 0), (1, 2, 0)]:
    for sgn in [(1, 1, 1), (-1, 1, 1), (1, -1, 1), (1, 1, -1)]:
        Q = np.zeros((3, 3))
        for i, p in enumerate(perm):
            Q[i, p] = sgn[i]
        NSp = NS0 @ Q.T                                  # Qn
        vQ = Evec(EPS, NSp)                              # E(Qn; eps)
        vr = Evec(Q.T @ EPS @ Q, NS0)                     # E(n; Qᵀ eps Q)
        worst = max(worst, float(np.max(np.abs(vQ - vr))))
scale = max(abs(Evec(EPS, NS0)).max(), 1e-30)
print('\nH-4′ 正对照（协变关系 `E(Qn;eps) = E(n;QᵀepsQ)`，16 个立方操作）：'
      'max|ΔE| = %.3e ；相对 %.2e' % (worst, worst / scale))
print("     （应 ≈0；不为 0 ⇒ 本探针张量缩并写错。⚠ 上一版按“E(n) 不变”判，"
      "那条 FAIL 是**我的判据错**）")

# ---------------- 主表 ----------------
NS = fib(a.nsphere)
g = W.LevelSetMulti(16, 16 * 50e-9, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                    df=[0.0] + [3.5e8] * NV, workers=1, reinit_every=0)
NPF = {}
_rng = np.random.default_rng(0)
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = Efun(np.asarray(EPS0[v], float), n)
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn

print('\nH-5/H-6/H-7 逐变体')
print('  %-4s %10s %10s %8s | %7s %7s %7s | %7s %7s %7s | %-6s' %
      ('变体', 'E(NPF)', 'E(glob)', 'E比', '<NPF,g>', '<neng,g>', '<aeng,g>',
       'NPF→334', 'neng→334', 'aeng→334', '谁在最小'))
nbad = 0
for k in range(1, NV + 1):
    eps = np.asarray(EPS0[k - 1], float)
    v = Evec(eps, NS)
    i0 = int(np.argmin(v))
    ng, vg = refine(eps, NS[i0], np.random.default_rng(11 + k)), None
    ng, vg = ng[0], ng[1]
    vfib = float(v[i0])
    vN = Efun(eps, np.asarray(NPF[k], float))
    w_ = np.asarray(g.wtab[k], float); w_ /= np.linalg.norm(w_)
    a_ = np.asarray(g.atab[k], float); a_ /= np.linalg.norm(a_)
    neng = np.cross(w_, a_); neng /= np.linalg.norm(neng)
    ratio = vN / vg
    if abs(ratio - 1.0) > 1e-3:
        nbad += 1
    who = []
    if ang(NPF[k], ng) < 5:
        who.append('NPF')
    if ang(neng, ng) < 10:
        who.append('neng')
    if ang(a_, ng) < 5:
        who.append('aeng')
    print('  %-4d %10.3e %10.3e %8.5f | %6.2f° %6.2f° %6.2f° | %6.2f° %6.2f° %6.2f° | %s'
          % (k, vN, vg, ratio, ang(NPF[k], ng), ang(neng, ng), ang(a_, ng),
             near334(NPF[k]), near334(neng), near334(a_), '+'.join(who) or '—'))
    print('       H-5 精修：Fibonacci 最优 %.3e → 精修 %.3e（相对降 %.2e）'
          % (vfib, vg, (vfib - vg) / vg))

print('\n  ⇒ H-6：`E(NPF)/E(glob) − 1 > 1e-3` 的变体数 = **%d/%d**' % (nbad, NV))
print('  ⇒ H-7：若某一列的 “→334” 全部 ≈0–5° ⇒ **那一列才是物理惯习面法向**。')
print('=' * 112)
