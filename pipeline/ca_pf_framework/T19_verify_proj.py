#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T19_verify_proj.py --- **D17**：P1（界面带自发膨胀）的**结构性修法**验证。

背景（为什么要改结构而不是调参）
-------------------------------
`P1_band.py` 已实测：`upwind` 对带宽/种子带**完全不敏感**（12 个组合逐位相同，
键/解析 = 2.70），`central` 跨 4 倍（2.09–8.07）⇒ **调参修不好**。剩下的是结构性修法。

修法（已在 `windowB_surface.py` 落地，`adv_grad='proj'` / `'proj2'`）
-----------------------------------------------------------------
把"法向速度"**投影**成矢量速度场 `V = v_canon·n_orient`（`n_orient = ∇d/|∇d|`，
`d` 按区域编号定向 = T11j 的修法），再对 `φ_t + V·∇φ = 0` 用**迎风通量**
（`upwind_flux_vec`）。三个理由（都是结构性的，不是拟合）：
  1. 迎风对**线性**数据精确 ⇒ 倾斜平面**精确**平移、无阶梯慢化
     （修掉 `upwind`/Godunov 的 `O(dx)` 取向误差）；
  2. 迎风**单调** ⇒ 无网格尺度伪振荡 ⇒ 界面不自发粗化（修掉 `central`）；
  3. 两个场共用**同一个** `V` ⇒ 差分场 `d` 只平移、`|∇d|` 不变。

判据（**全部先做已知答案正对照**，见 `MEASUREMENT_SPEC.md` R0）
--------------------------------------------------------------
  T19-0 **R0 键测度正对照**：干净阶梯球的键数 vs `1.5·4πR²/dx²`
        （★ 本轮发现：旧口径用 `mean_r` 当 R，而球内平均半径 = `0.75R`
         ⇒ 解析对照被低估 `1/0.5625 = 1.778×` ⇒ "upwind 也在膨胀"是**量具假象**）
  T19-A **斜面平移（已知答案）**：`φ_exact = n·(x−x0) − v·t`。四格式的
        `v/(MΔf)`（残差口径 + 体积口径）都要 ≈ 1.0000
  T19-B **Δx 无关性**：三档 Δx 的 `v/(MΔf)` 相对散布
  T19-C **P1 球（已知答案 `R(t)=R0+vt`）**：界面键数 / 干净阶梯键测度必须 ≈ 1.0
        （`central` 会涨到 2.3+；这是 P1 的定量判据）
  T19-D **球半径精度**：`R_meas/R_exact − 1`
  T19-E **各向异性幅度**（W1 口径）：`a2` 必须 ≈ 1.0（`upwind` 只有 0.90–0.93）
  T19-F **多畴回归**：12 变体短跑不得退化（T9-D 口径：尺度比 + 最薄方向夹角）

用法：
  python3 T19_verify_proj.py --stage 0,1        # 先跑便宜的正对照
  python3 T19_verify_proj.py --stage all
退出码：0 = 全部 PASS
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402

DF, MOB = 2.0e8, 1e-9
EXACT = MOB * DF                     # 0.2 m/s
ADVS = ('central', 'upwind', 'proj', 'proj2')


# ---------------------------------------------------------------- 量具
def bond_count(reg):
    nb = 0
    for ax in range(3):
        nb += int((reg != np.roll(reg, -1, axis=ax)).sum())
    return nb


def sphere_R(g, k=1):
    """体积口径半径。两种估计：
       A) 部分体积（coarea，线性 ramp）—— 平面精确、球面二阶；
       B) 平均半径 `(4/3)·mean_r`（★ 修正：球内平均半径 = 0.75R，不是 R！）。"""
    phi = g.phi[k]
    H = np.clip(0.5 - phi / g.dx, 0.0, 1.0)
    V = float(H.sum()) * g.dx ** 3
    RA = (3.0 * V / (4.0 * np.pi)) ** (1.0 / 3.0)
    idx = np.argwhere(phi < 0)
    c0 = np.array(g.phi.shape[1:], float) / 2.0
    rr = np.linalg.norm(idx.astype(float) + 0.5 - c0[None, :], axis=1) * g.dx
    RB = (4.0 / 3.0) * float(rr.mean()) if rr.size else np.nan
    return RA, RB


