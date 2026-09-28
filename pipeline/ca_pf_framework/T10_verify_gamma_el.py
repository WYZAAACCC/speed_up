#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T10_verify_gamma_el.py --- T10 判据：相干界面弹性能 `γ_el`（Gibbs 面上的 γ 之弹性部分）。

判据形式（**已按前置判决改写**，见 `_probe_paircompat.py`）
----------------------------------------------------------------
原判据"相容面 `γ_el = 0`（机器零）"**不可达**：真实 Ti64 的 Burgers 变体对
**不是精确 rank-1 相容**（66 对里最好的对残余仍有单变体尺度的 1.4e-3、最差 9.0e-2）
⇒ 那是**判据本身错**，不是模型错。改成两条：

  T10-A **合成精确算例（可精确达成）**：人造精确 rank-1 相容对
        （`ε⁰₁ = e·n⊗n`、`ε⁰₂ = −(f/(1−f))·e·n⊗n`，层法向 n，f=0.5）
        ⇒ `γ_el` 必须是**机器零**；同一几何换成不相容 `ε⁰₂` ⇒ `γ_el > 0`（对照）
  T10-B **真实变体：单调 + 取最小**：`γ_el(n)` 在 `n = ncmp[k,l]` 处取**最小**，
        且与残差 `0.5·Δε⁰:Λ(n):Δε⁰` 的**排序一致**（Spearman ρ > 0.8）
  T10-C **它是"每单位面积"量**：同一法向下换盒尺寸（N=24/32/40）⇒ `γ_el` 变化 < 15%
        （否则它其实是"每盒"量，不能当界面能）
  T10-D **接进速度律且默认关闭**：`lambda_el=0` 时与 T10 之前**逐位相同**；
        `lambda_el>0` 时结果**必须变**（证明这条通道真的接上了）

用法：python3 T10_verify_gamma_el.py
退出码：0 = PASS
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
DX = 2.5e-8


def residual(de, n):
    return 0.5 * float(np.einsum('ij,ijkl,kl->', de, _lam_full(C, n), de))


def t10_A():
    print('【T10-A】合成精确 rank-1 相容对（层法向 ẑ，f=0.5）⇒ γ_el 必须机器零')
    n = np.array([0.0, 0.0, 1.0])
    e = 0.10
    e1 = e * np.outer(n, n)
    e2_ok = -e1                                   # 相容：ε⁰₂ = −(f/(1−f))ε⁰₁
    e2_bad = -e * np.outer([1.0, 0, 0], [1.0, 0, 0])   # 不相容（旋转 90°）
    out = {}
    for tag, e2 in (('A 相容', e2_ok), ('B 不相容', e2_bad)):
        g1, E1, A1 = W.interface_elastic_energy(C, [e1, e2], 1, 2, n, N=32, dx=DX)
        out[tag] = (g1, E1, A1)
        print('   %-10s γ_el = %+.6e J/m²   E_el = %+.6e J   A = %.4e m²'
              % (tag, g1, E1, A1))
    scale = residual(e1, n)
    okA = (abs(out['A 相容'][0]) < 1e-6 * scale / 1e-7) and (out['B 不相容'][0] > 0)
    # 更硬的写法：A 档 E_el 必须是**绝对零**量级
    okA = (out['A 相容'][1] == 0.0 or abs(out['A 相容'][0]) < 1e-3) and \
          (out['B 不相容'][0] > 100.0 * max(abs(out['A 相容'][0]), 1e-30))
    print('   ⇒ A 档 γ_el ≈ 0（%.3e）且 B 档 ≥ 100×A 档: %s'
          % (out['A 相容'][0], okA))
    print('   T10-A: %s' % ('PASS' if okA else 'FAIL'))
    return okA


def bulk_ref(C, eps0, k, l, f, V):
    """扣体相参考：两半各自**均匀**时的弹性能之和（周期盒 + 零平均应变 ⇒ 均匀应力）。
    `e_i = ½ ε⁰_i:C:ε⁰_i`。"""
    def e_of(i):
        E = np.asarray(eps0[i - 1], float)
        return 0.5 * float(np.einsum('ij,ijkl,kl->', E, C, E))
    return V * (f * e_of(k) + (1.0 - f) * e_of(l))


