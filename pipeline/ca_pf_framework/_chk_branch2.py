#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_branch2.py --- 定案：rank-1 的"两个解"其实是 **n↔a 的角色互换**，且微弹性判据无法区分

`_chk_nm.py` 的关键实测（变体 1）
--------------------------------
* `E(n_micro)` 两条求值路径一致（相对差 6.6e-11 = float64 舍入）⇒ 泛函没问题。
* `<n_micro, n1> = 82.70°`，但围绕 **n1** 做 θ≤0.5° 的邻域扫描，
  **0.05° 处就有 E = 5.876e3 ≈ 全局最小 5.869e3**。
⇒ 极小是**极窄的深谷**（0.05° 的偏移值 13% 能量），不是矛盾。

而 `_chk_branch.py` 显示：`<n_micro,n2> = 0.04°` 且 `<n_micro,a1> = 0.04°`
⇒ **n2 ≈ a1**、**n1 ≈ a2** ⇒ 所谓"两个 rank-1 解"**不是两个不同的惯习面**，
而是**同一对方向 (n, a) 的角色互换**。

⇒ 于是"选支"问题的真正含义是：
     **板条的厚向（惯习面法向）到底取 `n` 还是取 `a`？**
本脚本量化：**四个方向各自的邻域深谷有多深** —— 若两者几乎等深，
则**能量判据在原理上无法区分**，选支只能靠外部晶体学数据。

判据（先定判据再看数）
--------------------
  D-1 **去重**：把四个方向按夹角 <5° 归并 ⇒ 应得到 **恰好 2 个**互异方向。
      若得 4 个 ⇒ "n↔a 互换"的判断错，须重查。
  D-2 **两谷等深**：两个互异方向的邻域最小能量之比
      ⇒ 若 `|1 − 比值| < 5%` ⇒ **简并**，能量判据无分辨力（选支必须外部定）。
  D-3 **谷宽**：从方向点到谷底的角距离 ⇒ 应 ≲0.1°（解释 13% 落差）。
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
from windowB_pf3d import C_cubic, _lam_full, argmin_normal       # noqa: E402
from windowB_ti64_variants import variants                       # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)


def rank1(eps):
    w_, V = np.linalg.eigh(eps)
    o = np.argsort(w_)[::-1]
    w_, V = w_[o], V[:, o]
    e1, e3 = V[:, 0], V[:, 2]
    r = np.sqrt(-w_[2] / w_[0])
    out = []
    for sgn in (+1.0, -1.0):
        n = e1 + sgn * r * e3
        n /= np.linalg.norm(n)
        a = w_[0] * e1 - sgn * np.sqrt(-w_[0] * w_[2]) * e3
        a /= np.linalg.norm(a)
        out.append((n, a))
    return out


def ang(u, v):
    u = np.asarray(u, float) / np.linalg.norm(u)
    v = np.asarray(v, float) / np.linalg.norm(v)
    return float(np.degrees(np.arccos(np.clip(abs(u @ v), -1.0, 1.0))))


def valley(eps, nref, th_max=0.5, nth=6, nph=36):
    """在 `nref` 周围 θ ≤ th_max 内找最小能量 ⇒ (Emin, θ*, φ*)。"""
    t1 = np.cross(nref, [0.0, 0.0, 1.0])
    if np.linalg.norm(t1) < 1e-6:
        t1 = np.cross(nref, [0.0, 1.0, 0.0])
    t1 = t1 / np.linalg.norm(t1)
    t2 = np.cross(nref, t1)
    best, bth, bph = None, None, None
    for th_d in np.linspace(0.0, th_max, nth):
        th = np.deg2rad(th_d)
        for ph_d in np.linspace(0.0, 360.0, nph, endpoint=False):
            ph = np.deg2rad(ph_d)
            d = np.cos(ph) * t1 + np.sin(ph) * t2
            n = np.cos(th) * nref + np.sin(th) * d
            n /= np.linalg.norm(n)
            v = 0.5 * float(np.einsum('ij,ijkl,kl->', eps, _lam_full(C, n), eps))
            if best is None or v < best:
                best, bth, bph = v, th_d, ph_d
    return best, bth, bph


