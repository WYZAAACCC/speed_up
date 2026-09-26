#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_rank1.py --- 判据 D12：对每个变体的形状应变 eps0[v] 做 **rank-1 分解**，
   得到不变平面法向 n 与位移方向 a；用于构造第二钉扎轴 w = n x a。

物理：rank-1 相容（MATH_FRAMEWORK 5.6 的 lam2(U)=1）等价于 dEps 的中间特征值 = 0，
      此时存在 n, a 使 dEps = 0.5*(a n^T + n a^T)。
      * n  = 惯习面法向（大面法向；已被 beta_h 压制）-- 应与 npref 一致（自证）
      * a  = 界面位错的**位移/滑移方向** = 板条的**长轴**（不压制）
      * w = n x a = 面内垂直方向 = 板条**宽度方向**（第二钉扎轴）

判据（三条，全部机器可判）：
  D12-1  lam2(eps0[v]) 应 << lam1/lam3 的尺度（rank-1 成立）
  D12-2  分解出的 n 与 npref[v]（弹性最省能法向）夹角应很小
  D12-3  n, a, w 三者正交归一；a 落在不变平面内（a.n ~ 0）
"""
import numpy as np
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, Fs, meta = variants()
nv = len(eps0)
rng = np.random.default_rng(0)
npref = {}
for v in range(nv):
    best, bn = None, None
    for n in rng.normal(size=(800, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
        if best is None or val < best:
            best, bn = val, n
    npref[v + 1] = bn


def rank1(eps):
    w, V = np.linalg.eigh(np.asarray(eps, float))
    o = np.argsort(w)[::-1]
    w = w[o]; V = V[:, o]
    mu1, mu2, mu3 = w
    e1, e3 = V[:, 0], V[:, 2]
    if mu1 <= 0 or mu3 >= 0:
        return None
    r = np.sqrt(-mu3 / mu1)
    n = e1 + r * e3
    n /= np.linalg.norm(n)
    a = mu1 * e1 - np.sqrt(-mu1 * mu3) * e3
    a /= np.linalg.norm(a)
    return dict(n=n, a=a, mu=(mu1, mu2, mu3))


print('=== D12: 变体的 rank-1 分解 ===')
print('%-4s %10s %10s %10s | %9s %9s | %9s %9s' %
      ('V', 'mu1', 'mu2', 'mu3', 'lam2/sc', 'ang(n,npref)', 'a.n', 'check'))
ok1 = ok2 = ok3 = 0
worst_ang = 0.0
for v in range(1, nv + 1):
    R = rank1(eps0[v - 1])
    if R is None:
        print('V%-2d 不是 rank-1' % v); continue
    mu1, mu2, mu3 = R['mu']
    sc = mu1 - mu3
    ang = np.degrees(np.arccos(np.clip(abs(R['n'] @ npref[v]), 0, 1)))
    adn = abs(R['a'] @ R['n'])
    # 重构检查
    rec = 0.5 * (np.outer(R['a'], R['n']) + np.outer(R['n'], R['a']))
    err = np.linalg.norm(rec / np.linalg.norm(rec) - eps0[v - 1] / np.linalg.norm(eps0[v - 1]))
    ok1 += int(abs(mu2) / sc < 1e-3)
    ok2 += int(ang < 15.0)
    ok3 += int(adn < 1e-6)
    worst_ang = max(worst_ang, ang)
    print('V%-2d %10.5f %10.5f %10.5f | %9.2e %9.1f | %9.1e %9.1e'
          % (v, mu1, mu2, mu3, abs(mu2) / sc, ang, adn, err))
print('  D12-1 rank-1 成立(|mu2|/scale<1e-3): %d/12' % ok1)
print('  D12-2 分解n vs npref 夹角<15deg   : %d/12 (最差 %.1f deg)' % (ok2, worst_ang))
print('  D12-3 a.n ~ 0（a 在不变平面内）  : %d/12' % ok3)
