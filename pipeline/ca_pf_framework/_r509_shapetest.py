#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r509_shapetest.py —— `--nuc-shape` 的**可证伪预测**检验。

## 预测（写死在 `R507_fullclosure` 里，本文件只负责检验）

| 量 | `disc`（尖边圆柱，默认） | `ellipsoid`（光滑椭球） |
|---|---|---|
| `\|med_ed\|` 弹性罚 | **3.1818e8**（`_r479` 实测） | **2.0873e8**（`_r470`/`_r474` 实测） |
| 超临界翻转点 `df*` | **3.1818e8** | **≈2.0873e8** |
| 门槛温度 `T_阈` | **377.7 K** | **641.7 K** |

**⇒ 预测：换成椭球后，探针报的 `|med_ed|` 与翻转点都必须降到原来的 ~66%。**

## 预登记判据（**先写死，且必须能失败**）

| # | 检验 | 判据 |
|---|---|---|
| **S1** | **换形状真的降低了罚** | `\|med_ed\|_ellip < \|med_ed\|_disc`（严格） |
| **S2** | **降幅符合预测** | `\|med_ed\|_ellip / \|med_ed\|_disc ∈ [0.55, 0.80]`（预测 0.656） |
| **S3** | **翻转点同幅下降** | `df*_ellip / df*_disc ∈ [0.55, 0.80]`，且 `df* + med_ed ≈ fcrit`（残差 < 1e-6） |
| **S4** | **负对照：disc 必须复现 `_r479`** | `\|med_ed\|_disc` 与 3.1818e8 的相对差 ≤ 5% |
| **S5** | **只差形状** | 两种形状的 `cover` 胞数**相同**（同 R/t） |
| **S6** | **两者净效果都为零** | 调用前后 `phi` 逐位相同 |

⚠ **若 S2 FAIL** ⇒ 我的"椭球罚低 52%"这个前提不成立（那是 `_r474`/`_r479` 在**不同代码路径**
下测的：前者用 `PF3D`、后者用引擎的 `_supercrit_probe`）⇒ **必须照实记**，不得圆场。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_surface as W                                  # noqa: E402
import windowB_km as KM                                      # noqa: E402
from T16_verify_rve import C, EPS0                           # noqa: E402

N = 64
DX = 62.5e-9
NV = len(EPS0)
GAMMA = 0.25
T_NUC = 510e-9
R_NUC = 320e-9
ED_DISC_REF = 3.181850e8
ED_ELLIP_REF = 2.087286e8
PRED_RATIO = ED_ELLIP_REF / ED_DISC_REF      # 0.656
RATIO_LO, RATIO_HI = 0.55, 0.80
TOL_S4 = 0.05
TOL_S3 = 1e-6


def P(s=''):
    print(s, flush=True)


def build():
    eps0 = [np.asarray(e, float) for e in EPS0]
    g = W.LevelSetMulti(N, N * DX, C=C, eps0=eps0, gamma=GAMMA, Mob=1e-9,
                        df=[0.0] + [1.2e8] * NV, workers=1,
                        reinit_every=0, reinit_dt=1e-4)
    g.npref_tab = {k: np.asarray(W._argmin_normal(C, eps0[k - 1])[0], float)
                   for k in range(1, NV + 1)}
    g.init_parent()
    return g


def cover_of(g, ctr, nrm, R, t):
    rel = g.XYZ - np.asarray(ctr, float)
    d = rel @ np.asarray(nrm, float)
    rp = np.linalg.norm(rel - d[..., None] * np.asarray(nrm, float), axis=-1)
    return (np.abs(d) <= t / 2) & (rp <= R)


def flip_point(g, kk, ctr, nrm, R, t, cover, shape):
    """二分求 `df*`：该位点站得住所需的最小化学驱动力。"""
    lo, hi = -1e10, 1e10
    f_lo = g._supercrit_probe(kk, ctr, nrm, R, t, cover, lo, GAMMA, shape=shape)[0]
    f_hi = g._supercrit_probe(kk, ctr, nrm, R, t, cover, hi, GAMMA, shape=shape)[0]
    if f_lo == f_hi:
        return None
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if g._supercrit_probe(kk, ctr, nrm, R, t, cover, mid, GAMMA, shape=shape)[0]:
            hi = mid
        else:
            lo = mid
    return hi


