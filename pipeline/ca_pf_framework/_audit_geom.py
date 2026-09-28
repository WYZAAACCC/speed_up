#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_geom.py --- 独立审计：验证单核实验的"extent"是否被周期盒截断（几何上限）。"""
import sys, os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants()

# --- 复刻 _chk_single_lath.py 里 npref 的随机抽样算法（同 seed=0, 400 样本）---
rng = np.random.default_rng(0)
npref = {}
for v in range(len(eps0)):
    best, bn = None, None
    for n in rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
        if best is None or val < best:
            best, bn = val, n
    npref[v + 1] = bn

# --- 类内 _rank1_axes 用的 nref（seed 0, 400 样本）---
rng2 = np.random.default_rng(0)
ns = rng2.normal(size=(400, 3)); ns /= np.linalg.norm(ns, axis=1)[:, None]
wtab = {}; atab = {}
for v in range(len(eps0)):
    E = np.asarray(eps0[v], float)
    val = 0.5 * np.einsum('ij,sijkl,kl->s', E, np.array([_lam_full(C, n) for n in ns]), E)
    nref = ns[int(np.argmin(val))]
    R = _rank1 = None
    w_, V = np.linalg.eigh(E); o = np.argsort(w_)[::-1]; w_ = w_[o]; V = V[:, o]
    mu1, mu3 = w_[0], w_[2]
    e1, e3 = V[:, 0], V[:, 2]
    r = np.sqrt(-mu3 / mu1)
    cands = []
    for sgn in (+1.0, -1.0):
        n = e1 + sgn * r * e3; n /= np.linalg.norm(n)
        a = mu1 * e1 - sgn * np.sqrt(-mu1 * mu3) * e3; a /= np.linalg.norm(a)
        cands.append((n, a))
    nd = nref / np.linalg.norm(nref)
    best = max(cands, key=lambda t: abs(t[0] @ nd))
    n, a = best
    wv = np.cross(n, a); wv /= np.linalg.norm(wv)
    wtab[v + 1] = wv; atab[v + 1] = a

k = 1
n1 = npref[k] / np.linalg.norm(npref[k])
t1 = wtab[k] / np.linalg.norm(wtab[k])
t2 = np.cross(n1, t1); t2 /= np.linalg.norm(t2)
a_true = atab[k] / np.linalg.norm(atab[k])
n_true = None

print('=== 变体 %d ===' % k)
print('npref (驱动脚本, 400 随机抽样)   =', np.array2string(n1, precision=5))
print('atab  (类内 rank-1 真长轴 a)     =', np.array2string(a_true, precision=5))
print('wtab  (类内 w = n_hab x a)       =', np.array2string(t1, precision=5))
print('驱动脚本用的 along = npref x wtab =', np.array2string(np.cross(n1, t1) / np.linalg.norm(np.cross(n1, t1)), precision=5))
print('  -> 驱动脚本 along 与真 a 的夹角 = %.2f deg'
      % np.degrees(np.arccos(np.clip(abs(np.cross(n1, t1) / np.linalg.norm(np.cross(n1, t1)) @ a_true), 0, 1))))
print('t2 = npref x wtab  (驱动脚本的"长轴方向") =', np.array2string(t2, precision=5))
print('  -> t2 与真 a 的夹角 = %.2f deg'
      % np.degrees(np.arccos(np.clip(abs(t2 @ a_true), 0, 1))))
print('a.npref 夹角 = %.2f deg' % np.degrees(np.arccos(np.clip(abs(a_true @ n1), 0, 1))))
print('w.npref 夹角 = %.2f deg' % np.degrees(np.arccos(np.clip(abs(t1 @ n1), 0, 1))))

print()
print('=== 周期盒投影上限（extent 的最大可能值 = L * sum|v_i|）===')
for name, v in (('npref', n1), ('wtab', t1), ('t2(=along 用)', t2), ('真 a', a_true)):
    s = float(np.abs(v).sum())
    for L in (1.6e-6, 2.4e-6, 3.2e-6):
        print('  %-14s L=%.1f um -> 上限 %.3f um' % (name, L * 1e6, L * s * 1e6))

print()
print('=== 关键实测值 vs 上限 ===')
obs = {
    'W23(N=80,L=1.6)  e1=2.2973': (2.2973e-6, 1.6e-6),
    'X10(N=160,L=1.6) e1=2.1913': (2.1913e-6, 1.6e-6),
    'N1 (N=80,L=1.6)  side2=2.450': (2.450e-6, 1.6e-6),
    'D03(N=120,L=2.4) e1=2.8849': (2.8849e-6, 2.4e-6),
    'D20(N=120,L=2.4) side2=3.406': (3.406e-6, 2.4e-6),
    'C0 (N=160,L=3.2) side2=4.175': (4.175e-6, 3.2e-6),
    'C1 (N=160,L=3.2) side2=5.262': (5.262e-6, 3.2e-6),
    'A0 (N=120,L=2.4) side2=3.568': (3.568e-6, 2.4e-6),
    'A1 (N=120,L=2.4) side2=3.784': (3.784e-6, 2.4e-6),
}
for name, (val, L) in obs.items():
    lim = L * abs(t2).sum()
    print('  %-30s extent %.4f um ; 该方向周期投影上限 %.4f um ; 占上限 %5.1f%%   %s'
          % (name, val * 1e6, lim * 1e6, 100 * val / lim,
             '*** 疑已被盒截断 ***' if val > 0.9 * lim else
             ('> L 本身 (%.1f um)' % (L * 1e6) if val > L else 'ok')))
