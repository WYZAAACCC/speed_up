#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_habit3.py --- 把四组候选轴**认成 Miller 指数**：`n*` 到底该是哪个方向？

背景：`_chk_axes.py` / `_chk_habit2.py` 实测，同一个变体有**四组**候选轴：
  ① `NPF[k]`      —— `T16_verify_rve.py` 的 400 随机 argmin（探针拿它当**厚向**、并当 `npref` 传进 `M(n)`）
  ② `n_eng[k]`    —— 引擎 `wtab × atab`（`_rank1_axes` 的 rank-1 解，用作 `β_w` 的 `w` 的母体）
  ③ `a_eng[k]`    —— 引擎 `atab`（rank-1 的长轴）
  ④ `n_glob[k]`   —— 40k Fibonacci + 模式搜索精修后的**真全局最小**（12 个变体能量全 = 5.869e3）

判据：β 笛卡尔系 = 立方晶轴系（`windowB_ti64_variants` 文档）⇒ 每一组都应能被
**小整数三元组** `(hkl)`（|h|,|k|,|l| ≤ 8）在 **<2°** 内识别。
  * 若 ④ 全部识别为 **{3 3 4}** 且 ① 不能 ⇒ `NPF` 是错的，`n*` 应取 ④。
  * 若 ② 全部识别为 {3 3 4} ⇒ rank-1 解才是物理惯习面，`n*` 应取 ②。
  * 若 ④ 与 ② 都识别为 {3 3 4} 但差 ~90° ⇒ 说明 {3 3 4} 里有两个不同的极
    （(3,3,4) 与 (3,-3,4) 系），须看**是哪一个**。

用法：python3 _chk_habit3.py
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
EPS0, _F, _M = variants()
NV = len(EPS0)

_CAND = []
for h in range(0, 9):
    for k in range(0, 9):
        for l in range(0, 9):
            if (h, k, l) == (0, 0, 0):
                continue
            g = np.gcd(np.gcd(h, k), l)
            if g != 1:
                continue
            for s in itertools.product((+1, -1), repeat=3):
                v = np.array([h * s[0], k * s[1], l * s[2]], float)
                if h == 0 and s[0] < 0:
                    continue
                _CAND.append((v / np.linalg.norm(v), (h * s[0], k * s[1], l * s[2])))
# 去重（同一个轴只留一个代表）
KEYS, CAND, CAND_U = set(), [], []
for u, idx in _CAND:
    key = tuple(np.round(u, 9))
    if key in KEYS:
        continue
    if any(abs(u @ w) > 1 - 1e-9 for w in CAND_U):
        continue
    KEYS.add(key)
    CAND.append((u, idx))
    CAND_U.append(u)
CU = np.array([c[0] for c in CAND])


def miller(u):
    u = np.asarray(u, float) / np.linalg.norm(u)
    d = np.abs(CU @ u)
    j = int(np.argmax(d))
    return CAND[j][1], float(np.degrees(np.arccos(np.clip(d[j], -1, 1))))


def fib(n):
    i = np.arange(n, dtype=float)
    ph = np.pi * (3.0 - np.sqrt(5.0)) * i
    z = 1.0 - 2.0 * (i + 0.5) / n
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    NS = np.stack([r * np.cos(ph), r * np.sin(ph), z], axis=1)
    return NS / np.linalg.norm(NS, axis=1)[:, None]


def Efun(eps, n):
    return 0.5 * float(np.einsum('ij,ijkl,kl->', eps, _lam_full(C, n), eps))


def refine(eps, n0, rng, iters=60, nsamp=400, r0=0.25):
    best, vb = np.asarray(n0, float), Efun(eps, n0)
    r = r0
    for _ in range(iters):
        d = rng.normal(size=(nsamp, 3))
        d /= np.linalg.norm(d, axis=1)[:, None]
        cand = best[None, :] + r * d
        cand /= np.linalg.norm(cand, axis=1)[:, None]
        v = 0.5 * np.einsum('ij,sijkl,kl->s', eps,
                            np.array([_lam_full(C, n) for n in cand]), eps)
        j = int(np.argmin(v))
        if v[j] < vb:
            best, vb = cand[j], float(v[j])
        r *= 0.85
    return best, vb


NS = fib(40000)
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

print('=' * 104)
print('_chk_habit3 —— 四组候选轴的 Miller 指数识别（β 笛卡尔系 = 立方晶轴系，|hkl|≤8）')
print('=' * 104)
print('  %-4s | %-14s %-14s | %-14s %-14s' %
      ('变体', '① NPF', '② n_eng=w×a', '③ a_eng', '④ n_glob(精修)'))
for k in range(1, NV + 1):
    eps = np.asarray(EPS0[k - 1], float)
    v = 0.5 * np.einsum('ij,sijkl,kl->s', eps, np.array([_lam_full(C, n) for n in NS]), eps)
    ng, _ = refine(eps, NS[int(np.argmin(v))], np.random.default_rng(11 + k))
    w_ = np.asarray(g.wtab[k], float); w_ /= np.linalg.norm(w_)
    a_ = np.asarray(g.atab[k], float); a_ /= np.linalg.norm(a_)
    neng = np.cross(w_, a_); neng /= np.linalg.norm(neng)
    r1 = miller(NPF[k]); r2 = miller(neng); r3 = miller(a_); r4 = miller(ng)
    print('  %-4d | %-14s %-14s | %-14s %-14s'
          % (k, '%s (%.1f°)' % (r1[0], r1[1]), '%s (%.1f°)' % (r2[0], r2[1]),
             '%s (%.1f°)' % (r3[0], r3[1]), '%s (%.1f°)' % (r4[0], r4[1])))
print('=' * 104)
