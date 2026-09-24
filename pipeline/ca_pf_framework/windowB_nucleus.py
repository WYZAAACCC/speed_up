#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_nucleus.py --- 晶核法向的两条独立判据交叉验证 + 比弹性能标定

判据 A（晶体学, PTMC）：不变平面法向 = U = sqrt(F^T F) 的 lambda2 本征向量
                        （lambda2 = 1 时才严格存在不变平面；本项目 lambda2 = 1.00042）
判据 B（弹性, 本模型）：使 eps0:Lambda(n):eps0 最小的方向（孤立薄板的弹性能最小化）
两者必须一致 —— 若一致，说明"弹性最小化"这条便宜的路能替代 PTMC 搜索。
同时给出【单位转变量】的弹性能 w_el(f)，用来判断多高的 Delta f 才推得动长大。
"""
import numpy as np
from windowB_pf3d import C_iso3, _lam_full
from windowB_ti64_variants import variants

E_MOD, NU = 113e9, 0.34


def lam2_normal(F):
    """U 的最小本征值对应的本征向量（lambda2 = 中间本征值 = 1 时的不变平面法向）"""
    w, V = np.linalg.eigh(F.T @ F)
    U = np.sqrt(np.clip(w, 1e-30, None))
    i = int(np.argsort(U)[1])
    return V[:, i], U


def elastic_normal(C, eps, nobs=3000):
    best, bn = None, None
    rng = np.random.default_rng(0)
    for n in rng.normal(size=(nobs, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps, _lam_full(C, n), eps))
        if best is None or val < best:
            best, bn = val, n
    return bn, best


def main():
    C = C_iso3(E_MOD, NU)
    eps0, Fs, meta = variants()
    print('=' * 96)
    print('晶核法向：PTMC(lambda2) vs 弹性最小化  两条独立判据的交叉验证')
    print('=' * 96)
    angs = []
    for v in range(len(Fs)):
        n_ptmc, U = lam2_normal(Fs[v])
        n_el, w_el = elastic_normal(C, eps0[v])
        a1, a2 = abs(float(np.dot(n_ptmc, n_el))), abs(float(np.dot(n_ptmc, n_el)))
        ang = np.degrees(np.arccos(min(1.0, max(-1.0, a2))))
        angs.append(ang)
        if v < 4:
            print('  V%2d: lambda=(%.5f,%.5f,%.5f)' % (v + 1, *np.sort(U)))
            print('        PTMC  n* = [%+.3f %+.3f %+.3f]' % tuple(n_ptmc))
            print('        弹性  n* = [%+.3f %+.3f %+.3f]   夹角 %.2f deg'
                  '   0.5 eps:Lam(n*):eps = %.4e J/m^3' % (*n_el, ang, w_el))
    print('\n  12 个变体的两条判据夹角: min %.2f  max %.2f  deg   %s'
          % (min(angs), max(angs), 'PASS(一致)' if max(angs) < 5 else 'CHECK'))
    w_min = np.mean([elastic_normal(C, e)[1] for e in eps0[:4]])
    w_u = np.mean([0.5 * np.einsum('ij,ijkl,kl->', e, C, e) for e in eps0[:4]])
    print('\n  [比能标定] 孤立薄板最优取向的弹性能 = %.3e J/m^3' % w_min)
    print('             均匀(无择优)变体的弹性能   = %.3e J/m^3' % w_u)
    print('     => 薄板形状把比弹性能压低 %.0f 倍（说明"板条形状"本身就是弹性最优）'
          % (w_u / w_min))
    print('     => 要推动板条长大, df 需与"薄板比弹性能"同量级：df >~ %.1e J/m^3'
          % w_min)
    return angs


if __name__ == '__main__':
    main()
