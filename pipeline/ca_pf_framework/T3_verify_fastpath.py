#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T3_verify_fastpath.py --- T3「去空算 + 降内存」的**分项**等价性判据。

T3 改了四件事，本脚本**逐项**验证（不做整体对照，因为整体对照无法定位错在哪一项）：

  T3-1 **曲率的对角项**（`∂_i n_i` 只算对角 + 周期中心差分）
       · 判据 (a) 内部区域与旧写法（`np.gradient(n_i)[i]`，内部即中心差分）**逐位相同**
       · 判据 (b) 边界层两写法不同，且**新写法更接近解析值**（周期盒没有单边边界）
         —— 用解析 SDF `φ = |x−x0| − R`，其曲率在球面上恰为 `2/|x|`
  T3-2 **包围盒加速**（只在该场活跃胞的 bbox 内算）：bbox 内取值与**全盒**算的**逐位相同**
  T3-3 **`elastic_driving_pair`**（只算 winner/runner-up）：与 `elastic_driving()` 的
       对应分量相对差 < 1e-12（只是求和次序不同）
  T3-4 **Λ 低精度（float32）正对照**：`sigma` 与 `E_el` 相对误差 < 1e-5
  T3-5 **`_stefan` 早退**（k_part=1 且 surface_chem=False）：`c` 与 `Γ_mol` **逐位不变**

用法：python3 T3_verify_fastpath.py [--N 48]
退出码：0 = PASS
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, PF3D, _lam_full               # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
_rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(300, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn


def curv_old(g, k):
    """旧版曲率（T3 之前）：全盒 np.gradient(edge_order=2)，3 个偏导全算。"""
    gg = np.gradient(g.phi[k], g.dx, edge_order=2)
    gn = np.sqrt(sum(gi ** 2 for gi in gg)) + 1e-30
    n = [gi / gn for gi in gg]
    return sum(np.gradient(n[i], g.dx, edge_order=2)[i] for i in range(3))


def mk(N, dx, nseed=3, seed=4):
    L = N * dx
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                        df=[0.0] + [2.0e8] * NV, workers=1, reinit_every=0)
    rng = np.random.default_rng(seed)
    R = 0.16 * L
    ns = 0
    while ns < nseed:
        c = rng.random(3) * (L - 2 * R) + R
        try:
            g.seed_plate(int(rng.integers(1, NV + 1)), c, NPF[1], R, 4 * dx)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    return g


def t3_1(N, dx):
    print('【T3-1】曲率对角项：内部逐位相同 + 边界更接近解析值')
    L = N * dx
    g = mk(N, dx, nseed=1)
    x0 = np.array([L / 2] * 3)
    R = 0.3 * L
    r = np.linalg.norm(g.XYZ - x0, axis=-1)
    g.phi[1] = r - R
    g.init_parent()
    k_new = g.curvature_of(1)
    k_old = curv_old(g, 1)
    # 内部（去掉首末 2 层）
    sl = tuple(slice(2, -2) for _ in range(3))
    d_in = float(np.max(np.abs(k_new[sl] - k_old[sl])))
    # 边界层
    bnd = np.ones((N, N, N), bool)
    bnd[sl] = False
    d_bnd = float(np.max(np.abs(k_new[bnd] - k_old[bnd])))
    # 解析值：球面 |x|=R 上 div(grad|r-R|) = 2/r；取 r∈[0.8R,1.2R] 的壳
    shell = (r > 0.8 * R) & (r < 1.2 * R)
    err_new = float(np.max(np.abs(k_new[shell] - 2.0 / r[shell])))
    err_old = float(np.max(np.abs(k_old[shell] - 2.0 / r[shell])))
    print('   内部 max|Δκ| = %.3e（应 = 0，逐位）;  边界层 max|Δκ| = %.3e' % (d_in, d_bnd))
    print('   对解析 2/r 的最大偏差：新 = %.4e   旧 = %.4e   （新应 ≤ 旧）'
          % (err_new, err_old))
    ok = (d_in == 0.0) and (err_new <= err_old * 1.0000001)
    print('   T3-1: %s' % ('PASS' if ok else 'FAIL'))
    return ok