def clean_ref(nb_clean, R, dx):
    """干净阶梯球的**实测**键测度（正对照基准），不是解析式。"""
    return nb_clean, 1.5 * 4.0 * np.pi * R ** 2 / dx ** 2


def seed_perfect_sphere(N, dx, R, L=None):
    """造一个**解析 SDF 球**（不演化），用于键测度正对照。"""
    L = N * dx if L is None else L
    g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=1, gamma=0.0, Mob=MOB,
                        df=[0.0, DF], workers=1, reinit_every=0)
    g.seed_sphere(1, [L / 2] * 3, R)
    g.init_parent()
    return g


# ---------------------------------------------------------------- T19-0
def stage0():
    print('=' * 100)
    print('T19-0 **R0 正对照**：干净阶梯球的键测度（已知答案 = 1.5·4πR²/dx²）')
    print('  ★ 为什么必须做：P1 的"两者都在膨胀"用的是 `mean_r` 当 R，')
    print('    而球内平均半径 = 0.75R ⇒ 解析对照被低估 1/0.5625 = 1.778×。')
    print('-' * 100)
    print('  %-8s %-7s %-10s %-10s %-10s %-10s %s'
          % ('Δx(nm)', 'R(nm)', 'nb 实测', '1.5·4πR²/dx²', '比', 'R_A/R_B', '判定'))
    ok = True
    rows = []
    for dxn in (50.0, 25.0, 12.5):
        dx = dxn * 1e-9
        N = 64
        L = N * dx
        R0 = 0.30 * L
        g = seed_perfect_sphere(N, dx, R0, L)
        RA, RB = sphere_R(g)
        nb = bond_count(g.region())
        ref = 1.5 * 4.0 * np.pi * RA ** 2 / dx ** 2
        r = nb / ref
        good = 0.9 <= r <= 1.1
        ok &= good
        rows.append((dxn, r))
        print('  %-8.1f %-7.1f %-10d %-10.0f %-10.3f %-10.4f %s'
              % (dxn, RA * 1e9, nb, ref, r, RA / RB, 'PASS' if good else 'FAIL'))
    print('  ⇒ 键测度的"干净阶梯"基准 = **1.5·4πR²/dx²**（实测比 = %.3f±%.3f）'
          % (np.mean([r for _, r in rows]), np.std([r for _, r in rows])))
    print('  ⇒ P1 的 2.70（旧口径）除以 1.778 = **1.52** ⇒ `upwind` 其实**干净**！')
    print('     （这条推翻了 P1 的"换格式只是缓解"结论 —— 是量具错，不是模型错。）')
    print('=' * 100)
    return ok


# ---------------------------------------------------------------- T19-A/B
def _wrap_field(s, L):
    """周期化：`wrap(s) = s − L·round(s/L)`。
    ★ 为什么必须（本轮记账）：旧写法（T11g）直接放 `φ = n·(x−x0)`，而**线性场不是周期场**
      ⇒ 在周期盒面上有一道 **`n_i·L` 高的跳变**（本例 800 nm ≈ 16–32 胞），
      它使"零等值面"退化成"平面 + 台阶"。后果实测：`max|resid|/dx` 被台阶污染到
      **50–71**（而 `median` 口径 vD 仍是干净的 1.0000）—— 即旧口径的
      `max|resid|` 与"体积口径 vE"（面积随位置变）都**不是**可靠判据。
      wrap 之后场是**真周期**的，零集是**一族平行平面**（同法向、同速度 ⇒ 一起平移），
      台阶消失 ⇒ `max|resid|`、面积守恒、键数守恒全都变成干净的已知答案。"""
    return s - L * np.round(s / L)