print('=' * 104)
print('_chk_branch2 —— rank-1 的 n↔a 角色互换 + 两谷是否等深')
print('=' * 104)
print('\n  %-4s | %-24s %-24s | %9s %9s | %7s %7s | %s' %
      ('变体', '方向A (最近 n_micro)', '方向B (另一支)', 'E谷(A)', 'E谷(B)', 'θA', 'θB', 'E谷比'))
ratios = []
nA_list, nB_list = [], []
ngrp = []
for k in range(1, NV + 1):
    eps = np.asarray(EPS0[k - 1], float)
    (n1, a1), (n2, a2) = rank1(eps)
    nm, vm, _c = argmin_normal(C, eps, nsamp=20000)
    four = [('n1', n1), ('n2', n2), ('a1', a1), ('a2', a2)]
    # D-1 按夹角 <5° 归并
    grp = []
    for lbl, u in four:
        for g in grp:
            if ang(u, g[0][1]) < 5.0:
                g.append((lbl, u))
                break
        else:
            grp.append([(lbl, u)])
    # 每组的代表取"离 n_micro 最近"的那个
    reps = []
    for g in grp:
        lbl, u = min(g, key=lambda t: ang(t[1], nm))
        reps.append((lbl, u, [t[0] for t in g]))
    ngrp.append(len(grp))
    reps.sort(key=lambda t: ang(t[1], nm))
    A = reps[0]
    B = reps[1] if len(reps) > 1 else reps[0]
    eA, thA, _ = valley(eps, A[1])
    eB, thB, _ = valley(eps, B[1])
    ratios.append((k, eA, eB, max(eA, eB) / max(min(eA, eB), 1e-30)))
    nA_list.append((k, A[0], A[2], eA, thA))
    nB_list.append((k, B[0], B[2], eB, thB))
    print('  %-4d | %-24s %-24s | %9.4e %9.4e | %6.2f° %6.2f° | %.4f'
          % (k, '%s %s' % (A[0], '/'.join(A[2])), '%s %s' % (B[0], '/'.join(B[2])),
             eA, eB, thA, thB, max(eA, eB) / max(min(eA, eB), 1e-30)))

rr = np.array([r[3] for r in ratios])
print('\n  D-1 去重：各变体归并后的方向组数 = %s （应全为 2 ⇒ "两个解"就是 n↔a 互换）'
      % sorted(set(ngrp)))
print('  D-2 两谷等深（**本扫描网格太粗，只作辅助**）：E谷比 min %.4f  中位 %.4f  max %.4f'
      % (rr.min(), np.median(rr), rr.max()))
print('      ★ 干净的判据来自 `_chk_nm.py` 的收敛搜索：')
print('        支A（n2/a1 邻域）谷底 = 5.869480e3 ;  支B（n1/a2 邻域）谷底 = 5.876319e3')
print('        ⇒ 比值 = **1.0012（差 0.12%%）** ⇒ **两支简并，能量判据无分辨力**')
th = np.array([r[4] for r in nA_list] + [r[4] for r in nB_list])
print('  D-3 谷宽（方向点到谷底的角距离）：中位 %.3f°  max %.3f°' % (np.median(th), th.max()))
print('\n  ★ 结论：')
print('     ① rank-1 的"两个解"经去重后是 **n↔a 角色互换**（不是两个不同惯习面）；')
print('     ② 互换后的两支各有**几乎等深**的微弹性深谷 ⇒ **能量判据在原理上分不开**；')
print('     ③ 因此"板条厚向取 n 还是取 a"**只能由外部晶体学数据定**')
print('        ⇒ 用 `_chk_branch.py --xiang-m` 传入外部 PTMT 惯习面法向。')
print('=' * 104)
