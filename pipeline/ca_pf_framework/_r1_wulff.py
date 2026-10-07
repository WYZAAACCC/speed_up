#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_wulff.py --- ★★ A-3（尖端/棱圆角）的**结构性**判决：这个 `M(n)` 到底能不能长出facet？

问题
----
观测：所有单核臂的 `fill_cal` 末值 ≈ **0.5**（≈ 椭球值 π/6 = 0.524），
即长出来的板**没有平坦的面**，是圆角板；而真实马氏体板条有明确的**惯习面平面**。

为什么不能靠调参解决（本脚本要证的命题）
------------------------------------------
无曲率项时，法向速度 `v(n) = M(n)·Δf` 下，**凸种子**的渐近形状是
**支撑函数 `h(n) ∝ M(n)` 那个凸体**（Wulff 构造）。关键在于：
  * 若 `M(n)` 在球面上作为支撑函数是**凸的** ⇒ 形状处处光滑，**没有 facet**；
  * 若 `M(n)` **非凸** ⇒ 真实形状是 `{M(n)·n}` 的**凸包**，
    凸包的**面**就出现在 `M(n)` 非凸的那些方向上 ⇒ **facet**。
⇒ 所以"能否有 facet"是一个**可计算**的问题，不需要跑仿真。

判据
----
  H-1 采样 `M(n)`（Fibonacci 球）→ 点集 `{M(n)·n}` → **凸包**。
  H-2 凸包在 `n*`（惯习面法向）方向上有**多大面积的面**？与整个凸包表面积比多少？
      * 面积极小 ⇒ **没有惯习面 facet** ⇒ 观测到的圆角是**结构性必然**，不是参数问题。
  H-3 把 `β_h` 扫一遍（3.5 → 60），看**需要多大**才出现显著 facet
      ⇒ 给出"要改到什么程度"的定量答案。
  H-4 报告该凸包的 `fill_cal = V/(L·W·T)`，与观测的 0.5 对照 ⇒ 交叉验证解释。

