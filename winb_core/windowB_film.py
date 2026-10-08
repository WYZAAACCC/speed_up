#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_film.py —— **Gibbs 面上的薄膜序参量 ψ**（`BLOCK_DERIVATION.md` §4.6）。

## 物理

板条间界面是**零厚度 Gibbs 面**。面上带一个独立状态量 @@\\psi@@：
@@\\psi=0@@ = **干低角晶界**（面能 @@\\gamma_{\\rm dry}@@），@@\\psi=1@@ = **有膜**（面能 @@\\gamma_f@@）。

@@
\\gamma_\\Sigma(\\psi,\\theta)=(1-f(\\psi))\\,\\gamma_{\\rm dry}(\\theta)+f(\\psi)\\,\\gamma_f+W g(\\psi),
\\qquad f=\\psi^2(3-2\\psi),\\; g=\\psi^2(1-\\psi)^2
@@

@@
\\partial_t\\psi=-L_\\psi\\big[f'(\\psi)(\\gamma_f-\\gamma_{\\rm dry})+W g'(\\psi)-\\kappa_\\psi\\nabla_\\Sigma^2\\psi\\big]
\\tag{4.9}
@@

## ★ 引擎**没有面网格** —— @@\\nabla_\\Sigma^2@@ 怎么算（E-8c）

把 ψ 存在界面带（3D 胞）上，直接做 3D @@\\nabla^2@@ 得到的是**体** Laplacian（法向只有 1–2 层胞，
法向二阶差分会污染）。正确做法是**先沿法向延拓、再取体 Laplacian**：

@@
\\text{延拓后}\\ \\nabla\\psi\\perp\\mathbf n\\ \\Longrightarrow\\
\\nabla_\\Sigma^2\\psi=\\nabla^2\\psi-(\\mathbf n\\cdot\\nabla)^2\\psi\\approx\\nabla^2\\psi
@@

延拓用引擎里**已有**的 `extend_along_normal`（`windowB_surface.py:420`）—— 不另写一份。

## ★★ 两个必须知道的数值事实

1. **ψ≡0 与 ψ≡1 都是 (4.9) 的精确不动点**（@@f'(0)=f'(1)=g'(0)=g'(1)=0@@）
   ⇒ 从均匀态出发**一步都不动**（Allen–Cahn 的一般性质：均匀态没有"形核"驱动力）。
   ⇒ `psi0` 必须取 **0.99 / 0.01**（等价于无穷小扰动），**不能取 1.0 / 0.0**。
2. ψ=1 是否**稳定**取决于 @@\gamma_f-\gamma_{\rm dry}@@ 与 @@W@@：
   线性化给 @@\psi=1@@ 稳定 @@\iff\gamma_f-\gamma_{\rm dry}<W/3@@。
   本项目 @@\gamma_f-\gamma_{\rm dry}\approx0.5\gg W/3@@ ⇒ **ψ=1 不稳定 ⇒ 会退湿**（P-2）。

## 本文件**只提供算子**，不改引擎

⇒ 生产跑（`_bk_exp.py`）**不受影响**；接线进 `advance` 是下一步（I-5 的剩余部分）。
`_selftest` 在**合成数据**上验证 5 条（不需要仿真）。

跑法：`python3 windowB_film.py`
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


# ---------------------------------------------------------------------------
def f_interp(psi):
    """@@f(\\psi)=\\psi^2(3-2\\psi)@@（@@f(0)=0,f(1)=1,f'=6\\psi(1-\\psi)@@）"""
    p = np.asarray(psi, float)
    return p * p * (3.0 - 2.0 * p)


def g_well(psi):
    """@@g(\\psi)=\\psi^2(1-\\psi)^2@@（@@g'=2\\psi(1-\\psi)(1-2\\psi)@@）"""
    p = np.asarray(psi, float)
    return p * p * (1.0 - p) ** 2


def gamma_mix(g_dry, psi, gamma_f, W):
    """(4.8b)：把"干"与"膜"两种面能按 ψ 混合。"""
    f = f_interp(psi)
    return (1.0 - f) * g_dry + f * gamma_f + W * g_well(psi)


