#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_auditR708_facetproj.py --- **审计用只读数值实验 v2**（不改任何主代码、不跑仿真）。

只做一件事：把 `_r68_facet_op.facet_project_one`（= `LevelSetMulti.facet_project()`
唯一的算子）的**后果逐个量出来**，每一项都给可复现的数。

v1 的教训（留档）：第一版用**中心对称**的圆盘做算例 ⇒ 支点漂移恒为 0，
**量具没有分辨力**（本项目纪律 P24/P47：负对照/量具必须先证明它有分辨力）。
v2 因此**故意用非对称、非凸**的构型。

量五项：
  M1 **凭空造/删体积**：算子自称"保体积标定"。量 `|V_after − V_before|/V_before`。
     物理后果：`region()` 一变，**界面自己动了** —— 这不是"保持形状"，是"改变形状"。
  M2 **质心漂移**：算子把盒子建在"体在各轴上的 min/max 中点"上，
     并把新场**重新居中到那个中点**。非对称体的质心 ≠ 中点 ⇒ 质心被搬走。
  M3 **尖棱离散曲率**：算子输出恒有 12 条尖棱。速度律 `v = M[Δf+Δed−stk·κ]`
     里的 `κ = div(∇φ/|∇φ|)` 在尖棱上**离散发散**（量级 ~1/Δx），
     而平面上的 `κ ≡ 0`。⇒ 同一张面上"平面罚 0、棱上罚 ~γ/Δx"，
     **惩罚强度由网格决定**（不是物理量）。量 `max|κ|·Δx` 与 `max|κ|` 的 Δx 标度。
  M4 **表示的凸性上限**：算子输出是 `K=3`（6 个法向）的**轴对齐盒子** ⇒ **凸**。
     量"投影前在体外、投影后在体内"的胞数（= 被**填平**的凹区）。
  M5 **幂等性（正对照）**：输入**本来就是**算子输出形状时应近似不变。
     这是必要的正对照 —— 若这一项也不过，说明算子连自己的不动点都不认。

运行（WSL，≤4 核，nice 10）：
  cd /mnt/f/speed_up/pipeline/ca_pf_framework
  OMP_NUM_THREADS=1 taskset -c 0-3 nice -n 10 \
    /root/miniconda3/envs/ml/bin/python -u _auditR708_facetproj.py
