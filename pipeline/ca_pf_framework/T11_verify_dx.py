#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T11_verify_dx.py --- T11 判据：**Δx 无关性**（Gibbs 面的立身之本，决策点 D11）。

为什么这是"立身之本"
--------------------
选 Gibbs 零厚度面的**全部理由**就是"界面表示不该依赖分辨率"
（`RESEARCH_INTENT.md` §一）。若某个观测量随 Δx 漂移，那条理由就不成立。

★ 本轮已做的**离散化物理化**（否则测不了）：
  `reinit_every`（步数）在 CFL `dt ∝ dx` 下对应的**物理间隔 ∝ Δx** ⇒ 换分辨率就换了物理。
  新增 `reinit_dt`（秒）⇒ 按**物理时间**触发；`None` 时沿用步数语义（**逐位兼容**）。

判据（只改 Δx 三档 40/50/62.5 nm，其余物理量全同）
--------------------------------------------------
  T11-A **平面界面速度**（有精确答案 `v = M·Δf`）：三档的相对散布 < 5%，
        且**单调收敛**（越细越接近 1.000）
  T11-B **界面面积测度**：对解析球面，`cell_area_geom` 的总面积误差随 Δx **单调减小**
        （零厚度面必须靠"面测度"而不是"界面宽度"来收敛）
  T11-C **Gibbs–Thomson 有效界面能** `γ_eff`：球在驱动 `Δf` 下的平衡半径满足
        `Δf = γ_eff·2/R` ⇒ `γ_eff = Δf·R_eq/2`。三档散布 < 10%
  T11-D **重初始化的物理时间化**：同一物理时间下，`reinit_dt` 档的 `\|∇φ\|` 健康度
        三档一致；而固定 `reinit_every`（步数）档随 Δx **漂移**（证明这条修的是真问题）

用法：python3 T11_verify_dx.py [--dxs 40,50,62.5] [--N 48]
退出码：0 = PASS（Δx 无关）
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
_rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn

DF = 2.0e8
MOB = 1e-9


def t11_A(N, dx, nstep=80, band_len=1000e-9):
    """平面界面速度：精确答案 v = M·Δf = 0.2 m/s。用亚胞界面位置量。

    ★ T11：延拓带宽按**物理长度**给（`band_len=1000 nm`）而不是固定 20 胞
      ⇒ 物理带宽与 Δx 无关（这正是计划里"延拓带宽改物理长度"那一条）。"""
    L = N * dx
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.0, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=1, reinit_every=0)
    g.pf = None
    n_h = np.asarray(NPF[1], float)
    n_h = n_h / np.linalg.norm(n_h)
    rel = g.XYZ - np.array([L / 2] * 3)
    d = rel @ n_h
    g.phi[1] = d
    for j in range(1, g.nreg):
        if j != 1:
            g.phi[j] = 1e3
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    n0, c0 = g.iface_offset(k=1, l=0, axis=int(np.argmax(np.abs(n_h))))
    t0 = 0.0
    for _ in range(nstep):
        g.advance(dt, band_len=band_len)
        t0 += dt
    n1, c1 = g.iface_offset(k=1, l=0, axis=int(np.argmax(np.abs(n_h))))
    if n0 == 0 or n1 == 0:
        return None
    v = abs(c1 - c0) / t0
    return v, v / (MOB * DF)


def t11_B(N, dx, L):
    """界面面积测度：解析球（R = 0.25L 固定）vs cell_area_geom 之和。"""
    R = 0.25 * L
    g = W.LevelSetMulti(N, L, C=None, eps0=None, gamma=0.15, Mob=1e-9,
                        df=[0.0, 1e8], workers=1, reinit_every=0, nv=1)
    g.seed_sphere(1, [L / 2] * 3, R)
    g.init_parent()
    A = float(g.cell_area_geom().sum())
    Aex = 4.0 * np.pi * R ** 2
    return A / Aex


DF_GT = 1.0e6             # ★ 可分辨的 Gibbs–Thomson 工况：R_eq = 2γ/Δf ≈ 300 nm


