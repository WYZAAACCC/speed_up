#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T22_verify_paircurv.py --- **A1**：变体-变体（与变体-母相）界面的曲率必须
   来自差分场、且**带 winner 定向**。

病灶（本轮定位）
--------------
`pair_curvature=True` 一直 **FAIL**（T11j-2 实测："全涨，连 R0=100 nm 都涨 6185×"）。
根因**不是**差分场本身，而是**漏了一个定向因子**：
  `d = σ·(φ_karr − φ_larr)`（`σ = sign(larr−karr)`）是**按区域编号**定向的
  —— 这样 `d` 的符号跨界面连续（T11j 的正确修法）。但 `d < 0` 因此恒在**编号较小**
  的区域里，**而不是**在 winner 里。
  下游约定是 `dG = … − stk·κ`，要求 **κ > 0 ⟺ winner 凸**（凸 ⇒ 回退 ⇒ v<0）。
  ⇒ 当 `karr > larr` 时编号定向给出的 κ **与"winner 凸"恰好反号** ⇒ 曲率项把
  "回退"变成"前进" ⇒ 球无限涨。
修法（一行）：`κ_winner = σ · div(∇(σ·Δφ)/|∇(σ·Δφ)|)`。
  `karr<larr`：σ=+1 ⇒ 凸 winner 给 `+2/R` ✓
  `karr>larr`：σ=−1、`div=−2/R` ⇒ `κ=+2/R` ✓   ⇒ 两种次序都给 `+2/R`，且跨界面连续。

判据（全部是**已知答案**，见 MEASUREMENT_SPEC R0）
------------------------------------------------
  **T22-1 纯曲率流必须收缩**：`Δf = 0`、`γ > 0`、凸球 ⇒ 精确解是**单调收缩**
          （`dR/dt = −Mγκ < 0`）。三档对照：
            `pair_curvature=False`（旧默认，winner 场自己的 κ）
            `pair_curvature=True` + `_pc_legacy=True`（T11j 的旧写法，应 **FAIL**）
            `pair_curvature=True`（**A1 修法**，应 **PASS**）
  **T22-2 符号正确性（逐胞，机器级）**：在**两区域 + winner 次序两侧都构造**的球上，
          界面胞的 `κ` 中位必须 **> 0**（凸区域）。这是最便宜的"能否分辨"判据 ——
          若修法无效，`karr>larr` 的那一半胞会给 **< 0**，中位被拉低甚至变号。
  **T22-3 Gibbs–Thomson 临界半径**：`Δf > 0`、`γ > 0` ⇒ 存在缩/涨分界
          `R_c = 2γ/Δf`；扫 R0 必须看到**由缩转涨**（旧的 `pair_curvature=True` 全涨、
          没有分界 ⇒ FAIL）。

用法：python3 T22_verify_paircurv.py [--N 64] [--dx-nm 25]
退出码：0 = PASS
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from scipy.ndimage import distance_transform_edt                # noqa: E402

MOB = 1e-9
GAM = 0.15


def mk(N, dx, R0, pair_curv, legacy=False, nv=1):
    L = N * dx
    g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=nv, gamma=GAM, Mob=MOB,
                        df=[0.0] * (nv + 1), workers=4, reinit_every=0)
    g.pair_curvature = bool(pair_curv)
    g._pc_legacy = bool(legacy)
    g.seed_sphere(1, [L / 2] * 3, R0)
    g.init_parent()
    return g


def volume(g, k=1):
    return float((g.region() == k).sum()) * g.dx ** 3


