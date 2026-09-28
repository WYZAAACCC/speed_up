#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T1_verify_edsign.py --- T1 判据：弹性驱动力 `ed` 的**符号**（P0-1）。

判据（出自 `WINDOWB_P0_REGISTER.md` §P0-1「修后必过的判据」，本脚本按实测修订）：

  D1a  `ed` 与正确驱动力 `D_corr = -dE_el/dV` **同号**，且比值落在判据带内
  D1b  **反向对照**：把符号翻回去 ⇒ 判据必须 FAIL（证明判据有分辨力）
  D1c  **相容配置下 ed 必须为机器零**（合成精确算例，单变量对照）
  D1d  A0/A1 式「疯长」消失（弹性项必须**反对**转变）

本版相对首版的**两处修订**（都是"这个测试能不能看到目标现象"，本项目教训 #14）：

  (1) **D1a 的 D_corr 改用自相似恒等式 `D_corr = -E_el/V`，不再用有限差分。**
      理由：有限差分对 `dR` 不收敛 —— 实测球 R=120 nm 上
        dR= 4 nm ⇒ dE/dR = 2.701e-5 ;  dR=20 nm ⇒ 3.895e-5   （差 44%！）
      而 `dR < dx` 时体素集合可能**逐位不变** ⇒ dE/dR ≡ 0 是**离散化假象**
      （审计的 plate 档就是这样：t=120 与 124 nm 都给 672 胞、E_el 逐位相同）。
      自相似恒等式来自：椭球内含物的 σ **与尺寸无关**（Eshelby）⇒ E_el ∝ V
      ⇒ dE_el/dV = E_el/V。**实测校验**：球档 3E/R = 3.841e-5 vs 差分 3.895e-5（差 1.4%）✓。
      另附**精确能量关系**做交叉验证：`<ed>_Ω = -2 E_el / V_Ω`
      （由 F_el = -½∫_Ω ε⁰:σ dV 得来；实测球/板都吻合到 <1%）。

  (2) **D1c 改用真正的无限平板**（面内半径 R ≫ L，铺满整盒 ⇒ 周期意义下无限）
      + **合成 ε⁰**（有精确答案）。首版用 Ti64 真实变体 + R=t=120 nm 的"板"，
      那其实是**等轴圆盘**，边缘区应力永远存在 ⇒ `|ed|/|Δf| < 1e-2` **物理上不可能达到**。
      实测：等轴形状 E_el/vol ≈ 2.1e8 J/m³ 且与形状/尺寸无关（`_probe_Eel_vs_t.py`）。

记账（本脚本实测出来的、影响后续 T 的事实）：
  * **界面带均值 `ed_band` ≈ 0.78 × D_corr**（dx=20 nm, R=120 nm），
    而**变体内均值** `ed_interior` = **2.0 × D_corr**（逐位吻合 -2E/V）。
    ⇒ 二者之差不是 bug，而是：`∂F/∂φ` 在**母相一侧**取值才是正确的 `-dF/dV`
    （变分：dF = -∫_{δΩ} ε⁰:σ dV，δΩ 是界面**外侧**薄壳），而带内均值跨了两侧。
    ⇒ **这是一个分辨率相关的离散偏差，必须在 T11（Δx 无关性）里收敛掉**，
      本脚本用 dx 扫描给出它的收敛趋势。

用法：
    python3 T1_verify_edsign.py                 # D1a/D1b/D1c（快，~2 min）
    python3 T1_verify_edsign.py --growth        # 追加 D1d
退出码：0 = 全部 PASS 且 D1b 确认 FAIL；1 = 有判据未过。
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
K = 1                                                           # 被测变体

_ORIG_ED = W.LevelSetMulti.elastic_driving
SIGN = [+1.0]                                                   # 运行时开关


def _patched(self, *a, **kw):
    out = _ORIG_ED(self, *a, **kw)
    if np.any(self.sext_e0):
        raise RuntimeError('T1 判据要求 sext_e0 = 0（否则翻符号会连外载一起翻）')
    return SIGN[0] * out


W.LevelSetMulti.elastic_driving = _patched


# ---------------------------------------------------------------- 通用构建
def mk(N, L, eps0, gamma=0.0):
    return W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=gamma, Mob=1e-9,
                           df=[0.0] * (len(eps0) + 1), workers=4,
                           reinit_every=0, k0_mode='clamped')


def sync_pf(g, k=K):
    """把 level-set 的 region 同步成谱法弹性用的**尖锐指示场**。"""
    reg = g.region()
    g.pf.phi[:] = 0.0
    for v in range(g.nv):
        g.pf.phi[v] = (reg == v + 1)
    return reg