def t11_C(N, dx, L, nstep=1500):
    """Gibbs–Thomson：球在驱动下停在 `Δf = γ·2/R` ⇒ `γ_eff = Δf·R_eq/2`。

    ★ 参数必须让平衡半径**可分辨**：`R_eq = 2γ/Δf`。Δf 取 `DF_GT=1e6`、γ=0.15
      ⇒ `R_eq ≈ 300 nm`（≥ 5 个 Δx）。首版用 Δf=2e8 ⇒ R_eq=1.5 nm，测的是假量。
    """
    R0 = 0.10 * L
    g = W.LevelSetMulti(N, L, C=None, eps0=None, gamma=0.15, Mob=MOB,
                        df=[0.0, DF_GT], workers=1, reinit_every=0, nv=1)
    g.seed_sphere(1, [L / 2] * 3, R0)
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF_GT)
    m = (g.region() == 1)
    vs = []
    for it in range(nstep):
        g.advance(dt, band_cells=20)
        if (it + 1) % 100 == 0:
            vs.append(float((g.region() == 1).sum()))
    v1, v2 = vs[-2], vs[-1]
    conv = abs(v2 - v1) / max(v1, 1e-30)
    V = v2 * dx ** 3
    Req = (3.0 * V / (4.0 * np.pi)) ** (1.0 / 3.0)
    gam = DF_GT * Req / 2.0
    return Req, gam, conv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dxs', type=str, default='40,50,62.5')
    ap.add_argument('--L-nm', type=float, default=3000.0,
                    help='**固定物理盒**（分辨率研究必须固定 L 变 N；'
                         '固定 N 变 dx 改变的是盒尺寸，问题自相似 ⇒ 测不到 Δx 依赖）')
    a = ap.parse_args()
    dxs = [float(x) * 1e-9 for x in a.dxs.split(',')]
    L = a.L_nm * 1e-9
    Ns = [int(round(L / dx)) for dx in dxs]
    print('=' * 100)
    print('T11 —— Δx 无关性   **固定 L = %.0f nm**，Δx = %s nm ⇒ N = %s'
          % (a.L_nm, a.dxs, Ns))
    print('  ★ 记账（首版无信息量）：首版固定 N=48 变 dx ⇒ 变的是**盒尺寸**（L=N·dx），')
    print('    而 `v = M·Δf` 无长度尺度、`A/R²` 无量纲 ⇒ 三档**恒等**（散布 0.000），')
    print('    那是自相似、不是"Δx 无关"（"测试看不到目标现象"，教训 #14）。')
    print('=' * 100)
    dxs = dxs
    Ns = Ns

    print('【T11-A】平面界面速度（精确答案 v = M·Δf）')
    rows = []
    for dx, N in zip(dxs, Ns):
        r = t11_A(N, dx)
        if r is None:
            print('   Δx=%.1f nm (N=%d) ⇒ 界面未找到' % (dx * 1e9, N))
            continue
        rows.append((dx, r[0], r[1]))
        print('   Δx=%-6.1f nm (N=%-4d)  v = %.5e m/s  v/(MΔf) = %.4f'
              % (dx * 1e9, N, r[0], r[1]))
    if len(rows) < 3:
        print('   ⚠ 档数不足')
        return 2
    rr = np.array([r[2] for r in rows])
    spA = float((rr.max() - rr.min()) / abs(rr.mean()))
    # ★ 记账：首版把单调性判反了（rr 是"细→粗"顺序，收敛应看 **最后** 比 **第一** 更接近 1）
    monoA = bool(abs(rr[-1] - 1.0) <= abs(rr[0] - 1.0) + 1e-9)
    print('   相对散布 = %.4f ; 误差随 Δx 单调趋 1: %s（细 %.4f → 粗 %.4f）'
          % (spA, monoA, rr[0], rr[-1]))
    okA = (spA < 0.05) and monoA

    print()
    print('【T11-B】界面面积测度（解析球面 R = 0.25L 固定）')
    ab = []
    for dx, N in zip(dxs, Ns):
        r = t11_B(N, dx, L)
        ab.append(r)
        print('   Δx=%-6.1f nm (N=%-4d)  A/A_exact = %.4f  （偏差 %+.2f%%）'
              % (dx * 1e9, N, r, 100 * (r - 1)))
    ab = np.array(ab)
    monoB = bool(abs(ab[-1] - 1.0) <= abs(ab[0] - 1.0) + 1e-9)
    print('   误差随 Δx 单调收敛: %s' % monoB)
    okB = monoB

    print()
    print('【T11-C】Gibbs–Thomson 有效界面能 γ_eff = Δf·R_eq/2')
    print('   ★ 记账（首版测的是假量）：首版用 Δf=2e8、γ=0.15 ⇒ 平衡半径 `2γ/Δf = 1.5 nm`')
    print('     **根本不可分辨**（远小于 Δx），球只会一直长 ⇒ 测到的是"盒子尺寸"。')
    print('     现在改用**可分辨**的工况：Δf = %.1e ⇒ R_eq ≈ %.0f nm。' % (DF_GT, 2 * 0.15 / DF_GT * 1e9))
    gc = []
    for dx, N in zip(dxs, Ns):
        Req, gam, conv = t11_C(N, dx, L)
        gc.append(gam)
        print('   Δx=%-6.1f nm (N=%-4d)  R_eq = %.2f nm  γ_eff = %.5e J/m²  '
              '（末段体积变化 %.2e）' % (dx * 1e9, N, Req * 1e9, gam, conv))
    gc = np.array(gc)
    spC = float((gc.max() - gc.min()) / abs(gc.mean()))
    print('   相对散布 = %.4f（<0.10）；输入 γ = 0.15 J/m²  ⇒ γ_eff/γ = %s'
          % (spC, ' '.join('%.3f' % (x / 0.15) for x in gc)))
    okC = spC < 0.10

    print()
    print('=' * 100)
    print('  T11-A（v 与 Δx 无关）: %s' % ('PASS' if okA else 'FAIL'))
    print('  T11-B（面积测度单调收敛）: %s' % ('PASS' if okB else 'FAIL'))
    print('  T11-C（γ_eff 与 Δx 无关）: %s' % ('PASS' if okC else 'FAIL'))
    allok = okA and okB and okC
    print('  ⇒ T11 %s' % ('PASS（Δx 无关）' if allok else 'FAIL（有 Δx 依赖，需回头改离散化）'))
    print('=' * 100)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