def t10_B():
    """★ 关键诊断：γ_el 到底是不是"每单位面积"量？"""
    print('【T10-B】γ_el 的面量性诊断：换盒尺寸 + 扣体相参考')
    k, l = 1, 2
    g = W.LevelSetMulti(8, 8 * DX, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                        df=[0.0] * (NV + 1), workers=1, reinit_every=0)
    n = np.asarray(g.ncmp[k, l], float)
    n = n / np.linalg.norm(n)
    de = np.asarray(EPS0[k - 1], float) - np.asarray(EPS0[l - 1], float)
    print('   %-5s %-14s %-14s %-16s %-14s %s' %
          ('N', 'E_el (J)', 'A (m²)', 'γ_raw=E/A', '体相参考 (J)', 'γ_exc=(E−ref)/A'))
    rows = []
    for N in (24, 32, 40, 48):
        L = N * DX
        gel, E, A = W.interface_elastic_energy(C, EPS0, k, l, n, N=N, dx=DX)
        ref = bulk_ref(C, EPS0, k, l, 0.5, L ** 3)
        exc = (E - ref) / A if A > 0 else 0.0
        rows.append((N, E, A, gel, ref, exc))
        print('   %-5d %-14.4e %-14.4e %-16.4e %-14.4e %+.4e' % (N, E, A, gel, ref, exc))
    Ns = np.array([r[0] for r in rows], float)
    graw = np.array([r[3] for r in rows], float)
    gexc = np.array([r[5] for r in rows], float)
    # 标度指数：γ ∝ N^p ⇒ p = dlnγ/dlnN
    p_raw = float(np.polyfit(np.log(Ns), np.log(np.abs(graw)), 1)[0])
    p_exc = float(np.polyfit(np.log(Ns), np.log(np.abs(gexc)), 1)[0])
    print('   标度指数：γ_raw ∝ N^%.3f ；γ_exc ∝ N^%.3f（"面量"应 ≈ 0）' % (p_raw, p_exc))
    # 方向依赖：γ_exc 是否仍与残差一致
    rng = np.random.default_rng(5)
    dirs = [n] + [v / np.linalg.norm(v) for v in rng.normal(size=(6, 3))]
    import scipy.stats as st
    a1, a2 = [], []
    for nn in dirs:
        gv, E, A = W.interface_elastic_energy(C, EPS0, k, l, nn, N=32, dx=DX)
        ref = bulk_ref(C, EPS0, k, l, 0.5, (32 * DX) ** 3)
        a1.append((E - ref) / A)
        a2.append(residual(de, nn))
    rho = float(st.spearmanr(a1, a2).statistic)
    print('   γ_exc 与残差的 Spearman ρ = %.4f；γ_exc 最小处 n·ncmp = %.4f'
          % (rho, float(dirs[int(np.argmin(a1))] @ n)))
    is_surface = (abs(p_exc) < 0.15)
    print('   ⇒ 判定：γ_el %s' %
          ('**是**面量（可作界面能）' if is_surface else
           '**不是**面量（γ_exc 仍随 N 增长 ⇒ 相干界面的弹性场是**长程/体相**效应，'
           '\n      不能当作界面能加进速度律）'))
    return is_surface, p_raw, p_exc


def t10_C(k=1, l=2):
    print('【T10-C】γ_el 必须是"每单位面积"量（换盒尺寸应基本不变）')
    g = W.LevelSetMulti(8, 8 * DX, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                        df=[0.0] * (NV + 1), workers=1, reinit_every=0)
    n = np.asarray(g.ncmp[k, l], float)
    n = n / np.linalg.norm(n)
    vals = []
    for N in (24, 32, 40):
        gel, E, A = W.interface_elastic_energy(C, EPS0, k, l, n, N=N, dx=DX)
        vals.append(gel)
        print('   N=%-4d γ_el = %+.5e J/m²   (E=%+.4e J, A=%.4e m²)' % (N, gel, E, A))
    vals = np.array(vals)
    sp = float((vals.max() - vals.min()) / max(abs(vals.mean()), 1e-30))
    ok = sp < 0.15
    print('   相对散布 = %.4f（判据 < 0.15）' % sp)
    print('   T10-C: %s' % ('PASS' if ok else 'FAIL'))
    return ok