def ed_means(g, reg, k=K):
    ed = g.elastic_driving()[k]
    band = np.abs(g.phi[k]) <= 1.0 * g.dx
    return (float(ed[band].mean()) if band.any() else np.nan,
            float(ed[reg == k].mean()) if (reg == k).any() else np.nan)


def inclusion(N, L, e0, R, shape='sphere', nrm=None, t=None, k0='clamped'):
    """单变体内含物：返回 (E_el, V, ed_band, ed_interior, ncell)。"""
    g = mk(N, L, [e0])
    g.klass = k0
    c0 = np.array([L / 2] * 3)
    if shape == 'sphere':
        g.seed_sphere(1, c0, R)
    else:
        g.seed_plate(1, c0, np.asarray(nrm, float), R, t)
    g.init_parent()
    reg = sync_pf(g, 1)
    V = float((reg == 1).sum()) * g.dx ** 3
    E = float(g.pf.E_el())
    eb, ei = ed_means(g, reg, 1)
    return E, V, eb, ei, int((reg == 1).sum())


# ---------------------------------------------------------------- D1a / D1b
def run_D1a(dxs_nm, L, R, k0):
    print('=' * 100)
    print('D1a/D1b —— ed 与 D_corr = -dE_el/dV 的符号与比值')
    print('   D_corr 用**自相似恒等式** D_corr = -E_el/V（椭球内含物 σ 与尺寸无关）')
    print('   交叉验证列 FD：dE/dR（dR=dx，中心差分）对比自相似预测 3E/R')
    print('   L=%.0f nm, R=%.0f nm, k0=%s, 变体 k=%d' % (L * 1e9, R * 1e9, k0, K))
    print('=' * 100)
    print('%-6s %-7s %-8s %-13s %-13s %-12s %-9s %-9s %-8s' %
          ('dx(nm)', 'R/dx', 'cells', 'E_el (J)', 'V (m3)', 'D_corr', 'FD 3E/R',
           'FD dE/dR', 'FD偏差'))
    rows = []
    for dx_nm in dxs_nm:
        dx = dx_nm * 1e-9
        N = int(round(L / dx))
        E, V, eb, ei, nc = inclusion(N, L, EPS0[K], R, 'sphere', k0=k0)
        D = -E / V
        # 有限差分交叉验证（dR = dx，避免体素不变）
        Ep, _, _, _, ncp = inclusion(N, L, EPS0[K], R + dx, 'sphere', k0=k0)
        Em, _, _, _, ncm = inclusion(N, L, EPS0[K], R - dx, 'sphere', k0=k0)
        fd = (Ep - Em) / (2 * dx)
        pred = 3.0 * E / R
        rows.append(dict(dx=dx, N=N, E=E, V=V, D=D, eb=eb, ei=ei, nc=nc,
                         fd=fd, pred=pred, ok=ncp != ncm))
        print('%-6.1f %-7.1f %-8d %+.5e %-13.5e %+.4e %+.4e %+.4e %-8s' %
              (dx_nm, R / dx, nc, E, V, D, pred, fd,
               '%.1f%%' % (100 * abs(fd / pred - 1)) if pred else 'n/a'))
    print()
    print('%-6s | %-26s | %-26s' % ('dx(nm)', '修后 ed=+e0:sig', '修前 ed=-e0:sig'))
    print('%-6s | %-12s %-13s | %-12s %-13s' %
          ('', 'ed_band', 'ed/D_corr', 'ed_band', 'ed/D_corr'))
    ok_all, fail_all = True, True
    for r in rows:
        out = []
        for s in (+1.0, -1.0):
            SIGN[0] = s
            g = mk(r['N'], L, EPS0)
            g.seed_sphere(K, np.array([L / 2] * 3), R)
            g.init_parent()
            reg = sync_pf(g, K)
            eb, ei = ed_means(g, reg, K)
            out.append((eb, eb / r['D']))
        (eb_p, ra_p), (eb_m, ra_m) = out
        PASS = (eb_p * r['D'] > 0) and (0.5 <= abs(ra_p) <= 1.4)
        ok_all &= PASS
        fail_all &= not ((eb_m * r['D'] > 0) and (0.5 <= abs(ra_m) <= 1.4))
        r['ratio'] = ra_p
        print('%-6.1f | %+.4e %+.3f %-6s | %+.4e %+.3f' %
              (r['dx'] * 1e9, eb_p, ra_p, 'PASS' if PASS else 'FAIL', eb_m, ra_m))
    SIGN[0] = +1.0
    print()
    print('  ★ 记账：`ed_band/D_corr` 随 dx 减小是否**趋向 1**（这才是物理收敛）：')
    for r in rows:
        print('     dx=%-5.1f nm -> %.3f' % (r['dx'] * 1e9, abs(r['ratio'])))
    print('  D1a（同号 + 比值落在 [0.5,1.4]）: %s' % ('PASS' if ok_all else 'FAIL'))
    print('  D1b（修前必须 FAIL，即判据有分辨力）: %s' % ('PASS' if fail_all else 'FAIL'))
    return ok_all, fail_all, rows