"""
import os
import sys

import numpy as np

# ⚠ 本文件归档在 `_r712_work/` ⇒ 它 import 的 `_r68_facet_op.py` 在**父目录**
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _r68_facet_op as FP          # noqa: E402


def kappa_abs(phi, dx):
    """`div(grad phi / |grad phi|)` 的**逐胞** |κ| 场（与 `curvature_of` 同式）。"""
    g = np.gradient(phi, dx, edge_order=2)
    gn = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
    out = None
    for i in range(3):
        ni = g[i] / gn
        di = (np.roll(ni, -1, axis=i) - np.roll(ni, 1, axis=i)) / (2.0 * dx)
        out = di if out is None else out + di
    return np.abs(out)


def kappa_max(phi, dx):
    """`max|κ|` 与 95 分位。"""
    a = kappa_abs(phi, dx)
    return float(a.max()), float(np.percentile(a, 95))


def body_stats(phi, dx):
    m = phi < 0
    n = int(m.sum())
    if n == 0:
        return None, 0
    idx = np.argwhere(m)
    return ((idx + 0.5).mean(0)) * dx, n


def grid(N, L):
    dx = L / N
    ii = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(ii, ii, ii, indexing='ij')
    return dx, X, Y, Z


def run_case(tag, N, L, mk, axes):
    dx, X, Y, Z = grid(N, L)
    phi0 = mk(N, L, dx, X, Y, Z)
    c0, n0 = body_stats(phi0, dx)
    k0max, k0p95 = kappa_max(phi0, dx)
    phin, info = FP.facet_project_one(phi0, dx, axes)
    c1, n1 = body_stats(phin, dx)
    k1max, k1p95 = kappa_max(phin, dx)
    dv = (n1 - n0) / max(n0, 1)
    dc = (np.linalg.norm(c1 - c0) if (c0 is not None and c1 is not None) else float('nan'))
    print('  %-26s V %6d -> %6d  (Δ %+7.2f%%)   |Δcom| = %6.2f nm (%5.2f dx)  '
          'max|κ| %8.3e -> %8.3e   κ·dx %5.3f -> %5.3f'
          % (tag, n0, n1, 100 * dv, dc * 1e9, dc / dx, k0max, k1max,
             k0max * dx, k1max * dx))
    return dict(tag=tag, N=N, dx=dx, v0=n0, v1=n1, dv=dv, dc=dc,
                k0=k0max, k1=k1max, k1x=k1max * dx, p95=(k0p95, k1p95))


def normal_quality(phi, dx):
    """界面法向质量（**这是 `M(n)` 的唯一输入**）。

    与 `advance()` 的口径一致：`ndir = ∇d/|∇d|`，`d = φ_k − φ_l`（此处取 d = φ）。
    量三件事（都在**零等值面带上** `|φ| <= 1.5·Δx`）：
      * `|∇φ|` 的中位 —— 单位 SDF 应为 1.000；偏离即"法向被污染"
      * 相邻胞法向夹角的**中位**与 **p90**（度）—— 真平面应 ≈ 0
      * `n·n*` 的分布 —— 刻面的判据是**大量胞取到同一个方向**
    """
    g = np.gradient(phi, dx, edge_order=2)
    gn = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
    band = np.abs(phi) <= 1.5 * dx
    if int(band.sum()) < 50:
        return None
    n = np.stack([gi / gn for gi in g], -1)
    n = n[band]
    gm = gn[band]
    # 相邻胞法向夹角（沿三轴，只取"带内与带内"的相邻对）
    angs = []
    for ax in range(3):
        nb = np.roll(band, -1, axis=ax)
        m = band & nb                                  # 两胞都在带内的相邻对
        if int(m.sum()) < 20:
            continue
        n_all = np.stack([gi / gn for gi in g], -1)
        n0 = n_all[m]
        n1 = n_all[np.roll(m, -1, axis=ax)]            # 同一对里的后一个胞
        c = np.clip(np.abs(np.einsum('ij,ij->i', n0, n1)), 0, 1)
        angs.append(np.degrees(np.arccos(c)))
    a = np.concatenate(angs) if angs else np.array([0.0])
    return dict(n=int(band.sum()), gmed=float(np.median(gm)),
                amed=float(np.median(a)), ap90=float(np.percentile(a, 90)))


def main():
    print('=' * 118)
    print('审计 R708 v2：`facet_project_one` 的五项量化')
    print('=' * 118)

    # ---------------- 算例定义（全部解析构造，与生产同轴约定）----------------
    nstar = np.array([0.0, 0.0, 1.0])
    wv = np.array([0.0, 1.0, 0.0])
    av = np.cross(wv, nstar)
    AX = (nstar, av, wv)

    def disc(N, L, dx, X, Y, Z):
        """生产形核胚口径：`sdf = max(|d|−t/2, rperp−R)`（尖边圆柱，shape='disc'）。"""
        ctr = np.array([L / 2] * 3)
        rel = np.stack([X - ctr[0], Y - ctr[1], Z - ctr[2]], -1)
        d = rel @ nstar
        rp = np.linalg.norm(rel - d[..., None] * nstar, axis=-1)
        return np.maximum(np.abs(d) - 0.45e-6 / 2, rp - 0.9e-6)

    def crescent(N, L, dx, X, Y, Z):
        """**非对称**体：圆盘在 +a 侧被咬掉一大口（模拟被邻片/弹性扭曲过的真实板条）。"""
        base = disc(N, L, dx, X, Y, Z)
        ctr = np.array([L / 2] * 3)
        e = (X - ctr[0]) * av[0] + (Y - ctr[1]) * av[1] + (Z - ctr[2]) * av[2]
        d = Z - ctr[2]
        rp = np.sqrt((X - ctr[0]) ** 2 + (Y - ctr[1]) ** 2)
        bite = np.maximum(np.abs(d) - 0.45e-6 / 2, np.sqrt((e - 0.55e-6) ** 2 + rp ** 2) - 0.75e-6)
        return np.maximum(base, -bite)          # 集合差：圆盘 \ 咬口

    def analytic_box(N, L, dx, X, Y, Z):
        """**算子自己的不动点形状**：沿 (n*, a, w) 的解析长方体（正对照用）。"""
        ctr = np.array([L / 2] * 3)
        rel = np.stack([X - ctr[0], Y - ctr[1], Z - ctr[2]], -1)
        pr = np.stack([rel @ nstar, rel @ av, rel @ wv], -1)
        hw = np.array([0.30e-6, 1.20e-6, 0.55e-6])       # 半宽 (n*, a, w)
        return np.max(np.abs(pr) - hw, axis=-1)

    print('\n【M1/M2/M3/M4】真实形状（生产口径 dx=62.5 nm, N=96, L=6 µm）')
    r1 = run_case('光滑圆盘（中心对称）', 96, 6.0e-6, disc, AX)
    r2 = run_case('月牙形（非对称、非凸）', 96, 6.0e-6, crescent, AX)

    print('\n【M5】正对照：输入本来就是"算子不动点"（解析长方体）——应近似不变')
    r3 = run_case('解析长方体', 96, 6.0e-6, analytic_box, AX)

    print('\n【M3 标度】max|κ| 随 Δx 的标度（N 变化、盒固定）——')
    print('          尖棱若真发散，max|κ|·Δx 应趋于常数（而不是 →0）；'
          '平面上的 κ 应为 0（盒面是平的）。')
    for N in (48, 64, 96, 128):
        dx, X, Y, Z = grid(N, 6.0e-6)
        ph = analytic_box(N, 6.0e-6, dx, X, Y, Z)
        phn, _ = FP.facet_project_one(ph, dx, AX)
        km, p95 = kappa_max(phn, dx)
        print('    N=%3d  Δx=%6.1f nm   max|κ| = %9.3e 1/m   max|κ|·Δx = %6.3f   '
              '1/Δx = %9.3e   ⇒ max|κ|/(1/Δx) = %6.3f'
              % (N, dx * 1e9, km, km * dx, 1.0 / dx, km * dx))

    print('\n【M3b 定位】κ 的"面 vs 棱"分解（解析长方体，三个分辨率）——')
    print('          盒子有 6 个平面 + 12 条棱。平面上的 κ 应 ≈ 0；'
          '若 95 分位随 Δx 增，说明被罚的是**棱/角**（它们占界面面积的少数）。')
    for N in (48, 96, 128):
        dx, X, Y, Z = grid(N, 6.0e-6)
        ph = analytic_box(N, 6.0e-6, dx, X, Y, Z)
        phn, _ = FP.facet_project_one(ph, dx, AX)
        a = kappa_abs(phn, dx)
        km, p95, med = float(a.max()), float(np.percentile(a, 95)), float(np.median(a))
        print('    N=%3d  Δx=%6.1f nm  max|κ|=%.3e  95%%=%.3e  中位=%.3e  '
              '⇒ p95·Δx=%.4f  中位·Δx=%.4f'
              % (N, dx * 1e9, km, p95, med, p95 * dx, med * dx))

    print('\n【M6 ★界面法向质量】`M(n) = M0·exp[−β_h(n·n*)² − β_w(n·w)²]` 的**唯一输入**。')
    print('     `|∇φ|` 中位应为 1.000（单位 SDF）；相邻胞法向夹角的中位应为 ≈0（光滑面）。')
    print('     生产口径：Δx=62.5 nm，N=96，L=6 µm。')
    for nm, mk in (('光滑圆盘（投影前）', disc),
                   ('光滑圆盘（投影后）', None),
                   ('解析长方体（= 算子不动点）', analytic_box)):
        dx, X, Y, Z = grid(96, 6.0e-6)
        ph = mk(96, 6.0e-6, dx, X, Y, Z) if mk is not None else None
        if ph is None:
            ph0 = disc(96, 6.0e-6, dx, X, Y, Z)
            ph, _ = FP.facet_project_one(ph0, dx, AX)
        q = normal_quality(ph, dx)
        if q is None:
            print('    %-30s 带上胞不足' % nm)
            continue
        print('    %-30s 带胞 %6d  |∇φ|中位 %6.4f  夹角中位 %6.2f°  夹角p90 %6.2f°'
              % (nm, q['n'], q['gmed'], q['amed'], q['ap90']))

    print('\n' + '=' * 118)
    print('读表口径（本脚本只报数）：')
    print('  M1  ΔV% ≠ 0        ⇒ 算子**改动了体积** ⇒ `region()` 变了 ⇒ 界面在"没算物理"的那一步动了。')
    print('  M2  |Δcom| ≠ 0     ⇒ 算子把质心搬走 ⇒ 几何重心与弹性/驱动力解耦（静默平移）。')
    print('  M3  max|κ|·Δx ≈ O(1) 且不随 Δx 衰减 ⇒ 尖棱上的曲率惩罚 **∝ 1/Δx**，')
    print('      即 `−stk·κ` 这一项在棱上的取值**由网格决定，不是物理量**（不收敛）。')
    print('  M4  投影把凹区填平（月牙形的 ΔV 明显大于凸体）⇒ 表示上限 = 凸多面体，`K=3`。')
    print('  M5  正对照：长方体上应 ΔV≈0、Δcom≈0；若这一项也不过，则算子连不动点都不认。')
    print('=' * 118)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