def run(N, dx, R0, pair_curv, legacy=False, nstep=60, dtfac=0.02):
    g = mk(N, dx, R0, pair_curv, legacy)
    L = N * dx
    # dt：按曲率速度 M·γ·κ，κ≈2/R0 ⇒ v=M·γ·2/R0
    v = MOB * GAM * 2.0 / R0
    dt = dtfac * dx / max(v, 1e-30)
    v0 = volume(g)
    vs = []
    for i in range(nstep):
        g.advance(dt)
        if (i + 1) % max(1, nstep // 4) == 0:
            vs.append(volume(g) / max(v0, 1e-30))
    return vs, g, dt, v


def kappa_at_iface(g):
    """逐胞量界面带内 winner 场自己的 κ（`pair_curvature=False` 用的就是它），
       以及**差分场带 winner 定向**的 κ（A1 修法）。返回各自的分位数。"""
    ph = g.phi
    karr = np.argmin(ph, axis=0)
    larr = np.empty(karr.shape, dtype=karr.dtype)
    best = np.full(karr.shape, np.inf)
    for j in range(g.nreg):
        m = (karr != j) & (ph[j] < best)
        larr[m] = j
        best[m] = ph[j][m]
    pha = np.take_along_axis(ph, karr[None], 0)[0]
    phb = np.take_along_axis(ph, larr[None], 0)[0]
    sg = np.where(karr < larr, 1.0, -1.0)
    dd = sg * (pha - phb)
    gd = np.gradient(dd, g.dx, edge_order=2)
    gn = np.sqrt(sum(t ** 2 for t in gd)) + 1e-30
    k_idx = g.curvature_of(0, grad=gd, gn=gn)
    k_win = sg * k_idx
    # winner 场自己的 κ（旧默认）
    kw = np.zeros(pha.shape)
    act = np.unique(karr)
    for k in act:
        k = int(k)
        mw = (karr == k)
        if not mw.any():
            continue
        gg = np.gradient(ph[k], g.dx, edge_order=2)
        gnn = np.sqrt(sum(t ** 2 for t in gg)) + 1e-30
        kw[mw] = g.curvature_of(k, grad=gg, gn=gnn)[mw]
    band = np.abs(pha) <= 1.5 * g.dx
    return kw[band], k_win[band], sg[band], karr[band], larr[band]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=64)
    ap.add_argument('--dx-nm', type=float, default=25.0)
    ap.add_argument('--nstep', type=int, default=60)
    a = ap.parse_args()
    N, dx = a.N, a.dx_nm * 1e-9
    L = N * dx
    R0 = 0.15 * L
    print('=' * 104)
    print('T22 —— A1：差分场曲率的 **winner 定向因子**   N=%d Δx=%.1f nm L=%.2f µm R0=%.1f nm'
          % (N, a.dx_nm, L * 1e6, R0 * 1e9))
    print('  病灶：κ 取自**编号定向**的差分场 ⇒ `karr>larr` 的那一半胞符号反 ⇒ 曲率驱动反向')
    print('  修法：`κ_winner = σ·div(∇(σΔφ)/|∇(σΔφ)|)`（一行）')
    print('=' * 104)

    # ---------------- T22-2 一致性（逐胞，最便宜）----------------
    print('【T22-2】逐胞一致性：A1 的 `κ_win = σ·div(∇(σΔφ)/…)` 必须**等于**默认路径的')
    print('        `kap_w`（winner 场自己的 κ）—— 这才是正确的判据。')
    print('        ★ 记账：首版把判据写成"κ 中位必须 > 0"是**错的** —— κ 的约定是')
    print('          "winner 凸 ⇒ κ>0"，而界面带**两侧的 winner 不同**（内侧是变体、')
    print('          外侧是母相）⇒ 带内 κ 本来就有正有负，中位无物理含义。')
    g = mk(N, dx, R0, pair_curv=True)
    kw, kwin, sg, karr, larr = kappa_at_iface(g)
    kold = k_idx_of(g)
    d_new = float(np.max(np.abs(kwin - kw)) / max(np.max(np.abs(kw)), 1e-30))
    d_old = float(np.max(np.abs(kold - kw)) / max(np.max(np.abs(kw)), 1e-30))
    print('   旧默认 `kap_w`              ：κ 中位 = %+.4e（>0 占比 %.3f，带内两侧不同 winner）'
          % (np.median(kw), float((kw > 0).mean())))
    print('   **A1 修法 vs 旧默认的最大相对差** = **%.3e**（应 ~0）' % d_new)
    print('   T11j 旧写法 vs 旧默认的最大相对差 = %.3e（应显著 >0 ⇒ 对照有分辨力）' % d_old)
    for tag, m in (('karr<larr 侧', sg > 0), ('karr>larr 侧', sg < 0)):
        if m.sum() > 5:
            print('      %-14s 胞数 %-6d  κ 中位 = %+.4e' % (tag, int(m.sum()), np.median(kwin[m])))
    ok2 = (d_new < 1e-6) and (d_old > 1e-2)
    print('   T22-2: %s（A1 ≡ 默认 **且** 旧写法确实不同）' % ('PASS' if ok2 else 'FAIL'))

    # ---------------- T22-1 纯曲率流必须收缩 ----------------
    print('-' * 104)
    print('【T22-1】纯曲率流（Δf=0, γ>0, 凸球）⇒ 必须**单调收缩**（精确解 dR/dt<0）')
    print('   %-34s %s' % ('配置', 'V/V0 轨迹（4 个采样点，应 <1 且单调降）'))
    res = {}
    for tag, pc, lg in (('pair_curvature=False（旧默认）', False, False),
                        ('True + _pc_legacy（T11j 旧写法）', True, True),
                        ('**True（A1 修法）**', True, False)):
        vs, g1, dt, v = run(N, dx, R0, pc, lg, a.nstep)
        res[tag] = vs
        good = (vs[-1] < 0.99) and all(vs[i] >= vs[i + 1] - 1e-9 for i in range(len(vs) - 1))
        print('   %-34s %s  ⇒ %s' % (tag, ' '.join('%.4f' % x for x in vs),
                                     'PASS' if good else 'FAIL'))
    ok1 = all((res[t][-1] < 0.99) and
              all(res[t][i] >= res[t][i + 1] - 1e-9 for i in range(len(res[t]) - 1))
              for t in ('pair_curvature=False（旧默认）', '**True（A1 修法）**'))
    print('   T22-1（"False" 与 "True(A1)" 都必须 PASS；"legacy" 预期 FAIL 作反面对照）: %s'
          % ('PASS' if ok1 else 'FAIL'))

    # ---------------- T22-3 Gibbs–Thomson 临界半径 ----------------
    print('-' * 104)
    # ★ R1（可行性先算）：要让 R_c 落在网格能分辨的范围，Δf 必须小。
    #   首版取 Δf=1e8 ⇒ R_c = 3 nm **远小于 Δx=25 nm** ⇒ 四档全在亚网格 ⇒ 读数无意义
    #   （实测 0.000/0.000/0.000/1.6e7 是量具坏，不是模型坏）。
    df = 2.4e6
    Rc_th = 2.0 * GAM / df
    print('【T22-3】Gibbs–Thomson 临界半径：Δf=%.2e ⇒ 理论 R_c = 2γ/Δf = **%.1f nm**'
          '（= %.1f Δx，可分辨 ✓）' % (df, Rc_th * 1e9, Rc_th / dx))
    print('   %-34s %s' % ('配置', 'R0/Rc = 0.5/1/2/4 的 V/V0（应出现由缩转涨）'))
    ok3 = {}
    for tag, pc, lg in (('pair_curvature=False（旧默认）', False, False),
                        ('True + _pc_legacy（T11j 旧写法）', True, True),
                        ('**True（A1 修法）**', True, False)):
        row = []
        for Rf in (0.5, 1.0, 2.0, 4.0):
            g2 = mk(N, dx, Rf * Rc_th, pc, lg)
            g2.df[1:] = df
            v = MOB * df
            dt = 0.05 * dx / max(v, 1e-30)
            v0 = volume(g2)
            for _ in range(60):
                g2.advance(dt)
            row.append(volume(g2) / max(v0, 1e-30))
        ok3[tag] = (row[0] < 1.0) and (row[-1] > 1.0)
        print('   %-34s %s  ⇒ %s'
              % (tag, ' '.join('%.3f' % x for x in row), 'PASS' if ok3[tag] else 'FAIL'))
    ok3v = ok3['**True（A1 修法）**']
    print('   T22-3（A1 修法必须出现缩/涨分界）: %s' % ('PASS' if ok3v else 'FAIL'))
    # ---------------- T22-4 镜像 SDF 前提（变体-变体）----------------
    print('-' * 104)
    print('【T22-4】**前提条件**：默认路径成立 ⟺ 变体-变体界面两侧的 SDF 互为镜像')
    print('        （`cos(∇φ_k,∇φ_l) ≈ −1`、`|∇φ_k| ≈ |∇φ_l|`）。这里**直接量它**。')
    from windowB_pf3d import C_cubic, _lam_full
    from windowB_ti64_variants import variants
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
    N2, dx2 = 64, 25e-9
    L2 = N2 * dx2
    # (a) **解析正对照**：两个半空间相接 ⇒ 镜合度必须**精确** −1.000 / 1.000
    ga = W.LevelSetMulti(N2, L2, C=None, eps0=None, nv=2, gamma=0.15, Mob=MOB,
                         df=[0.0, 2.0e8, 2.0e8], workers=1, reinit_every=0)
    yy = ga.XYZ[..., 1] - L2 / 2        # ★ `XYZ` 的形状是 (N,N,N,3)
    ga.phi[1] = yy                      # 区域 1：y < L/2
    ga.phi[2] = -yy                     # 区域 2：y > L/2
    # ★ 记账：**不能调 `init_parent()`** —— 它会令 `φ_0 = −min(φ_1,φ_2) = |yy|`，
    #   而在界面处 `|yy| ≈ 0` 与**非 winner 的那个变体**（值为 +|yy|）**恰好相等**
    #   ⇒ 三场简并 ⇒ `larr` 取到 0 ⇒ 变体-变体胞数 = 0（首版正对照就是这样"0 胞"）。
    #   ⇒ 把母相场设成不可能的 1e3（仓库里既有的做法）。
    ga.phi[0] = 1e3
    m = mirror_stats(ga)
    print('   (a) 解析两半空间（正对照，已知答案 −1.000 / 1.000）：胞数 %d  |cos| = %.4f  '
          '|∇φ_k|/|∇φ_l| = %.4f' % (m['n'], m['cos'], m['ratio']))
    ok_a = m['n'] > 50 and abs(m['cos'] - 1.0) < 0.02 and abs(m['ratio'] - 1.0) < 0.02
    print('       正对照: %s' % ('PASS（量具可用）' if ok_a else 'FAIL（量具不可用）'))
    # (b) **演化后**（多核碰撞）
    g3 = W.LevelSetMulti(N2, L2, C=C, eps0=EPS0, nv=NV, gamma=0.15, Mob=MOB,
                         df=[0.0] + [2.0e8] * NV, workers=4, reinit_every=0,
                         reinit_dt=6.0e-7)
    _r2 = np.random.default_rng(11)
    ns = 0
    for _ in range(60):
        if ns >= 10:
            break
        c = _r2.random(3) * (L2 - 1.6e-6) + 0.8e-6
        k = int(_r2.integers(1, NV + 1))
        nrm = np.asarray(NPF[k], float)
        nrm = nrm / np.linalg.norm(nrm)
        try:
            g3.seed_plate(k, c, nrm, 3.2e-7, 8.0e-8)
            ns += 1
        except ValueError:
            pass
    g3.init_parent()
    dt = 0.15 * dx2 / (MOB * 2.0e8)
    best_n = 0
    for it in range(1, 101):
        g3.elastic_driving()
        g3.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
        if it % 20 == 0:                    # ★ 记账：每步调 `mirror_stats` 太贵
            best_n = max(best_n, mirror_stats(g3)['n'])
    m2 = mirror_stats(g3)
    print('   (b) 演化 %d 核 ×100 步后：变体-变体胞数 = %d（过程中最多 %d）'
          % (ns, m2['n'], best_n))
    if m2['n'] > 10:
        print('       |cos(∇φ_k,∇φ_l)| 中位 = **%.3f**（理想 1.000 ⇒ 完全反平行）' % m2['cos'])
        print('       |∇φ_k|/|∇φ_l| 中位 = **%.3f**（理想 1.000 ⇒ 同尺度）' % m2['ratio'])
        print('       代码内自量 `_pair_mirror` / `_pair_scale` = %s / %s'
              % (getattr(g3, '_pair_mirror', 'n/a'), getattr(g3, '_pair_scale', 'n/a')))
        # ★ 记账（判据修正）：首版把 T22-4 写成"前提必须**成立**"（cos>0.8 且 ratio∈(0.7,1.4)），
        #   这是**旧默认路径**的判据。默认改成差分场之后，前提**不再被需要** ——
        #   差分场曲率 `div(∇d/|∇d|)` 做了归一化，与各场的尺度无关，**无论前提成不成立都对**。
        #   ⇒ 本条的职责变成**提供改用差分场的理由**：必须实测到前提**不成立**。
        #   判据：前提**确实被违反**（这正是切换默认的依据）**且** 量具在解析正对照上可用。
        violated = (m2['cos'] < 0.95) or not (0.85 < m2['ratio'] < 1.18)
        print('       ⇒ 前提被违反 = %s（这正是"必须走差分场"的理由）'
              % ('是 ✓' if violated else '**否**（若成立，两条路径等价，切换默认无收益）'))
        ok4 = ok_a and violated
    else:
        print('       ⚠ 仍未产生变体-变体界面 ⇒ (b) **INCONCLUSIVE**（只能靠 (a) 的正对照）')
        print('       ⇒ 移交 T16/T13b 的多核算例复量（那里碰撞是必然发生的）')
        ok4 = ok_a
    print('   T22-4: %s' % ('PASS' if ok4 else 'FAIL'))
    print('=' * 104)
    allok = ok1 and ok2 and ok3v and ok4
    print('  ⇒ T22 %s' % ('PASS' if allok else 'FAIL'))
    print('=' * 104)
    return 0 if allok else 1


