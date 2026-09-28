#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_reinit_deg.py --- R1 reinit 审计（第 7 步）：**在"确实退化"的场上定 iters**。

主代理反馈（要点）：C1 的 `med_in = 0.9945` ⇒ 输入本身已是合格 SDF ⇒
`reinit_skip_tol=0.05` 在生产路径上**本来就会跳过**它 ⇒ 那张表回答的是
"在好场上 Sussman 迭代做多少坏事"（值钱），但**回答不了"iters 该取多少才够"**。

⇒ 本文件补一个**界面真正退化**的场。做法（明确记录用了哪一种）：
  **构造一个界面密度高的配置，关掉全部 reinit 自然演化**（不是人为乘系数 ——
  实测 `sussman_reinit` 内部有 `|_gm−1|>0.2 ⇒ 除以 _gm` 的归一化，
  **整体乘系数会被它精确抵消**，见 `_r1_reinit_posctrl.py` 的 P3）。
  配置 D：N=96 Δx=125 nm L=12 µm，24 个核（3×2×4 格子 + 抖动），变体循环 1..12，
  R=0.50 µm t=0.40 µm ⇒ 界面多、会碰撞 ⇒ 退化快。

三段
  Phase 1 自然演化（reinit 全程关闭），每 10 步记录**全体活跃配对**的带内
          `median|∇d2|`（中心差分，与引擎告警同口径），`med ≤ 0.80` 或 200 步即停。
  Phase 2 在**最差的那一对**上扫 iters，报中心差分/迎风两个量具 + `flips` + `dV`
          + 与 iters=200 的最大逐胞偏差，并给出**恢复到 1±0.02 所需的最小 iters**。
  Phase 3 逐配对账（iters=100）：带胞数、`带胞/N³`、单独计时、是否会被 skip_tol 跳过。