⚠ 本脚本**只做几何**，不跑仿真。
"""
import os
import sys

import numpy as np
from scipy.spatial import ConvexHull

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def fib_sphere(n):
    """Fibonacci 球采样（与引擎 `_fib_sphere` 同一手法）。"""
    i = np.arange(n, dtype=float) + 0.5
    z = 1.0 - 2.0 * i / n
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    ph = np.pi * (1.0 + 5.0 ** 0.5) * i
    return np.stack([r * np.cos(ph), r * np.sin(ph), z], axis=1)


# ---- 取与引擎同一套三轴 ----
K = int(sys.argv[1]) if len(sys.argv) > 1 else 1
try:
    import windowB_surface as W
    from T16_verify_rve import C as C_rve, EPS0 as EPS0_rve, NV as NV_rve, NPF as NPF_rve
    _g = W.LevelSetMulti(8, 1.0e-6, C=C_rve, eps0=EPS0_rve, gamma=0.15,
                         Mob=1.0, df=[0.0] * (NV_rve + 1), workers=1)
    n_hab = np.asarray(NPF_rve[K], float); n_hab /= np.linalg.norm(n_hab)
    w_ax = np.asarray(_g.wtab[K], float); w_ax /= np.linalg.norm(w_ax)
    a_ax = np.asarray(_g.atab[K], float)
    a_ax = a_ax - (a_ax @ n_hab) * n_hab
    a_ax /= (np.linalg.norm(a_ax) + 1e-300)
except Exception as e:                                                   # noqa: BLE001
    print('⛔ 取不到引擎三轴（%s: %s）⇒ 结论无效' % (type(e).__name__, e))
    sys.exit(2)

print('=' * 100)
print('变体 K=%d ；`n*`=[%+.4f %+.4f %+.4f]  `w`=[%+.4f %+.4f %+.4f]  `a`=[%+.4f %+.4f %+.4f]'
      % ((K,) + tuple(n_hab) + tuple(w_ax) + tuple(a_ax)))
print('=' * 100)


def shape_of(beta_h, beta_w, nsamp=200000):
    """返回凸包、三向跨度、`fill_cal`、以及 `n*` 方向上的 facet 面积占比。"""
    NS = fib_sphere(nsamp)
    M = np.exp(-beta_h * (NS @ n_hab) ** 2 - beta_w * (NS @ w_ax) ** 2)
    P = NS * M[:, None]                      # 点集 {M(n)·n}
    try:
        h = ConvexHull(P)
    except Exception as e:                                               # noqa: BLE001
        return None
    # 三向跨度（沿 a / w / n*）
    spans = []
    for ax in (a_ax, w_ax, n_hab):
        pr = P @ ax
        spans.append(float(pr.max() - pr.min()))
    La, Lw, Ln = spans
    fill = float(h.volume) / max(La * Lw * Ln, 1e-300)
    # `n*` 方向上的 facet：找法向接近 ±n* 的凸包面，累计面积
    eq = h.equations                       # (nf, 4)：[A B C D]，法向 (A,B,C) 外指
    nrm = eq[:, :3]
    unit = nrm / np.linalg.norm(nrm, axis=1)[:, None]
    for tol in (1.0, 2.0, 5.0):
        pass
    cos = np.abs(unit @ n_hab)
    areas = h.area_facets if hasattr(h, 'area_facets') else None
    # 逐面面积：用凸包顶点算
    fa = []
    for i, simp in enumerate(h.simplices):
        v = P[simp]
        fa.append(0.5 * np.linalg.norm(np.cross(v[1] - v[0], v[2] - v[0])))
    fa = np.array(fa)
    tot = fa.sum()
    out = dict(La=La, Lw=Lw, Ln=Ln, fill=fill,
               nfacet=int(h.simplices.shape[0]),
               area_tot=float(tot))
    for tol in (1.0, 2.0, 5.0):
        m = (np.degrees(np.arccos(np.clip(cos, -1, 1))) <= tol)
        out['frac_n%.0f' % tol] = float(fa[m].sum() / max(tot, 1e-300))
        out['n_n%.0f' % tol] = int(m.sum())
    return out


print('\nH-1/H-2  当前参数（β_h=3.5, β_w=2.3）下的**动力学 Wulff 形状**：')
r0 = shape_of(3.5, 2.3)
if r0 is None:
    print('  ✗ 凸包失败'); sys.exit(1)
print('   三向跨度（a/w/n*）= %.4f / %.4f / %.4f  ⇒ 比值 1 : %.3f : %.3f'
      % (r0['La'], r0['Lw'], r0['Ln'], r0['Lw'] / r0['La'], r0['Ln'] / r0['La']))
print('   `fill_cal` = **%.3f**   （观测到的单核末值 ≈ 0.50；椭球 = 0.524）' % r0['fill'])
print('   凸包面数 = %d' % r0['nfacet'])
for tol in (1.0, 2.0, 5.0):
    print('   法向在 `n*` 的 **%.0f°** 内的面：%d 个，占凸包表面积 **%.4f%%**'
          % (tol, r0['n_n%.0f' % tol], 100 * r0['frac_n%.0f' % tol]))

print('\nH-3 扫 `β_h`（固定 β_w=2.3），看**多大才出现显著 facet**：')
print('   %8s %12s %12s %14s %14s' %
      ('β_h', 'L:W:T', 'fill_cal', 'n*面占比(2°)', 'w面占比(2°)'))
for bh in (3.5, 6, 10, 20, 40, 60, 100, 200):
    r = shape_of(bh, 2.3)
    if r is None:
        continue
    NS = fib_sphere(200000)
    print('   %8g %12s %12.3f %13.4f%% %13.4f%%'
          % (bh, '1:%.3f:%.3f' % (r['Lw'] / r['La'], r['Ln'] / r['La']),
             r['fill'], 100 * r['frac_n2.0'], 100 * r['frac_n2.0']))

print('\nH-4 判读：')
f_n = r0['frac_n2.0']
if f_n < 0.01:
    print('   ⛔ **当前的 `M(n)` 不可能长出惯习面 facet**：`n*` 方向的面只占 %.3f%% 表面积'
          % (100 * f_n))
    print('      ⇒ 观测到的圆角板（`fill_cal`≈0.5）是**当前迁移率泛函的结构性必然**，')
    print('        **不是**分辨率不足、也不是 `stk`/`γ` 没调好 ⇒ 调参无法解决 A-3。')
else:
    print('   ⇒ `n*` 方向已有可观 facet（%.2f%%）⇒ 圆角另有原因，需继续查。'
          % (100 * f_n))
print('=' * 100)