def main():
    P('=' * 96)
    P('R509  `--nuc-shape` 的可证伪预测检验（尖边圆柱 vs 光滑椭球）')
    P('=' * 96)
    P('  预测（`R507_fullclosure`）：椭球的弹性罚 = 圆盘 × **%.3f**' % PRED_RATIO)
    P('  参照实测：圆盘 %.4e（`_r479`）  椭球 %.4e（`_r470`/`_r474`）'
      % (ED_DISC_REF, ED_ELLIP_REF))
    P()

    g = build()
    kk = 2
    nrm = np.asarray(g.npref_tab[kk], float)
    nrm = nrm / (np.linalg.norm(nrm) + 1e-300)
    ctr = np.array([N * DX / 2] * 3)
    cov = cover_of(g, ctr, nrm, R_NUC, T_NUC)
    P('  位点 = 盒中心；R=%.0f nm  t=%.0f nm  ⇒ cover = **%d 胞**'
      % (R_NUC * 1e9, T_NUC * 1e9, int(cov.sum())))
    P()

    out = {}
    for shape in ('disc', 'ellipsoid'):
        phi0 = g.phi.copy()
        _, med, fc, nc = g._supercrit_probe(kk, ctr, nrm, R_NUC, T_NUC, cov,
                                            1.2e8, GAMMA, shape=shape)
        same = bool(np.array_equal(g.phi, phi0))
        dfstar = flip_point(g, kk, ctr, nrm, R_NUC, T_NUC, cov, shape)
        Tth = None
        if dfstar is not None:
            lo, hi = 298.0, 1144.0
            for _ in range(200):
                mid = 0.5 * (lo + hi)
                if float(KM.drive_of_T(mid, KM.T0_TI64, KM.DS_REF)) > abs(med):
                    lo = mid
                else:
                    hi = mid
            Tth = hi
        out[shape] = dict(med=med, fcrit=fc, ncov=nc, rollback=same,
                          dfstar=dfstar, Tth=Tth)
        P('  ── %s ──' % shape)
        P('     cover 胞数 = %d ；判据阈值 2γ/t = %.4e' % (nc, fc))
        P('     `med_ed` = **%.6e**  ⇒ 弹性罚 |med_ed| = **%.6e J/m³**'
          % (med, abs(med)))
        P('     翻转点 df* = %s' % ('%.6e' % dfstar if dfstar is not None else '（无）'))
        P('     门槛温度 T_阈 = %s' % ('%.1f K' % Tth if Tth else '（无）'))
        P('     调用前后 `phi` 逐位相同 = **%s**' % same)
        P()

    d, e = out['disc'], out['ellipsoid']
    P('=' * 96)
    P('★ 判据')
    s1 = abs(e['med']) < abs(d['med'])
    P('  S1 椭球罚 < 圆盘罚：%.6e vs %.6e ⇒ **%s**'
      % (abs(e['med']), abs(d['med']), '✅ PASS' if s1 else '❌ FAIL'))
    ratio = abs(e['med']) / abs(d['med'])
    s2 = RATIO_LO <= ratio <= RATIO_HI
    P('  S2 降幅符合预测：比值 = **%.4f**（预测 %.3f，判据 [%.2f, %.2f]）⇒ **%s**'
      % (ratio, PRED_RATIO, RATIO_LO, RATIO_HI, '✅ PASS' if s2 else '❌ FAIL'))
    s3 = False
    if d['dfstar'] and e['dfstar']:
        r2 = e['dfstar'] / d['dfstar']
        s3a = RATIO_LO <= r2 <= RATIO_HI
        _, m_e, f_e, _ = g._supercrit_probe(kk, ctr, nrm, R_NUC, T_NUC, cov,
                                            e['dfstar'], GAMMA, shape='ellipsoid')
        res = abs(e['dfstar'] + m_e - f_e) / max(abs(f_e), 1e-300)
        s3 = bool(s3a and res < TOL_S3)
        P('  S3 翻转点同幅下降：df*_e/df*_d = **%.4f**；核对残差 %.2e ⇒ **%s**'
          % (r2, res, '✅ PASS' if s3 else '❌ FAIL'))
    s4 = abs(abs(d['med']) - ED_DISC_REF) / ED_DISC_REF <= TOL_S4
    P('  S4 负对照：disc 必须复现 `_r479` 的 %.4e，实测 %.4e，相对差 %.4f ⇒ **%s**'
      % (ED_DISC_REF, abs(d['med']),
         abs(abs(d['med']) - ED_DISC_REF) / ED_DISC_REF, '✅ PASS' if s4 else '❌ FAIL'))
    s5 = (d['ncov'] == e['ncov'])
    P('  S5 只差形状：cover 胞数 %d vs %d ⇒ **%s**'
      % (d['ncov'], e['ncov'], '✅ PASS' if s5 else '❌ FAIL'))
    s6 = d['rollback'] and e['rollback']
    P('  S6 净效果为零：两形状回滚都干净 = %s ⇒ **%s**'
      % (s6, '✅ PASS' if s6 else '❌ FAIL'))

    P()
    P('=' * 96)
    ok = s1 and s2 and s3 and s4 and s5 and s6
    P('★ 汇总： S1=%s S2=%s S3=%s S4=%s S5=%s S6=%s'
      % tuple('PASS' if x else 'FAIL' for x in (s1, s2, s3, s4, s5, s6)))
    if ok:
        P('★ ⇒ **预测成立**：椭球把弹性罚降到 %.1f%%，门槛 %.1f K → %.1f K。'
          % (100 * ratio, d['Tth'] or float('nan'), e['Tth'] or float('nan')))
        P('    ⇒ `R507` 的五约束闭环（α_KM ∈ [0.0058, 0.0205]，参考 0.011 在内）成立。')
    else:
        P('★ ⇒ **预测未完全成立**，照实记，不得圆场。')
    P('=' * 96)
    return 0


if __name__ == '__main__':
    sys.exit(main())
