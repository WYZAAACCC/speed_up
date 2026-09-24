#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立正对照: Khachaturyan Lambda 张量的两条【已知解析答案】
 (1) rank-1 相容模式: eps = sym(a (x) n)  =>  eps:Lambda(n):eps = 0  （精确）
 (2) 纯体积特征应变 eps = e0*I      =>  0.5 eps:Lambda(n):eps = 2 mu e0^2 (1+nu)/(1-nu)
再把 V1-V2 的手推相容法向 n=[001] 代进去看是否为 0。
"""
import numpy as np
from windowB_pf3d import C_iso3, _lam_full, lambda_packed
from windowB_ti64_variants import variants

E_MOD, NU = 113e9, 0.34
C = C_iso3(E_MOD, NU)
mu = E_MOD / (2 * (1 + NU))

rng = np.random.default_rng(0)
worst = 0.0
for _ in range(5):
    a = rng.normal(size=3); n = rng.normal(size=3)
    a /= np.linalg.norm(a); n /= np.linalg.norm(n)
    eps = 0.5 * (np.outer(a, n) + np.outer(n, a))
    v = float(np.einsum('ij,ijkl,kl->', eps, _lam_full(C, n), eps))
    worst = max(worst, abs(v) / (mu * np.sum(eps ** 2)))
print('[L1] rank-1 模式 sym(a(x)n) => 0.5 eps:Lam:eps 的最大归一化值 = %.2e   %s'
      % (worst, 'PASS' if worst < 1e-12 else 'FAIL'))

e0 = 0.01
eps = e0 * np.eye(3)
for n in ([1, 0, 0], [1, 1, 0], [0.3, -0.5, 0.81]):
    v = float(np.einsum('ij,ijkl,kl->', eps, _lam_full(C, n), eps))
    vth = 2 * mu * e0 ** 2 * (1 + NU) / (1 - NU)
    print('[L2] 纯体积 eps=e0*I, n=%-18s 数值 = %.8e ; 解析 = %.8e ; 相对差 %.2e   %s'
          % (n, v, vth, abs(v - vth) / vth, 'PASS' if abs(v - vth) / vth < 1e-12 else 'FAIL'))

# lambda_packed 与 _lam_full 是否一致（打包/索引正确性）
K = np.array([[1., 0., 0.], [1., 1., 0.], [0.3, -0.5, 0.81], [0., 0., 0.]])
Lp = lambda_packed(C, K)
mx = 0.0
for i, k in enumerate(K):
    Lf = _lam_full(C, k) if np.linalg.norm(k) > 0 else C
    for p, (i1, j1) in enumerate([(0, 0), (1, 1), (2, 2), (1, 2), (0, 2), (0, 1)]):
        for q, (k1, l1) in enumerate([(0, 0), (1, 1), (2, 2), (1, 2), (0, 2), (0, 1)]):
            mx = max(mx, abs(Lp[i, p, q] - Lf[i1, j1, k1, l1]) / max(abs(Lf[i1, j1, k1, l1]), 1e-30))
print('[L3] lambda_packed vs _lam_full 最大相对差 = %.2e   %s' % (mx, 'PASS' if mx < 1e-12 else 'FAIL'))

# V1-V2 的手推相容法向
eps0, Fs, meta = variants()
de = eps0[1] - eps0[0]
print('\n[V1-V2] de =\n', np.round(de, 6))
for n in ([0, 0, 1], [1, 0, 0], [1, 1, 0]):
    v = 0.5 * float(np.einsum('ij,ijkl,kl->', de, _lam_full(C, np.array(n, float) + 1e-12), de))
    print('   n = %-12s 0.5 de:Lam:de = %+.6e  (归一化 %.3e)'
          % (n, v, v / (mu * np.sum(de ** 2))))
# 与 V1-V2 的 rank-1 判定
for nn in ([0, 0, 1.], [0.157, 0.988, 0.001]):
    n = np.array(nn); n /= np.linalg.norm(n)
    L = _lam_full(C, n)
    r = np.einsum('ijkl,kl->ij', L, de)
    print('   n = %-22s  |Lam:de| = %.4e (相对 |de| = %.3e)'
          % (nn, np.linalg.norm(r), np.linalg.norm(r) / np.linalg.norm(de)))
