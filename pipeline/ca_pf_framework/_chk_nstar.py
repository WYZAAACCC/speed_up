#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 PTMC 的不变平面法向代入弹性泛函：0.5 eps:Lam(n_PTMC):eps 是否 ≈ 0?
   若是，则"PTMC 不变平面"与"弹性最省能取向"是同一个东西（谷是零测度线/面，随机搜索会跑偏）。"""
import numpy as np
from windowB_pf3d import C_iso3, _lam_full
from windowB_ti64_variants import variants

C = C_iso3(113e9, 0.34)
eps0, Fs, meta = variants()
print('=' * 90)
print('PTMC 不变平面法向 vs 弹性泛函（V1~V3）')
print('=' * 90)
for v in range(3):
    F = Fs[v]
    w, V = np.linalg.eigh(F.T @ F)
    U = np.sqrt(np.clip(w, 1e-30, None))
    i2 = int(np.argsort(U)[1])
    i1, i3 = [k for k in range(3) if k != i2]
    e = eps0[v]
    def val(n):
        n = np.asarray(n, float)
        n = n / np.linalg.norm(n)
        return 0.5 * float(np.einsum('ij,ijkl,kl->', e, _lam_full(C, n), e))
    v_ptmc = val(V[:, i2])
    v1 = val(V[:, i1])
    v3 = val(V[:, i3])
    v_uni = 0.5 * float(np.einsum('ij,ijkl,kl->', e, C, e))
    # 定位优化：从 PTMC 法向出发再局部降
    rng = np.random.default_rng(1)
    best, bn = v_ptmc, V[:, i2]
    r = 0.3
    for _ in range(4000):
        cand = bn + r * rng.normal(size=3)
        cand /= np.linalg.norm(cand)
        vv = val(cand)
        if vv < best:
            best, bn = vv, cand
        else:
            r *= 0.999
    print('V%d  eps 本征值 = %s' % (v + 1, np.round(np.sort(np.linalg.eigvalsh(e)), 6)))
    print('     n_PTMC (lambda2 本征向量)     : 0.5eps:Lam:eps = %.6e J/m^3' % v_ptmc)
    print('     n = e1 / e3 (另两个本征方向)   : %.6e / %.6e' % (v1, v3))
    print('     局部优化后的最小值 %.6e （法向 %s）' % (best, np.round(bn, 3)))
    print('     均匀(无择优)对照               : %.6e J/m^3' % v_uni)

# ---- 判据（★ 2026-09-25 补：原脚本只打印数值、无 pass/fail）----
print()
print('---- 惯习面判据（两条，必须分开记）----')
_rows = []
for v in range(min(3, len(eps0))):
    e = eps0[v]
    ev, evec = np.linalg.eigh(e)
    n_ptmc = evec[:, 1]
    val = lambda nn: 0.5 * float(np.einsum('ij,ijkl,kl->', e, _lam_full(C, nn / (np.linalg.norm(nn) + 1e-30)), e))
    from scipy.optimize import minimize as _mn
    def obj(x):
        return val(x)
    best = None
    for _ in range(40):
        x0 = np.random.default_rng(100 + _).normal(size=3)
        r = _mn(obj, x0, method='Nelder-Mead', options=dict(maxiter=4000, xatol=1e-10, fatol=1e-6))
        if best is None or r.fun < best.fun:
            best = r
    _rows.append((float(val(n_ptmc)), float(best.fun), float(val(np.array([1., 0., 0.])))))
for i, (a, b, c) in enumerate(_rows):
    print('   V%d: PTMC(lambda2) = %.3e ; 弹性能最小 = %.3e ; 均匀对照 = %.3e'
          % (i + 1, a, b, c))
_minr = min(r[1] / max(r[2], 1e-30) for r in _rows)
_ptmr = min(r[0] / max(r[1], 1e-30) for r in _rows)
print('   NSTAR-1 存在"相容法向"使弹性能比均匀对照低 3 个数量级以上: %s（最小比 %.2e）'
      % ('PASS' if _minr < 1e-3 else 'FAIL', _minr))
print('   NSTAR-2 PTMC 的 lambda2 法向 **不是** 弹性能最小法向（两者相差 >= 10x）: %s（最小比 %.2e）'
      % ('PASS' if _ptmr > 10.0 else 'FAIL', _ptmr))
print('   => 记账：{334} 惯习面到底对应哪个判据（弹性最省能 vs lambda2=1）必须写明，不能互换。')