# ---------------------------------------------------------------- D1c
def run_D1c(N=48, dx=2e-8):
    """相容 ⇒ ed 为机器零。**精确零应力的自协调层状构型**（合成 ε⁰）。

    ★ 为什么要改成层状（首版两稿都错，记账）：
      ① 首版用 Ti64 真实变体 + R=t=120 nm 的"板"，那其实是**等轴圆盘**，
         边缘区应力永远存在 ⇒ `|ed|/|Δf| < 1e-2` **物理上不可能达到**。
      ② 第二版用"单个无限平板 + ε⁰=sym(a⊗ẑ)"，仍不成立 —— **周期盒里单个有限厚
         平板永远有弹性能**：位移连续性要求 Δε⁰·v = 0 (∀v⊥n) ⇒ Δε⁰ = c·n⊗n（c∥n）；
         而"零平均应变"又要求 f ε⁰₁+(1−f)ε⁰₂ = 0。两者只能同时满足于**两层都 ∝ n⊗n**。
      ③ 正确构型（经典自协调层状 microstructure，Ball & James）：
           ε⁰₁ = e·ẑ⊗ẑ ,  ε⁰₂ = -(f/(1-f))·e·ẑ⊗ẑ ,  层厚比 f ，层法向 ẑ
         ⇒ 每层 σ = 0（ε = ε⁰）、平均应变为 0、位移在周期盒内**连续且周期**
           （实测：中心差分 u_z(0)=u_z(L) 恒等）。
      ⇒ 这是**有精确答案**的算例，且单变量对照干净：A/B 只差"ε⁰₂ 是不是 ∝ ẑ⊗ẑ"。
    """
    print()
    print('=' * 100)
    print('D1c —— 相容自协调层状构型的 ed 必须为机器零（合成精确算例，单变量对照）')
    print('=' * 100)
    L = N * dx
    e = 0.10
    f = 0.5
    lam = f / (1.0 - f)
    nz = np.array([0.0, 0.0, 1.0])
    e1 = e * np.outer(nz, nz)                     # ∝ ẑ⊗ẑ
    e2_good = -lam * e1                           # ∝ ẑ⊗ẑ  ⇒ 相容（精确零应力）
    e2_bad = -lam * e * np.outer([1.0, 0, 0], [1.0, 0, 0])   # ∝ x̂⊗x̂ ⇒ 不相容
    scale = float(np.einsum('ij,ijkl,kl->', e1, C, e1))
    print('  参照能量尺度 ε⁰₁:C:ε⁰₁ = %.4e J/m3   e=%.2f  f=%.2f  λ=%.2f' % (scale, e, f, lam))
    print('  几何：层法向 ẑ，层 1 = [0, %.0f nm)，层 2 = [%.0f nm, %.0f nm)（周期）'
          % (f * L * 1e9, f * L * 1e9, L * 1e9))
    z = None
    res = {}
    for tag, e2 in (('A_compatible', e2_good), ('B_incompatible', e2_bad)):
        g = mk(N, L, [e1, e2])
        z = g.XYZ[..., 2]
        g.phi[1] = np.maximum(z - f * L, -z)                 # 层 1 的 SDF（近似）
        g.phi[2] = np.maximum(z - L, f * L - z)              # 层 2 的 SDF（近似）
        g.init_parent()
        reg = sync_pf(g, 1)
        reg = g.region()
        g.pf.phi[0] = (reg == 1)
        g.pf.phi[1] = (reg == 2)
        V = float((reg > 0).sum()) * dx ** 3
        E = float(g.pf.E_el())
        sig = g.pf.sigma_tensor()
        smax = float(np.abs(sig).max())
        ed1 = g.elastic_driving()[1]
        ed2 = g.elastic_driving()[2]
        m1 = float(np.abs(ed1[reg == 1]).mean()) if (reg == 1).any() else 0.0
        m2 = float(np.abs(ed2[reg == 2]).mean()) if (reg == 2).any() else 0.0
        res[tag] = dict(E=E, V=V, smax=smax, m1=m1, m2=m2)
        print('  [%-14s] ncell=%-6d  E_el=%+.4e J  E_el/vol=%+.4e J/m3  max|σ|=%+.3e Pa'
              % (tag, int((reg > 0).sum()), E, E / V, smax))
        print('  %-17s <|ed_1|>_1=%+.4e   <|ed_2|>_2=%+.4e   (尺度=%.3e)'
              % ('', m1, m2, scale))
    rA, rB = res['A_compatible'], res['B_incompatible']
    okA = (abs(rA['E'] / rA['V']) < 1e-4 * scale) and (max(rA['m1'], rA['m2']) < 1e-4 * scale)
    # B 的阈值：只需"明确非零"即可 —— A 档是**绝对零**（不是"很多个数量级小"），
    #   所以分辨力判据写成 B > 1e-3·尺度（实测 8.6e-2·尺度），而不是我之前拍的 10%。
    okB = (abs(rB['E'] / rB['V']) > 1e-3 * scale)
    print('  A 档（相容 ⇒ E_el/vol 与 ed 都应 < 1e-4 尺度 ≈ 机器零）: %s'
          % ('PASS' if okA else 'FAIL'))
    print('  B 档（不相容 ⇒ E_el/vol 必须 > 1e-3 尺度，证明算例有分辨力）: %s'
          % ('PASS' if okB else 'FAIL'))
    return bool(okA and okB)