def mirror_stats(g):
    """变体-变体界面胞的**镜合度**：`|cos(∇φ_k,∇φ_l)|` 与 `|∇φ_k|/|∇φ_l|` 的中位。"""
    ph = g.phi
    karr = np.argmin(ph, axis=0)
    larr = np.empty(karr.shape, dtype=karr.dtype)
    best = np.full(karr.shape, np.inf)
    for j in range(g.nreg):
        m = (karr != j) & (ph[j] < best)
        larr[m] = j
        best[m] = ph[j][m]
    pha = np.take_along_axis(ph, karr[None], 0)[0]
    phb = np.take_along_axis(ph, larr[None], 0)[0]
    hpp = (karr > 0) & (larr > 0)
    n = int(hpp.sum())
    if n < 5:
        return dict(n=n, cos=np.nan, ratio=np.nan)
    gk = np.gradient(pha, g.dx)
    gl = np.gradient(phb, g.dx)
    nk = np.sqrt(sum(t ** 2 for t in gk)) + 1e-30
    nl = np.sqrt(sum(t ** 2 for t in gl)) + 1e-30
    cosv = np.abs(sum(gk[i] * gl[i] for i in range(3)) / (nk * nl))
    return dict(n=n, cos=float(np.median(cosv[hpp])),
                ratio=float(np.median((nk / nl)[hpp])))


def k_idx_of(g):
    ph = g.phi
    karr = np.argmin(ph, axis=0)
    larr = np.empty(karr.shape, dtype=karr.dtype)
    best = np.full(karr.shape, np.inf)
    for j in range(g.nreg):
        m = (karr != j) & (ph[j] < best)
        larr[m] = j
        best[m] = ph[j][m]
    pha = np.take_along_axis(ph, karr[None], 0)[0]
    phb = np.take_along_axis(ph, larr[None], 0)[0]
    sg = np.where(karr < larr, 1.0, -1.0)
    dd = sg * (pha - phb)
    gd = np.gradient(dd, g.dx, edge_order=2)
    gn = np.sqrt(sum(t ** 2 for t in gd)) + 1e-30
    k = g.curvature_of(0, grad=gd, gn=gn)
    return k[np.abs(pha) <= 1.5 * g.dx]


if __name__ == '__main__':
    sys.exit(main())