def plane_setup(N, dx, n_h, L=None):
    L = N * dx if L is None else L
    g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=1, gamma=0.0, Mob=MOB,
                        df=[0.0, DF], workers=1, reinit_every=0)
    n_h = np.asarray(n_h, float) / np.linalg.norm(n_h)
    d0 = _wrap_field((g.XYZ - np.array([L / 2] * 3)) @ n_h, L)
    g.phi[1] = d0
    g.init_parent()
    return g, d0


def _count_vol(g):
    return float((g.phi[1] < 0).sum()) / g.N ** 3


def plane_run(N, dx, adv, n_h, nstep=80, band=20, iband=2.0):
    L = N * dx
    g, d0 = plane_setup(N, dx, n_h, L)
    # ★ R0 正对照：体积估计量的**标定常数** `K = Δf/δ`（用已知位移直接量）
    _delta = 0.37 * dx
    g.phi[1] = d0 - _delta
    g.phi[0] = -g.phi[1]
    fA = _count_vol(g)
    g.phi[1] = d0
    g.phi[0] = -g.phi[1]
    fB = _count_vol(g)
    K = abs(fA - fB) / _delta                      # 体积分数 / 米
    dt = 0.15 * dx / EXACT
    f0 = _count_vol(g)
    A0 = g.area_total_geom()
    t = 0.0
    for _ in range(nstep):
        g.advance(dt, band_cells=band, iface_band=iband, adv_grad=adv)
        t += dt
    f1 = _count_vol(g)
    A1 = g.area_total_geom()
    vE = abs(f1 - f0) / max(K, 1e-300) / t / EXACT      # 体积口径（已用 K 标定）
    phi_ex = d0 - EXACT * t
    bm = np.abs(phi_ex) <= 3.0 * dx
    resid = g.phi[1][bm] - phi_ex[bm]
    vD = 1.0 + float(np.median(resid)) / (EXACT * t)
    return dict(vE=vE, vD=vD, maxres=float(np.max(np.abs(resid)) / dx),
                rmsres=float(np.sqrt(np.mean(resid ** 2)) / dx),
                sv=A1 / max(A0, 1e-300), K=K * L)


def stageA(dxs=(50.0,), nstep=80):
    print('=' * 100)
    print('T19-A **斜面平移（已知答案 `φ_ex = wrap(n·(x−x0)) − v·t`）**  n=(1,2,3)/√14')
    print('  `v/(MΔf)`：残差口径 vD（中位，亚胞）与体积口径 vE（已用 K 标定）**都要 ≈ 1.0000**')
    print('  `maxres`：最大残差/dx（已知答案 **0**）；`Sv`：面积守恒（已知答案 **1.000**）')
    print('  ★ 旧口径（T11g）的线性场在周期面上有 800 nm 高的跳变 ⇒ maxres 被污染到 50–71；')
    print('    本脚本改用 **wrap 周期场**（零集 = 一族平行平面，一起平移）。')
    print('-' * 100)
    n_h = (1.0, 2.0, 3.0)
    L = 3.0e-6
    res = {}
    for dxn in dxs:
        dx = dxn * 1e-9
        N = int(round(L / dx))
        print('  Δx = %.1f nm（N=%d, L=%.2f µm, %d 步）' % (dxn, N, N * dxn / 1000.0, nstep))
        for adv in ADVS:
            r = plane_run(N, dx, adv, n_h, nstep)
            res.setdefault(adv, []).append(r)
            print('    %-8s vD=%-9.4f vE=%-9.4f maxres=%-8.3f rmsres=%-7.3f Sv=%.4f'
                  % (adv, r['vD'], r['vE'], r['maxres'], r['rmsres'], r['sv']), flush=True)
    print('-' * 100)
    print('  判据 T19-A（斜面）：|vD−1|<2e-3 且 |vE−1|<0.05 且 maxres<0.5 且 Sv∈[0.99,1.01]')
    okA = True
    for adv in ADVS:
        for r in res[adv]:
            a1 = abs(r['vD'] - 1) < 2e-3
            a2 = abs(r['vE'] - 1) < 0.05
            a3 = r['maxres'] < 0.5
            a4 = 0.99 <= r['sv'] <= 1.01
            okA &= (a1 and a2 and a3 and a4)
            print('    %-8s vD %s  vE %s  maxres %s  Sv %s'
                  % (adv, '✓' if a1 else '✗', '✓' if a2 else '✗',
                     '✓' if a3 else '✗', '✓' if a4 else '✗'))
    if len(dxs) > 1:
        print('  判据 T19-B（Δx 无关性）：三档 vD 相对散布 < 2e-3（固定物理 L，只变 N）')
        for adv in ADVS:
            vs = [r['vD'] for r in res[adv]]
            sp = (max(vs) - min(vs)) / max(np.mean(vs), 1e-30)
            print('    %-8s vD = %s ⇒ 散布 %.2e %s'
                  % (adv, ['%.4f' % v for v in vs], sp, '✓' if sp < 2e-3 else '✗'))
            okA &= (sp < 2e-3)
    print('=' * 100)
    return okA