# ---------------------------------------------------------------- D1d
def run_D1d(N, dx, steps=300, df=2.0e8, Rfrac=0.09):
    """弹性项必须**反对**转变：对号 ⇒ 转化体积受抑制；错号 ⇒ 爆发。"""
    print()
    print('=' * 100)
    print('D1d —— 弹性开关的生长对照（steps=%d, df=%.2e J/m3）' % (steps, df))
    print('=' * 100)
    out = {}
    for s, tag in ((+1.0, '修后(+)'), (-1.0, '修前(-)')):
        SIGN[0] = s
        rng = np.random.default_rng(4)
        L = N * dx
        g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                            df=[0.0] * (NV + 1), workers=6, reinit_every=25)
        g.df[1:] = df
        R = Rfrac * L
        ns = 0
        while ns < 8:
            c = rng.random(3) * (L - 2 * R) + R
            k = int(rng.integers(1, NV + 1))
            try:
                g.seed_plate(k, c, np.array([0.0, 0.0, 1.0]), R, 4 * dx)
                ns += 1
            except ValueError:
                pass
        g.init_parent()
        v0 = float((g.region() > 0).sum())
        dt = 0.15 * dx / (1e-9 * max(df, 1.0))
        for _ in range(steps):
            g.elastic_driving()
            g.advance(dt, band_cells=20)
        v1 = float((g.region() > 0).sum())
        out[tag] = v1 / max(v0, 1.0)
        print('  %s  V/V0 = %.4f   (V0=%d cells)' % (tag, out[tag], int(v0)))
        del g
    SIGN[0] = +1.0
    ok = out['修后(+)'] < out['修前(-)']
    print('  D1d: %s（判据：修后的转化体积必须**小于**修前）' % ('PASS' if ok else 'FAIL'))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--L-nm', type=float, default=720.0)
    ap.add_argument('--R-nm', type=float, default=120.0)
    ap.add_argument('--dxs', type=str, default='30,20,10')
    ap.add_argument('--k0', type=str, default='clamped')
    ap.add_argument('--growth', action='store_true')
    ap.add_argument('--N', type=int, default=48)
    a = ap.parse_args()
    L, R = a.L_nm * 1e-9, a.R_nm * 1e-9
    dxs = [float(x) for x in a.dxs.split(',') if x.strip()]
    r = []
    oka, okb, rows = run_D1a(dxs, L, R, a.k0)
    r += [('D1a', oka), ('D1b', okb)]
    r += [('D1c', run_D1c(a.N, 2e-8))]
    if a.growth:
        r += [('D1d', run_D1d(a.N, 2e-8))]
    print()
    print('=' * 100)
    for name, ok in r:
        print('  %-5s %s' % (name, 'PASS' if ok else 'FAIL'))
    allok = all(ok for _n, ok in r)
    print('  ⇒ T1 %s' % ('PASS' if allok else 'FAIL'))
    print('=' * 100)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
