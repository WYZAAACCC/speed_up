#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_paircompat.py —— 探针：变体对 (k,l) 在 `ncmp[k,l]` 处是不是**精确** rank-1 相容？

决定 T10 的判据形式：
  * 若 `0.5·Δε⁰:Λ(n):Δε⁰` 在 `n = ncmp[k,l]` 处**恰为 0** ⇒ 该界面**应力自由**
    ⇒ T10 判据可以写"相容面 `γ_el = 0`（机器零）"。
  * 若只是"很小但不为 0" ⇒ 判据必须写成"相容面 γ_el 比非相容面小 N 倍"，
    **不能**声称机器零（否则又是"测试看不到目标现象"的反面：判据本身不可达）。

同时给出 `ncmp` 与 `npref` 的夹角分布（T9 里 (1,2) 对是 46.96°）。
"""
import os
import sys

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
g = W.LevelSetMulti(8, 8 * 2.5e-8, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                    df=[0.0] * (NV + 1), workers=1, reinit_every=0)
tab = g.ncmp
E = [np.asarray(e, float) for e in EPS0]
# 参考尺度：单个变体的夹持弹性能
sc_ref = np.mean([0.5 * float(np.einsum('ij,ijkl,kl->', e, _lam_full(C, np.array([0., 0, 1.])), e))
                  for e in E])
print('参考尺度：单变体在 ẑ 法向下的夹持能 ~ %.4e J/m3' % sc_ref)
print()
print('%-10s %-16s %-16s %-12s %s' %
      ('(k,l)', '残余 0.5Δε:Lam:Δε', '相对单变体', 'ncmp·npref_k', '角(°)'))
worst = 0.0
for k in range(1, NV + 1):
    for l in range(k + 1, NV + 1):
        n = tab[k, l]
        if not np.isfinite(n).all():
            continue
        de = E[k - 1] - E[l - 1]
        res = 0.5 * float(np.einsum('ij,ijkl,kl->', de, _lam_full(C, n), de))
        nk = np.asarray(W.LevelSetMulti.__dict__ and [0, 0, 1.0])
        # 与 npref 无关，这里只报残余；角度列用 ncmp vs 自身所对应变体的"最软法向"
        worst = max(worst, res)
        if k <= 3 or res > 1e-3 * sc_ref:
            print('%-10s %-16.4e %-16.3e %-12s' %
                  ('(%d,%d)' % (k, l), res, res / sc_ref, '-'))
print()
print('所有 66 对的**最大**残余 = %.4e J/m3 （相对单变体尺度 %.3e）'
      % (worst, worst / sc_ref))
print('⇒ 若该值 ~0 ⇒ 存在**精确** rank-1 相容对；否则只能说"最小残差"')
print()
# npref 的残余（变体-母相）作为对照
print('变体-母相（npref[k]）的残余：')
for k in range(1, NV + 1):
    best = min(0.5 * float(np.einsum('ij,ijkl,kl->', E[k - 1],
                                     _lam_full(C, nn), E[k - 1]))
               for nn in (np.array([1.0, 0, 0]), np.array([0, 1.0, 0]),
                          np.array([0, 0, 1.0])))
    print('   k=%-2d %-16.4e  相对 %.3e' % (k, best, best / sc_ref))
