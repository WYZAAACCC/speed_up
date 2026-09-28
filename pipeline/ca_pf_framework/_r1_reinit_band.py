#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_reinit_band.py --- R1 reinit 审计（第 3 步）：**Q-B 窄带 vs 全域 / 逐配对的浪费**。

★ 只读引擎；**不改任何引擎代码**。

三次测量
--------
B1 **逐配对账**：用与 `reinitialize()` **同一套**配对枚举算法列出活跃配对；
   对每一对算：带胞数、`带胞/N³`、带内 `median|∇d2|`（决定它会不会被
   `reinit_skip_tol=0.05` 跳过）、以及**单独计时** `g.sussman_reinit(d2)`（= 引擎内部那一句）。
   正对照：`Σ(每对时间)` 必须能解释实测的 `reinitialize()` 总时间（误差应只在
   `reinitialize()` 自己的 argmin/argsort 开销量级）。

B2 **包围盒（bbox）对照**：把 Sussman 迭代限制在 `near` 掩模的**包围盒**（外扩 pad 胞）内，
   与全域做对比。用 `W._bbox_pad`（引擎自带、`T3_verify_fastpath.py` 已验证过的工具）。
   判据：带内逐胞最大差（胞）与 `region` 翻转数；同时**核验归一化统计量**
   `_gm = median(|∇d2| over |d2|≤6dx)` 在子盒与全域是否相同（不同 ⇒ 缩放分支被改动 ⇒ 结论无效）。
   ⚠ **必须记账的风险**：子盒内的 `np.roll` 在**子盒**上周期卷绕，与全域不同；
   只有当 pad > 特性线传播距离时带内才不受影响。本文件扫 pad 就是为了把"多大才够"量出来。

B3 **触发统计**：`reinit_skip_tol` 在实际状态下到底跳过了多少对（决定"100 次迭代"
   在真实轨迹上是否根本就没被执行）。