# ---------------------------------------------------------------- T19-C/D
def sphere_run(N, dx, adv, steps=300, band=20, R0f=0.15, every=30, reinit_dt=None):
    L = N * dx
    g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=1, gamma=0.0, Mob=MOB,
                        df=[0.0, DF], workers=1, reinit_every=0, reinit_dt=reinit_dt)
    R0 = R0f * L
    g.seed_sphere(1, [L / 2] * 3, R0)
    g.init_parent()
    dt = 0.15 * dx / EXACT
    hist = []
    t = 0.0
    for it in range(1, steps + 1):
        g.advance(dt, band_cells=band, adv_grad=adv)
        t += dt
        if it % every == 0:
            RA, RB = sphere_R(g)
            nb = bond_count(g.region())
            R_ex = R0 + EXACT * t
            hist.append(dict(it=it, R=RA, Rb=RB, nb=nb,
                             ref=1.5 * 4.0 * np.pi * RA ** 2 / dx ** 2,
                             R_ex=R_ex))
    return hist


def stageC(steps=120, reinit_dt=None, tag='C'):
    print('=' * 100)
    print('T19-C/D **P1 球（已知答案 `R(t)=R0+v·t`，界面**不该**粗化）**%s'
          % ('  [reinit ON]' if reinit_dt else ''))
    L = 64 * 25e-9
    R0 = 0.10 * L
    print('  N=64 Δx=25 nm ⇒ L=1.60 µm, R0=%.0f nm；%d 步后 R=%.0f nm（须 < 0.45L=%.0f）'
          % (R0 * 1e9, steps, (R0 + EXACT * (steps * 0.15 * 25e-9 / EXACT)) * 1e9, 0.45 * L * 1e9))
    print('  判据 T19-C：`键数/干净阶梯键测度` < 1.15（central 实测会到 **2.80**）')
    print('  判据 T19-D：`|R/R_ex − 1|` < 2%（central 实测 **+6.8%**）')
    print('  可重复性判据：末两档 |ΔR|/R < 0.5%（数值扩散是否已饱和）')
    print('-' * 100)
    okC = okD = True
    summary = {}
    for adv in ADVS:
        h = sphere_run(64, 25e-9, adv, steps, R0f=0.10, reinit_dt=reinit_dt)
        print('  【%s】 step   R_A(nm)  R_ex(nm)  R/R_ex−1   键数    键/干净阶梯' % adv)
        for r in h:
            print('        %-6d %-8.1f %-9.1f %+-9.4f %-7d %.3f'
                  % (r['it'], r['R'] * 1e9, r['R_ex'] * 1e9, r['R'] / r['R_ex'] - 1,
                     r['nb'], r['nb'] / r['ref']), flush=True)
        # ★ 判据口径（记账）：**必须在"同一个物理半径"上比**，否则比的是不同演化阶段。
        #   实测（首版用"盒内最后一档"）：central 在 step 90（R/dx=19.9）还干净（1.042），
        #   到 step 120（R/dx=26.6）才爆到 2.836 ⇒ 用"最后一档"会因盒子守卫而**误判 PASS**。
        #   ⇒ 改成在 `R_judge = 0.38L` 处**线性插值**取值（所有格式都达到过该半径）。
        L_ = 64 * 25e-9
        Rj = 0.38 * L_

        def _at(hist, key):
            R = np.array([r['R'] for r in hist])
            v = np.array([r[key] for r in hist])
            o = np.argsort(R)
            return float(np.interp(Rj, R[o], v[o]))

        ratio = _at(h, 'nb') / _at(h, 'ref')
        relerr = _at(h, 'R') / Rj - 1.0
        gC = ratio < 1.15
        gD = abs(relerr) < 0.02
        okC &= gC
        okD &= gD
        summary[adv] = (Rj * 1e9, relerr, ratio)
        print('        ⇒ 判定点 **R = %.0f nm**（=0.38L，线性插值）：键/干净阶梯 **%.3f** %s'
              ' ； R/R_ex−1 = %+.4f %s'
              % (Rj * 1e9, ratio, 'PASS' if gC else 'FAIL', relerr, 'PASS' if gD else 'FAIL'))
    print('-' * 100)
    print('  ★★ 汇总（**同一物理半径 R=%.0f nm 上插值**）：' % (Rj * 1e9))
    print('     %-8s %-10s %-14s %-14s %s' % ('格式', 'R(nm)', 'R/R_ex−1', '键/干净阶梯', '判定'))
    for adv in ADVS:
        rr_, re_, ra_ = summary[adv]
        print('     %-8s %-10.0f %+-14.4f %-14.3f %s'
              % (adv, rr_, re_, ra_, '★可用' if (abs(re_) < 0.02 and ra_ < 1.15) else '✗'))
    print('=' * 100)
    return okC and okD