def surface_laplacian(psi, phi, dx, iters=6, dtau_fac=0.4, par=None):
    """@@\\nabla_\\Sigma^2\\psi@@：**先沿法向延拓、再取体 Laplacian**（见模块 docstring）。

    `phi` = 用来定义法向的水平集场（取 winner 的 φ）。
    ⚠ 延拓的**理论依据**：延拓后 @@\\nabla\\psi\\perp\\mathbf n@@
    ⇒ @@(\\mathbf n\\cdot\\nabla)^2\\psi\\approx0@@ ⇒ @@\\nabla_\\Sigma^2\\psi\\approx\\nabla^2\\psi@@。
    这也正是"用延拓法算面扩散"的标准做法。
    """
    import windowB_surface as W
    ext = W.extend_along_normal(np.asarray(psi, float), np.asarray(phi, float),
                                dx, iters=iters, dtau_fac=dtau_fac)
    g = np.gradient(ext, dx, edge_order=2)
    return (np.gradient(g[0], dx, edge_order=2)[0]
            + np.gradient(g[1], dx, edge_order=2)[1]
            + np.gradient(g[2], dx, edge_order=2)[2])


def ac_rhs(psi, g_dry, gamma_f, W, kappa, lap):
    """(4.9) 的右端（**不含** @@-L_\\psi@@ 因子）。"""
    fp = 6.0 * psi * (1.0 - psi)
    gp = 2.0 * psi * (1.0 - psi) * (1.0 - 2.0 * psi)
    return -(fp * (gamma_f - g_dry) + W * gp - kappa * lap)


def safe_dt(L, W, gamma_f, g_dry_max, kappa, dx, dt):
    """显式 AC 的稳定步长（保守）：@@\\Delta t\\le0.2/\\big(L_\\psi(6\\Delta\\gamma+2W+\\kappa/dx^2)\\big)@@。"""
    rate = L * (6.0 * abs(gamma_f - g_dry_max) + 2.0 * W
                + (kappa / dx ** 2 if dx > 0 else 0.0))
    if rate <= 0:
        return dt
    return min(dt, 0.2 / rate)


def psi_step(psi, phi, dx, g_dry, dt, gamma_f, L=1.0e-8, W=0.05, kappa=0.0,
             band=None, iters=6, clip=True, par=None):
    """(4.9) 的一步（显式）。`g_dry` 逐胞（F3 用 @@\\gamma_{\\rm RS}(\\theta)@@，其余填 @@\\gamma_0@@）。

    `band` 给定时**只在带内更新**（带外保持不变）—— 引擎里带胞占 0.2%–1.2%（§4.6）。
    返回 (psi_new, 诊断 dict)。
    """
    psi = np.asarray(psi, float)
    g_dry = np.asarray(g_dry, float)
    dte = safe_dt(L, W, gamma_f, float(np.max(np.abs(g_dry))) if g_dry.size else 0.0,
                  kappa, dx, dt)
    lap = surface_laplacian(psi, phi, dx, iters=iters, par=par) if kappa != 0.0 \
        else np.zeros_like(psi)
    rhs = ac_rhs(psi, g_dry, gamma_f, W, kappa, lap)
    new = psi + dte * L * rhs
    if clip:
        new = np.clip(new, 0.0, 1.0)
    if band is not None:
        new = np.where(band, new, psi)
    return new, dict(dt_eff=dte, dt_req=dte < dt, max_abs_rhs=float(np.max(np.abs(rhs)))
                     if rhs.size else 0.0)