"""
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic                                # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
MOB, DF = 1e-9, 3.5e8
HERE = os.path.dirname(os.path.abspath(__file__))
BAND = 6.0
SKIP_TOL = 0.05
# ★ 记账：生成器把 L/dx 放在 `meta` 里但**没有写进 npz**（只写了 phi 帧）
#   ⇒ 这里用硬编码表兜底，并断言 N*dx == L。
TAGCFG = {'C1': (96 * 250e-9, 250e-9), 'C2': (96 * 125e-9, 125e-9)}


def cfg_of(z, tag, N):
    if ('%s_L' % tag) in z.files:
        return float(z['%s_L' % tag]), float(z['%s_dx' % tag])
    L, dx = TAGCFG[tag]
    assert abs(N * dx - L) < 1e-18, (tag, N, dx, L)
    return L, dx


def gradmag(f, dx):
    g = np.gradient(f, dx, edge_order=2)
    return np.sqrt(g[0] ** 2 + g[1] ** 2 + g[2] ** 2)


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


def gm_of(f, dx, band=BAND):
    sel = np.abs(f) <= band * dx
    if not sel.any():
        return np.nan
    return float(np.median(gradmag(f, dx)[sel]))


def overhead(g, phi0):
    """B0：`reinitialize()` 里**除逐对 Sussman 之外**的开销分解。"""
    print('  --- B0 reinitialize() 的非 Sussman 开销 ---')
    t0 = time.time()
    for _ in range(3):
        reg = g.region()
    t_reg = (time.time() - t0) / 3.0
    _o = np.argsort(phi0, axis=0)
    t0 = time.time()
    _o = np.argsort(phi0, axis=0)
    t_sort = time.time() - t0
    t0 = time.time()
    _ = g._band_bonds(reg)
    _ = g._band_bonds(reg)
    t_bb = (time.time() - t0) / 2.0
    _kb = 1e-6 * phi0.nbytes
    print('     region()(argmin over %d 场) = %.3f s   argsort(%d 场) = %.3f s   '
          '_band_bonds = %.3f s   phi 占用 = %.1f MB'
          % (phi0.shape[0], t_reg, phi0.shape[0], t_sort, t_bb, _kb), flush=True)
    return t_reg, t_sort, t_bb


def run_state(key, phi0, L, dx, g, iters_list, pads):
    N = phi0.shape[1]
    reg = np.argmin(phi0, axis=0).astype(np.int8)
    pairs = active_pairs(reg)
    print()
    print('#### 状态 %s : N=%d Δx=%.1f nm L=%.3f µm  活跃配对=%d'
          % (key, N, dx * 1e9, N * dx * 1e6, len(pairs)), flush=True)
    overhead(g, phi0)
    # ---------------- B1 逐配对账 ----------------
    rows = []
    tsum = {n: 0.0 for n in iters_list}
    for (k, l) in pairs:
        d2 = 0.5 * (phi0[k] - phi0[l])
        near = np.abs(d2) <= BAND * dx
        nb = int(near.sum())
        if nb == 0:
            continue
        med = gm_of(d2, dx)
        skipped = abs(med - 1.0) <= SKIP_TOL
        # 只对 largest 的若干对做全 iters 计时（省机时），其余只做基准 iters
        for n in iters_list:
            t0 = time.time()
            g.sussman_reinit(d2, iters=n)
            el = time.time() - t0
            if n == iters_list[0]:
                rows.append(dict(k=k, l=l, nb=nb, frac=nb / d2.size, med=med,
                                 skipped=skipped, t=el))
            tsum[n] += el
    print('  --- B1 逐配对账（时间列 = 单独调用 g.sussman_reinit(d2) 的 wall）---')
    print('  %5s %5s %9s %8s %9s %8s %10s' %
          ('k', 'l', '带胞', '带胞/N³', 'median|∇d2|', '会被跳过', 't_iters=%d (s)'
           % iters_list[0]))
    for r in rows:
        print('  %5d %5d %9d %7.3f%% %9.4f %8s %10.3f'
              % (r['k'], r['l'], r['nb'], 100 * r['frac'], r['med'],
                 'YES' if r['skipped'] else 'no', r['t']), flush=True)
    nskip = sum(1 for r in rows if r['skipped'])
    tot_band = sum(r['nb'] for r in rows)
    print('  ⇒ 配对数=%d  其中**会被 skip_tol 跳过**=%d  带胞合计=%d (%.3f%% of N³)'
          % (len(rows), nskip, tot_band, 100 * tot_band / phi0[0].size))
    # 正对照：Σ 每对时间 vs 实测 reinitialize() 总时间
    for n in iters_list:
        g.phi = phi0.copy()
        g.reinit_iters = n
        g._reinit_done = 0
        g._reinit_skipped = 0
        t0 = time.time()
        g.reinitialize()
        tot = time.time() - t0
        print('  [正对照] iters=%3d : Σ(逐对)=%7.2f s  实测 reinitialize()=%7.2f s  '
              '比值=%.3f  done=%d skipped=%d  region翻转=%d'
              % (n, tsum[n], tot, tsum[n] / max(tot, 1e-9),
                 getattr(g, '_reinit_done', 0), getattr(g, '_reinit_skipped', 0),
                 getattr(g, '_reinit_reg_flips_last', -1)), flush=True)
    # ---------------- B3 强制（force=True）路径 ----------------
    g.phi = phi0.copy()
    g.reinit_iters = 100
    g._reinit_done = 0
    g._reinit_skipped = 0
    t0 = time.time()
    g.reinitialize(force=True)
    print('  [B3] force=True : %.2f s  done=%d skipped=%d（force 下 skipped 应为 0）'
          % (time.time() - t0, getattr(g, '_reinit_done', 0),
             getattr(g, '_reinit_skipped', 0)), flush=True)
    # ---------------- B2 包围盒对照 ----------------
    big = max(rows, key=lambda r: r['nb']) if rows else None
    if big is None:
        return
    k, l = big['k'], big['l']
    d2 = 0.5 * (phi0[k] - phi0[l])
    near = np.abs(d2) <= BAND * dx
    gm_full = gm_of(d2, dx)
    print()
    print('  --- B2 包围盒对照：配对 (k=%d,l=%d) 带胞=%d  全域 _gm=%.5f ---'
          % (k, l, big['nb'], gm_full), flush=True)
    for n in iters_list:
        full = g.sussman_reinit(d2.copy(), iters=n)
        for pad in pads:
            sl = W._bbox_pad(near, pad=pad, wrap=True)
            if sl is None:
                continue
            shp = tuple(s.stop - s.start for s in sl)
            sub = d2[sl].copy()
            nsub = int(near[sl].sum())
            gsub = gm_of(sub, dx)
            t0 = time.time()
            subr = g.sussman_reinit(sub, iters=n)
            el = time.time() - t0
            # 只比较**带内**胞
            m = near[sl]
            dmax = float(np.max(np.abs(subr[m] - full[sl][m])) / dx)
            dmed = float(np.median(np.abs(subr[m] - full[sl][m])) / dx)
            nr0 = int(near.sum())
            nflip = int((np.where(subr < 0, 0, 1)[m] !=
                         np.where(full[sl] < 0, 0, 1)[m]).sum())
            # 子盒体积占比 ⇒ 潜在加速
            vfrac = np.prod(shp) / float(d2.size)
            print('     iters=%3d pad=%2d 盒=%-15s 盒/N³=%6.2f%% 子盒_gm=%.5f '
                  '带内dmax=%9.2e 胞  dmed=%8.2e  flips=%6d  t=%6.2f s (全域 %6.2f s) 省=%.2f×'
                  % (n, pad, str(shp), 100 * vfrac, gsub, dmax, dmed, nflip, el,
                     big['t'] * n / iters_list[0], (big['t'] * n / iters_list[0]) / max(el, 1e-9)),
                  flush=True)
    print('     ⚠ 记账：子盒内 `np.roll` **在子盒上周期卷绕**（与全域不同）。'
          'pad 不够时带内会被污染 ⇒ 上式 dmax 就是"污染有多大"的直接读数。')


def main():
    z = np.load(os.path.join(HERE, '_r1_reinit_states.npz'))
    print('=' * 118)
    print('R1 reinit 审计 / Q-B：窄带 vs 全域、逐配对账、包围盒对照')
    print('  reinit_skip_tol=%.2f  band_cells=%.1f' % (SKIP_TOL, BAND))
    print('=' * 118)
    gcache = {}
    for key in sorted(z.files):
        phi0 = z[key]
        tag = key.split('_')[0]
        N = phi0.shape[1]
        L, dx = cfg_of(z, tag, N)
        if tag not in gcache:
            t0 = time.time()
            gcache[tag] = W.LevelSetMulti(
                N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                df=[0.0] + [DF] * NV, workers=1, reinit_every=0,
                reinit_dt=None, reinit_band_cells=BAND)
            print('\n####### 配置 %s 建表 %.1f s' % (tag, time.time() - t0), flush=True)
        g = gcache[tag]
        run_state(key, phi0, L, dx, g, [100, 36], [2, 4, 8, 16, 24])
    print('=' * 118)
    return 0


if __name__ == '__main__':
    sys.exit(main())