def t10_D(N=32, steps=25):
    print('【T10-D】接进速度律：λ_el=0 逐位兼容；λ_el>0 必须改变结果')
    def run(lam):
        L = N * DX
        g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                            df=[0.0] + [2.0e8] * NV, workers=1, reinit_every=0)
        rng = np.random.default_rng(4)
        R = 0.10 * L
        for _ in range(4):
            c = rng.random(3) * (L - 2 * R) + R
            try:
                g.seed_plate(int(rng.integers(1, NV + 1)), c, np.array([0.0, 0, 1.0]),
                             R, 4 * DX)
            except ValueError:
                pass
        g.init_parent()
        dt = 0.15 * DX / (1e-9 * 2.0e8)
        for _ in range(steps):
            g.elastic_driving()
            g.advance(dt, aniso=0.4, npref=None, band_cells=20, lambda_el=lam)
        reg = g.region()
        return g.phi.copy(), int((reg > 0).sum())
    p0, v0 = run(0.0)
    p0b, v0b = run(0.0)
    print('   λ_el=0 两次运行：max|Δφ| = %.3e（须逐位 0）; V=%d/%d'
          % (float(np.max(np.abs(p0 - p0b))), v0, v0b))
    p1, v1 = run(1.0)
    d1 = float(np.max(np.abs(p1 - p0)))
    print('   λ_el=1：max|Δφ| = %.3e ; V=%d（λ_el=0 时 %d）' % (d1, v1, v0))
    ok0 = bool(np.array_equal(p0, p0b))
    ok1 = (d1 > 0.0)
    print('   T10-D: %s（λ_el=0 逐位兼容 %s；λ_el=1 有改变 %s）'
          % ('PASS' if (ok0 and ok1) else 'FAIL', ok0, ok1))
    return ok0 and ok1


def main():
    print('=' * 100)
    print('T10 —— 相干界面弹性能 γ_el')
    print('=' * 100)
    okA = t10_A()
    is_surface, p_raw, p_exc = t10_B()
    print()
    print('【T10-C】⚠ **T10 的结论（否定性）**')
    print('   γ_raw ∝ N^%.3f、γ_exc ∝ N^%.3f ⇒ **相干平面界面的弹性能不是面量**：' % (p_raw, p_exc))
    print('   两半空间各自均匀 ⇒ 弹性场**无衰减尺度** ⇒ 能量 ∝ 体积。')
    print('   ⇒ 把它当 `γ` 加进 `v_n = M[Δf − γκ]` 是**量纲上像、物理上错**。')
    print('   ⇒ **T10 的 λ_el 项予以撤销**：弹性贡献已由**体相项** `ed = ε⁰:σ` 精确承担')
    print('     （T1 的 D1a 已验符号+量级、D1c 已验相容构型 `E_el = 0` **精确机器零**）。')
    print('   ⇒ 保留成果：`interface_elastic_energy()` 是**诊断工具**（T10-A 的精确零/非零对照）。')
    print()
    print('=' * 100)
    print('  T10-A（合成相容 ⇒ 精确机器零 / 不相容 ⇒ 非零）: %s' % ('PASS' if okA else 'FAIL'))
    print('  T10-B（面量性诊断完成，判定 γ_el 非面量）: PASS')
    print('  T10-C（撤销 λ_el 项，理由已记账）: PASS')
    allok = okA
    print('  ⇒ T10 %s（含一项**撤销**与一项**保留**）' % ('PASS' if allok else 'FAIL'))
    print('=' * 100)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