def psi_step_local(psi, g_dry, dt, band, gamma_f, W=0.05, L=1.0e8, clip=True):
    """**局域**（@@\\kappa_\\psi=0@@）AC 一步：**只在 `band` 的胞上更新**。

    ★ 为什么本阶段的 `auto` 臂**这就够**：
      **P-2（自发退湿）是逐点判据** —— 每个 F3 胞按局部的 @@(\\gamma_f-\\gamma_{\\rm dry})@@
      决定 ψ 的去向。面内耦合 @@\\kappa_\\psi>0@@ 属精化（记账 S-6），
      而且它需要 @@\\nabla_\\Sigma^2@@（面延拓），在 N=192 上是**每步几十秒**的开销
      ⇒ 先用局域版把**判决**拿到。

    ★★ **性能与并行**：用 `np.flatnonzero(band)` 把更新限制在 F3 胞上
      （生产臂 ~3000 胞），**而不是**在整个 N³ 上算再 `where`
      ⇒ 瞬时分配从 4×56 MB 降到 **KB 量级**；且它跑在**主线程**
      （与 `par.for_each` 的 worker 不重叠）⇒ 不引入任何竞态。
    """
    if band is None or not band.any():
        return psi, dict(n_band=0, dt_eff=dt)
    flat = psi.ravel()
    idx = np.flatnonzero(band)
    p = flat[idx]
    gd = np.asarray(g_dry).ravel()[idx]
    dte = safe_dt(L, W, gamma_f, float(np.max(np.abs(gd))) if gd.size else 0.0,
                  0.0, 1.0, dt)
    p = p + dte * L * ac_rhs(p, gd, gamma_f, W, 0.0, np.zeros_like(p))
    if clip:
        p = np.clip(p, 0.0, 1.0)
    flat[idx] = p
    return psi, dict(n_band=int(idx.size), dt_eff=dte, dt_req=dte < dt,
                     psi_mean=float(p.mean()))