def t3_2(N, dx):
    print('【T3-2】包围盒加速：bbox 内取值与全盒算的逐位相同')
    g = mk(N, dx, nseed=5)
    order = np.argsort(g.phi, axis=0)
    karr, larr = order[0], order[1]
    ok = True
    worst = 0.0
    act = np.unique(np.concatenate((np.unique(karr), np.unique(larr))))
    for k in act:
        k = int(k)
        mw = (karr == k)
        ml = (larr == k)
        mk_ = mw | ml
        bb = W._bbox_pad(mk_, 2)
        # 全盒
        gfull = np.gradient(g.phi[k], g.dx, edge_order=2)
        gnf = np.sqrt(sum(t ** 2 for t in gfull)) + 1e-30
        kfull = g.curvature_of(k, grad=gfull, gn=gnf)
        sfull = g._stiff_of(k, gfull, gnf, NPF, 0.4, None, True, 0.0, 0.05)
        # k=0（母相）没有 npref ⇒ `_stiff_of` 返回**标量** γ（原代码用 `stiff[k]=gk` 广播）
        if np.ndim(sfull) == 0:
            sfull = np.full(g.phi[k].shape, float(sfull))
        # 子盒
        gsub = np.gradient(g.phi[k][bb], g.dx, edge_order=2)
        gnsub = np.sqrt(sum(t ** 2 for t in gsub)) + 1e-30
        ksub = g.curvature_of(k, grad=gsub, gn=gnsub)
        ssub = g._stiff_of(k, gsub, gnsub, NPF, 0.4, None, True, 0.0, 0.05)
        if np.ndim(ssub) == 0:
            ssub = np.full(gsub[0].shape, float(ssub))
        dk = float(np.max(np.abs(ksub[mk_[bb]] - kfull[bb][mk_[bb]])))
        ds = float(np.max(np.abs(ssub[mk_[bb]] - sfull[bb][mk_[bb]])))
        worst = max(worst, dk, ds)
        ok &= (dk == 0.0) and (ds == 0.0)
    print('   跨 %d 个活跃场：max|Δκ| 与 max|Δγ*| 的最大值 = %.3e（须逐位 0）'
          % (act.size, worst))
    print('   T3-2: %s' % ('PASS' if ok else 'FAIL'))
    return ok


def t3_3(N, dx):
    print('【T3-3】elastic_driving_pair 与 elastic_driving 的对应分量一致')
    g = mk(N, dx, nseed=5)
    order = np.argsort(g.phi, axis=0)
    karr, larr = order[0], order[1]
    ed = g.elastic_driving()
    ek, el = g.elastic_driving_pair(karr, larr)
    rk = float(np.max(np.abs(ek - np.take_along_axis(ed, karr[None], 0)[0])))
    rl = float(np.max(np.abs(el - np.take_along_axis(ed, larr[None], 0)[0])))
    sc = max(float(np.max(np.abs(ed))), 1e-30)
    print('   max|Δed_winner| = %.3e  max|Δed_runner| = %.3e  (尺度 %.3e ⇒ 相对 %.2e)'
          % (rk, rl, sc, max(rk, rl) / sc))
    ok = max(rk, rl) / sc < 1e-12
    print('   T3-3: %s' % ('PASS' if ok else 'FAIL'))
    return ok