★ 只读引擎；**不改任何引擎代码**。
"""
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic                                # noqa: E402
from windowB_pf3d import argmin_normal as _argmin_normal        # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
MOB, DF = 1e-9, 3.5e8
NPF = {v + 1: _argmin_normal(C, np.asarray(EPS0[v], float))[0] for v in range(NV)}
N, DX = 96, 125e-9
L = N * DX
BAND = 6.0
SKIP_TOL = 0.05
NSTEP_MAX = 200
STOP_MED = 0.80
LAD = [0, 5, 10, 20, 30, 36, 50, 75, 100, 150, 200, 300]
REF = 200
HERE = os.path.dirname(os.path.abspath(__file__))


def gcen(f, dx):
    g = np.gradient(f, dx, edge_order=2)
    return np.sqrt(g[0] ** 2 + g[1] ** 2 + g[2] ** 2)


def gupw(f, dx):
    s = np.sign(f)
    s[s == 0] = 1.0
    return W.upwind_grad2(f, s, dx)


def active_pairs(reg):
    pairs = set()
    for ax in range(3):
        a = reg
        b = np.roll(reg, -1, axis=ax)
        sel = a != b
        if sel.any():
            for x, y in zip(a[sel].ravel(), b[sel].ravel()):
                if x != y:
                    pairs.add((int(min(x, y)), int(max(x, y))))
    return sorted(pairs)


def pair_stats(phi, reg, dx):
    out = []
    for (k, l) in active_pairs(reg):
        d2 = 0.5 * (phi[k] - phi[l])
        near = np.abs(d2) <= BAND * dx
        n = int(near.sum())
        if n == 0:
            continue
        med = float(np.median(gcen(d2, dx)[near]))
        out.append(dict(k=k, l=l, n=n, med=med, frac=n / d2.size))
    return out


def main():
    print('=' * 122)
    print('R1 reinit 审计 / 在"确实退化"的场上定 iters')
    print('  配置 D：N=%d Δx=%.0f nm L=%.1f µm  24 个核（3×2×4 格子）R=0.50 µm t=0.40 µm'
          % (N, DX * 1e9, L * 1e6))
    print('  reinit 全程关闭自然演化；判据 med 用**中心差分**（引擎告警同口径）；'
          '停止条件 med ≤ %.2f 或 %d 步' % (STOP_MED, NSTEP_MAX))
    print('=' * 122)
    t0 = time.time()
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=1, reinit_every=0,
                        reinit_dt=None, reinit_band_cells=BAND)
    print('  建表 %.1f s' % (time.time() - t0), flush=True)
    rng = np.random.default_rng(11)
    ns = 0
    st = np.array([L / 3.0, L / 2.0, L / 4.0])
    for i in range(3):
        for j in range(2):
            for k in range(4):
                c = (np.array([i + 0.5, j + 0.5, k + 0.5]) * st
                     + (rng.random(3) - 0.5) * 0.20 * st)
                kk = ns % NV + 1
                nrm = np.asarray(NPF[kk], float)
                g.seed_plate(kk, c, nrm / np.linalg.norm(nrm), 0.50e-6, 0.40e-6)
                ns += 1
    g.init_parent()
    dt = 0.15 * DX / (MOB * DF)
    print('  种子=%d  dt=%.4e s' % (ns, dt), flush=True)
    reg = g.region()
    f = 1.0 - float((reg == 0).sum()) / g.N ** 3
    print('  [t=0] f=%.5f 活跃配对=%d' % (f, len(active_pairs(reg))), flush=True)
    # ---------------- Phase 1 ----------------
    print()
    print('  ---- Phase 1 自然退化（reinit 关闭）----')
    print('  %5s %9s %7s %11s %11s %11s %11s'
          % ('step', 'f', '配对数', 'med 中位', 'med 最差', 'med 最好', '用时(s)'))
    meds_hist = []
    for it in range(0, NSTEP_MAX + 1, 10):
        if it > 0:
            for _ in range(10):
                g.elastic_driving()
                g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                          mob_beta=3.5, mob_beta_w=2.3, adv_grad='proj2')
        reg = g.region()
        f = 1.0 - float((reg == 0).sum()) / g.N ** 3
        ps = pair_stats(g.phi, reg, DX)
        if not ps:
            print('     ⚠ 无活跃配对 ⇒ 停'); break
        ms = np.array([p['med'] for p in ps])
        meds_hist.append((it, f, ms.copy()))
        print('  %5d %9.5f %7d %11.5f %11.5f %11.5f %11.1f'
              % (it, f, len(ps), float(np.median(ms)), float(ms.min()),
                 float(ms.max()), time.time() - t0), flush=True)
        if float(np.median(ms)) <= STOP_MED:
            print('     ⇒ 达到停止条件 med≤%.2f' % STOP_MED)
            break
        if f > 0.60:
            print('     ⇒ f>0.60（impingement 主导）⇒ 停，避免把"碰撞"当成"退化"')
            break
    # ---------------- Phase 2 ----------------
    ps = pair_stats(g.phi, g.region(), DX)
    ps.sort(key=lambda p: p['med'])
    worst = ps[0]
    k, l = worst['k'], worst['l']
    d2_in = 0.5 * (g.phi[k] - g.phi[l])
    near = np.abs(d2_in) <= BAND * DX
    n0neg = int((d2_in < 0).sum())
    print()
    print('  ---- Phase 2 在最差配对 (k=%d,l=%d) 上扫 iters：带胞=%d (%.3f%%) '
          'med_in=%.5f  #d2<0=%d ----'
          % (k, l, worst['n'], 100 * worst['frac'], worst['med'], n0neg), flush=True)
    print('  %6s %8s %11s %11s %10s %9s %9s %12s'
          % ('iters', 'time_s', 'med|∇|中心', 'med|∇|迎风', 'flips', 'dV(胞)',
             'dmax(胞)', 'max|Δ−REF|'))
    t0 = time.time()
    ref = g.sussman_reinit(d2_in.copy(), iters=REF)
    med_ref = float(np.median(gcen(ref, DX)[near]))
    res = {}
    for n in LAD:
        t1 = time.time()
        dn = d2_in.copy() if n == 0 else g.sussman_reinit(d2_in.copy(), iters=n)
        el = time.time() - t1
        mc = gcen(dn, DX)[near]
        mu = gupw(dn, DX)[near]
        dv = int((dn < 0).sum()) - n0neg
        fl = int((np.where(d2_in < 0, 0, 1) != np.where(dn < 0, 0, 1)).sum())
        dev = float(np.max(np.abs(dn[near] - ref[near])) / DX)
        print('  %6d %8.3f %11.5f %11.5f %10d %9d %9.5f %12.4f'
              % (n, el, float(np.median(mc)), float(np.median(mu)), fl, dv,
                 float(np.max(np.abs(dn[near] - d2_in[near]))) / DX, dev),
              flush=True)
        res[n] = (float(np.median(mc)), float(np.median(mu)), fl, dv, dev)
    ok = [n for n in LAD if n > 0 and abs(res[n][0] - 1.0) <= 0.02]
    oku = [n for n in LAD if n > 0 and abs(res[n][1] - 1.0) <= 0.02]
    print('  ⇒ **中心差分口径**恢复到 1±0.02 的最小 iters = %s'
          % (min(ok) if ok else '无（到 %d 仍未达）' % max(LAD)))
    print('  ⇒ **迎风口径**恢复到 1±0.02 的最小 iters = %s'
          % (min(oku) if oku else '无（到 %d 仍未达）' % max(LAD)))
    print('  ⇒ REF(200) 的中心/迎风口径 = %.5f / %.5f'
          % (med_ref, float(np.median(gupw(ref, DX)[near]))))
    print('  ⇒ 输入 med_in（中心/迎风）= %.5f / %.5f'
          % (float(np.median(gcen(d2_in, DX)[near])),
             float(np.median(gupw(d2_in, DX)[near]))))
    # ---------------- Phase 3 ----------------
    print()
    print('  ---- Phase 3 逐配对账（iters=100）：带胞、占比、单独计时、skip 判据 ----')
    print('  %4s %4s %9s %8s %10s %10s %9s %9s'
          % ('k', 'l', '带胞', '带胞/N³', 'med_in', '会被跳过', 't₃₆(s)', 't₁₀₀(s)'))
    tot36 = tot100 = 0.0
    nsk = 0
    for p in ps[:12]:
        kk, ll = p['k'], p['l']
        dd = 0.5 * (g.phi[kk] - g.phi[ll])
        t1 = time.time()
        g.sussman_reinit(dd, iters=36)
        t36 = time.time() - t1
        t1 = time.time()
        g.sussman_reinit(dd, iters=100)
        t100 = time.time() - t1
        sk = abs(p['med'] - 1.0) <= SKIP_TOL
        nsk += int(sk)
        tot36 += t36
        tot100 += t100
        print('  %4d %4d %9d %7.3f%% %10.5f %10s %9.3f %9.3f'
              % (kk, ll, p['n'], 100 * p['frac'], p['med'],
                 'YES' if sk else 'no', t36, t100), flush=True)
    print('  ⇒ 前 %d 对合计：iters=36 用 %.1f s，iters=100 用 %.1f s ⇒ **比值 %.2f×**'
          % (min(12, len(ps)), tot36, tot100, tot100 / max(tot36, 1e-9)))
    print('  ⇒ 其中会被 `reinit_skip_tol=%.2f` **跳过**的 = %d / %d'
          % (SKIP_TOL, nsk, min(12, len(ps))))
    print('  ⇒ 全体配对 med 分布：min=%.4f p25=%.4f 中位=%.4f max=%.4f'
          % (min(p['med'] for p in ps),
             float(np.percentile([p['med'] for p in ps], 25)),
             float(np.median([p['med'] for p in ps])),
             max(p['med'] for p in ps)))
    print()
    print('  ⚠ 记账：本配置的**盒长 L=%.1f µm < 2×板条长(8.1µm)** ⇒ 违反 R24 盒长守卫；'
          '本文件**只用于 reinit 数值学**，不得出任何形貌读数。' % (L * 1e6))
    print('=' * 122)
    return 0


if __name__ == '__main__':
    sys.exit(main())