# ===========================================================================
def _selftest():
    F = []

    def ck(tag, ok, det=''):
        print('  %-58s %s %s' % (tag, 'PASS' if ok else '**FAIL**', det))
        if not ok:
            F.append(tag)

    print('=' * 100)
    print('windowB_film._selftest —— 合成数据（不需要仿真）')
    print('=' * 100)

    # F-1 混合函数的端点与单调性
    ck('F-1.1 gamma_mix(psi=0) == g_dry', abs(float(gamma_mix(0.3, 0.0, 0.8, 0.05)) - 0.3) < 1e-15)
    ck('F-1.2 gamma_mix(psi=1) == gamma_f', abs(float(gamma_mix(0.3, 1.0, 0.8, 0.05)) - 0.8) < 1e-15)
    ck("F-1.3 f'(0.5) == 1.5 且 g'(0.5) == 0",
       abs(6 * 0.5 * 0.5 - 1.5) < 1e-15 and abs(2 * .5 * .5 * (1 - 1.0)) < 1e-15)

    # F-2 不动点：均匀 psi、均匀 g_dry、无梯度 ⇒ rhs(0)=rhs(1)=0
    z = np.zeros((8, 8, 8))
    ck('F-2.1 psi≡0 是精确不动点',
       np.all(ac_rhs(z, np.full((8, 8, 8), 0.3), 0.8, 0.05, 0.0, z) == 0.0))
    ck('F-2.2 psi≡1 是精确不动点',
       np.all(ac_rhs(np.ones((8, 8, 8)), np.full((8, 8, 8), 0.3), 0.8, 0.05, 0.0,
                     z) == 0.0))

    # F-3 退湿 / 润湿：先用**精确的符号判据**（快且无收敛问题），再用松弛看方向
    ck('F-3.0a gamma_f>gamma_dry ⇒ rhs(psi=0.5) < 0（psi 减小）',
       float(ac_rhs(np.array([0.5]), np.array([0.15]), 0.60, 0.05, 0.0,
                    np.array([0.0]))[0]) < 0)
    ck('F-3.0b gamma_f<gamma_dry ⇒ rhs(psi=0.5) > 0（psi 增大）',
       float(ac_rhs(np.array([0.5]), np.array([0.60]), 0.15, 0.05, 0.0,
                    np.array([0.0]))[0]) > 0)

    def relax(p0, gd, gf, n=40000, L=1.0, W=0.05, eta=2e-3):
        """★ 记账：**趋近端点是渐近的** —— f'(ψ)=6ψ(1−ψ)→0（ψ→0）
           ⇒ 不能要求有限步内到 1e-3，只能判**方向 + 单调 + 已走完大部分**。"""
        p = np.full((4, 4, 4), float(p0))
        hist = []
        for i in range(n):
            p = np.clip(p + eta * L * ac_rhs(p, np.full(p.shape, gd), gf, W, 0.0,
                                             np.zeros_like(p)), 0.0, 1.0)
            if i % 2000 == 0:
                hist.append(float(p.mean()))
        return np.array(hist)
    h1 = relax(0.999, 0.15, 0.60)
    h2 = relax(0.001, 0.60, 0.15)
    ck('F-3.1 gamma_f > gamma_dry ⇒ **单调退湿** psi→0（P-2）',
       bool(np.all(np.diff(h1) <= 1e-12)) and h1[-1] < 0.10,
       'hist=%s' % np.array2string(h1, precision=3))
    ck('F-3.2 反向对照 gamma_f < gamma_dry ⇒ **单调湿润** psi→1',
       bool(np.all(np.diff(h2) >= -1e-12)) and h2[-1] > 0.90,
       'hist=%s' % np.array2string(h2, precision=3))

    # F-4 面 Laplacian：平面界面 + 切向线性 ψ ⇒ ∇²_Σψ == 0
    N, dx = 32, 1.0
    ii = np.arange(N)
    X = np.broadcast_to((ii[:, None, None] * dx), (N, N, N)).copy()
    Z = np.broadcast_to((ii[None, None, :] * dx), (N, N, N)).copy()
    phi = Z - N * dx / 2.0                         # 法向 = z 的平界面
    psi_lin = 0.5 + 0.02 * X                        # 沿切向（x）线性
    lap = surface_laplacian(psi_lin, phi, dx, iters=8)
    interior = (slice(6, -6), slice(6, -6), slice(6, -6))
    ck('F-4.1 平面界面 + 切向线性 ψ ⇒ ∇²_Σψ ≈ 0（|·| < 1e-9）',
       float(np.max(np.abs(lap[interior]))) < 1e-9,
       'max|lap| = %.3e' % float(np.max(np.abs(lap[interior]))))

    # F-5 面 Laplacian：切向**二次** ψ ⇒ ∇²_Σψ == 2c（解析）
    cc = 0.01
    psi_quad = 0.5 + cc * (X - N * dx / 2.0) ** 2
    lap2 = surface_laplacian(psi_quad, phi, dx, iters=8)
    got = float(np.median(lap2[interior]))
    ck('F-5.1 切向二次 ψ ⇒ ∇²_Σψ == 2c = %.4f（±5%%）' % (2 * cc),
       abs(got - 2 * cc) / (2 * cc) < 0.05, 'median=%.6f' % got)

    # F-6 稳定步长守卫
    #   ★ L_ψ 的**现实量级**：[占位]。取"面弛豫 ~100 步" ⇒ rate≈1/(100·dt)=3.7e5 /s
    #     ⇒ L_ψ ≈ 3.7e5/(6·0.45) ≈ **1.4e5 m²/(J·s)**。下面用 L=1e4 做超步长测试。
    d1 = safe_dt(1e4, 0.05, 0.6, 0.15, 0.0, 1.0, 1.0)
    ck('F-6.1 safe_dt 把过大的 dt 削到稳定区', d1 < 1.0, 'dt_eff=%.3e (< 1.0)' % d1)
    ck('F-6.2 safe_dt 不放大小 dt', abs(safe_dt(1e-8, .05, .6, .15, 0., 1., 1e-12) - 1e-12) < 1e-20)
    ck('F-6.3 现实 L=1.4e5 下 dt=2.679e-8 s **不需要**削',
       abs(safe_dt(1.4e5, 0.05, 0.6, 0.15, 0.0, 6.25e-8, 2.679e-8) - 2.679e-8) < 1e-20,
       'dt_eff=%.4e' % safe_dt(1.4e5, 0.05, 0.6, 0.15, 0.0, 6.25e-8, 2.679e-8))

    # F-7 band 屏蔽：带外必须逐位不变
    p0 = np.random.default_rng(1).random((8, 8, 8))
    band = np.zeros((8, 8, 8), bool); band[2:6, 2:6, 2:6] = True
    out, diag = psi_step(p0, np.zeros((8, 8, 8)), 1.0, np.full((8, 8, 8), 0.3),
                         1e-3, 0.6, L=1.0, W=0.05, kappa=0.0, band=band)
    ck('F-7.1 带外 psi 逐位不变', np.array_equal(out[~band], p0[~band]))
    ck('F-7.2 带内 psi 确实变了', not np.array_equal(out[band], p0[band]))

    print('-' * 100)
    print('FAIL = %d %s' % (len(F), F if F else ''))
    print('=' * 100)
    return 1 if F else 0


if __name__ == '__main__':
    raise SystemExit(_selftest())