def t3_4(N, dx):
    """★ 本条是**负面对照**（判决"低精度 Λ 不可用"），不是"等价性"判据。

    背景：原计划要"Λ 存 complex64"以省 144 B/胞。实测判决 **不可用**：
      `Lam` 的元素量级 **1.2e10–1.3e11**（不是 O(1)），而 σ 是 6 项**大数相消**的结果
      ⇒ float32 存 + float32 einsum 给出点位 σ 相对误差 RMS **0.70**、max **0.50**，
        **界面带内 100% 的胞 `ed` 误差 > 1%**（会直接污染界面速度）。
      ⚠ 陷阱：`|ΔE_el|/E_el` 只有 **1.9e-9** —— 能量由精确的低 k 模态主导，
        **只看能量判据会放过这个错**。
    ⇒ 生产默认取 `lam_prec='f64'`；本判据要求 f32 的误差**确实超标**（证明拒绝有依据）。
    """
    print('【T3-4】负面对照：低精度 Λ 必须被**拒绝**（原计划的 complex64 方案）')
    g = mk(N, dx, nseed=5)
    reg = g.region()

    def calc(prec):
        p = PF3D(N, g.L, C, EPS0, gamma=0.0, w90=1e-8, Lmob=0.0,
                 workers=1, k0_mode='clamped', lam_prec=prec)
        return p.sigma_tensor(reg), float(p.E_el()), p

    s64, e64, p64 = calc('f64')
    s32, e32, p32 = calc('f32')
    d = np.abs(s32 - s64)
    sm = max(float(np.max(np.abs(s64))), 1e-30)
    rms = float(np.sqrt(np.mean(d ** 2)) / np.sqrt(np.mean(s64 ** 2)))
    de = abs(e32 - e64) / max(abs(e64), 1e-30)
    print('   Lam 元素量级 median/max = %.3e / %.3e（不是 O(1) ⇒ 大数相消）'
          % (np.median(np.abs(p64.Lam)), np.max(np.abs(p64.Lam))))
    print('   f32: max|Δσ|/max|σ| = %.3f ; RMS 相对 = %.3f' % (d.max() / sm, rms))
    print('   ⚠ 同时 |ΔE_el|/E_el = %.3e（**只有能量会显得没问题**）' % de)
    bad = (d.max() / sm > 1e-5) or (rms > 1e-5)
    print('   ⇒ 低精度 Λ 误差确实超标（须为真，故拒绝）：%s' % ('PASS' if bad else 'FAIL'))
    print('   T3-4: %s' % ('PASS' if bad else 'FAIL'))
    return bad


def t3_5(N, dx):
    print('【T3-5】_stefan 早退（k_part=1 且 surface_chem=False）的逐位等价性')
    g = mk(N, dx, nseed=3)
    g.c[:] = 0.036
    c0 = g.c.copy()
    dt = 0.15 * dx / (1e-9 * 2.0e8)
    for _ in range(4):
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5)
    dc = float(np.max(np.abs(g.c - c0)))
    dg = float(np.max(np.abs(g.Gam_mol)))
    print('   max|c−c0| = %.3e（须逐位 0）;  max|Γ_mol| = %.3e（须逐位 0）' % (dc, dg))
    ok = (dc == 0.0) and (dg == 0.0)
    print('   T3-5: %s' % ('PASS' if ok else 'FAIL'))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=48)
    ap.add_argument('--dx-nm', type=float, default=25.0)
    a = ap.parse_args()
    N, dx = a.N, a.dx_nm * 1e-9
    print('=' * 96)
    print('T3 —— 去空算/降内存的**分项**等价性判据   N=%d dx=%.0f nm' % (N, a.dx_nm))
    print('=' * 96)
    r = [('T3-1', t3_1(N, dx)), ('T3-2', t3_2(N, dx)), ('T3-3', t3_3(N, dx)),
         ('T3-4', t3_4(N, dx)), ('T3-5', t3_5(N, dx))]
    print()
    print('=' * 96)
    for n, ok in r:
        print('  %-6s %s' % (n, 'PASS' if ok else 'FAIL'))
    allok = all(ok for _n, ok in r)
    print('  ⇒ T3 等价性 %s' % ('PASS' if allok else 'FAIL'))
    print('=' * 96)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