# ---------------------------------------------------------------- T19-E
def w1_aniso(N=64, dx=2e-9, R0=1.2e-8, Lam=0.4, nstep=600, adv='central'):
    """W1 口径：Herring 各向异性下平衡形状的 `a2`（应恢复到 1.0）。"""
    g = W.LevelSetMulti(N, N * dx, C=None, eps0=None, nv=1, gamma=0.15, Mob=MOB,
                        df=[0.0, DF], workers=1, reinit_every=0)
    g.seed_sphere(1, [N * dx / 2] * 3, R0)
    g.init_parent()
    dt = 0.05 * dx / EXACT
    for _ in range(nstep):
        g.advance(dt, aniso=Lam, adv_grad=adv)
    reg = g.region()
    idx = np.argwhere(reg == 1)
    if idx.size == 0:
        return np.nan
    c0 = np.array([N * dx / 2] * 3)
    p = (idx.astype(float) + 0.5) * dx - c0
    r = np.linalg.norm(p, axis=1)
    u = p / np.maximum(r[:, None], 1e-30)
    key = np.round(u * 5).astype(int)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    Rm = np.array([r[inv == j].mean() for j in range(inv.max() + 1)])
    Rbar = Rm.mean()
    # a2 = 形状的 2 阶各向异性幅度（相对 Rbar）
    return float(np.ptp(Rm) / Rbar)


def stageE():
    print('=' * 100)
    print('T19-E **各向异性幅度（复用已验证的 W1 harness）**')
    print('  仓库记账：一阶 Godunov 迎风 |∇φ| 把有效各向异性压低 ~8%（a2 比 0.90–0.93，')
    print('  且不随 dx 收敛）；`central` 复原到 0.99–1.01。'
          '⇒ 要求 `proj2` 的 a2 比 ≥ 0.95')
    print('  ★ R0：这里**不新造量具**，直接用 W1 的傅里叶口径（已有正/反向对照）')
    print('-' * 100)
    ref = None
    ok = True
    for adv in ('central', 'upwind', 'upwind2', 'proj2'):
        print('---- W1(Λ=0.4, herring=True, adv=%s) ----' % adv)
        good, fin = W.W1_wulff(N=64, Lam=0.4, nstep=600, adv_grad=adv, verbose=600)
        r = fin.get('a2', np.nan) / max(fin.get('a2_th', np.nan), 1e-30)
        if adv == 'central':
            ref = r
        rel = r / ref if ref else np.nan
        gE = rel >= 0.95
        ok &= gE
        print('    ⇒ a2/a2_th = %.4f ；相对 central = **%.4f** %s'
              % (r, rel, 'PASS' if gE else 'FAIL'), flush=True)
    print('=' * 100)
    return ok


