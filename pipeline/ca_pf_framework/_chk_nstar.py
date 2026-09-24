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