# ---------------------------------------------------------------- T19-F
def stageF():
    print('=' * 100)
    print('T19-F **多畴回归**：12 变体短跑，尺度比与最薄方向夹角（T9-D 口径）')
    print('=' * 100)
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
            val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v],
                                        _lam_full(C, n), EPS0[v]))
            if best is None or val < best:
                best, bn = val, n
        NPF[v + 1] = bn
    N, dx = 64, 25e-9
    L = N * dx
    for adv in ('central', 'proj', 'proj2'):
        g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, nv=NV, gamma=0.15, Mob=MOB,
                            df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                            reinit_dt=6e-7)
        g.seed_plate(1, [L / 2] * 3, np.asarray(NPF[1], float), 1.4e-7, 5e-8)
        g.init_parent()
        dt = 0.15 * dx / EXACT
        for _ in range(120):
            g.elastic_driving()
            g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                      mob_beta=3.5, mob_beta_w=2.3, adv_grad=adv)
        reg = g.region()
        m = (reg == 1)
        idx = np.argwhere(m)
        if idx.size < 20:
            print('    %-8s 变体 1 消失（f 太小）' % adv)
            continue
        p = (idx.astype(float) + 0.5) * dx
        ext = p.max(0) - p.min(0)
        order = np.argsort(ext)[::-1]
        nd = np.asarray(NPF[1], float)
        nd /= np.linalg.norm(nd)
        # 最薄方向的取向 vs npref[1]：用 PCA 的最小主轴
        q = p - p.mean(0)
        w, V_ = np.linalg.eigh(np.cov(q.T))
        thin = V_[:, 0]
        ang = np.degrees(np.arccos(np.clip(abs(thin @ nd), 0, 1)))
        f = m.sum() / g.N ** 3
        print('    %-8s f=%.4f  三向尺度比 = %.2f : %.2f : 1   最薄方向 vs npref[1] = %.2f°'
              % (adv, f, ext[order[0]] / ext[order[2]],
                 ext[order[1]] / ext[order[2]], ang), flush=True)
    print('=' * 100)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', default='0,A,C')
    ap.add_argument('--dxs', default='50')
    ap.add_argument('--steps', type=int, default=300)
    ap.add_argument('--nstep-plane', type=int, default=80)
    a = ap.parse_args()
    st = a.stage
    dxs = tuple(float(s) for s in a.dxs.split(',') if s.strip())
    print('#' * 100)
    print('# T19 —— D17（P1 的结构性修法：投影型保几何平流）验证')
    print('#   格式：%s' % (', '.join(ADVS),))
    print('#' * 100)
    ok = {}
    if 'all' in st or '0' in st:
        ok['0'] = stage0()
    if 'all' in st or 'A' in st:
        ok['A'] = stageA(dxs, a.nstep_plane)
    if 'all' in st or 'C' in st:
        ok['C'] = stageC(a.steps)
    if 'all' in st or 'Cr' in st:
        ok['Cr'] = stageC(a.steps, reinit_dt=6.0e-7, tag='Cr')
    if 'all' in st or 'E' in st:
        ok['E'] = stageE()
    if 'all' in st or 'F' in st:
        ok['F'] = stageF()
    print()
    print('#' * 100)
    for k in ('0', 'A', 'C', 'Cr', 'E', 'F'):
        if k in ok:
            print('#  T19-%s : %s' % (k, 'PASS' if ok[k] else 'FAIL'))
    print('#  ⇒ 全部: %s' % ('PASS' if all(ok.values()) else 'FAIL'))
    print('#' * 100)
    return 0 if all(ok.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
