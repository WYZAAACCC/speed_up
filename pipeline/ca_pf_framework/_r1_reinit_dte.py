#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_reinit_dte.py --- R1 reinit 审计（第 8 步）：**定位"为什么需要 100 次迭代"**。

动机（Q-A 实测逼出来的问题）
---------------------------
Q-A 在退化场上（`med_in=0.9657`）实测：`med_out` 随 iters **先掉后回**
（5→0.941, 20→0.876, 36→0.870, 50→0.933, 75→0.987, 100→0.993）。
而"几何传播"论证只要求 **36 次**（带宽 ±6 胞，每步推进 dτ=dx/6 ⇒ 1/6 胞/次）。
⇒ 两者差 3 倍，**必须找出被谁吃掉了**。

主假设（可证伪）：
  引擎每次迭代用 `_dte = min(dτ, (dx/6)/max(gm[_sel], 1))`（`_sussman_core` 第 284-285 行）。
  `gm` 是 `upwind_grad2`，它**必然在脊线/中轴处给出伪尖峰**（仓库已有记账：
  同一场全域 max 中心差分 = 1.00，而 `upwind_grad2` = **68.5**）。
  A-1 已把统计量域从"全域"收到"带内"，但**带内仍有脊线** ⇒
  若 `max(gm[带内]) = M ≫ 1`，则有效伪时间只有名义的 `1/M`
  ⇒ **100 次名义迭代只等于 100/M 次有效迭代**。

做法（★ 只读引擎，**不改 `windowB_surface.py`**）
----------------------------------------------
1. 在本文件里**逐行复制** `_sussman_core`（含归一化/`S`/`_sel`/clip/guard）为一个
   可换统计量的副本 `my_core(..., stat)`；`stat ∈ {'max'(=引擎行为), 'p999','p99','none'}`。
2. **正对照**：`my_core(stat='max')` 必须与 `W.sussman_reinit(...)` **逐位相同**；
   不同则本文件的一切结论作废（打印判定）。
3. 报告带内 `upwind_grad2` 的分布（median/p90/p99/p99.9/max）与**节流比 `1/M`**。
4. 扫 iters × stat，看"放开节流后需要多少次迭代"。

⚠ 风险记账：`p99/p999/none` 会让个别胞**违反 CFL**（gm 大于该分位数处）。
  更新被 `clip(±0.5dx)` 兜住，但**可能牺牲精度/单调性** ⇒ 必须同时报
  `max|φ|` 是否触发发散守卫、以及 `med_out` 是否真的更好。**不作为建议直接给出**，
  除非三档一致且无守卫触发。
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
TAGCFG = {'C1': (96 * 250e-9, 250e-9), 'C2': (96 * 125e-9, 125e-9)}
LAD = [10, 20, 30, 36, 50, 75, 100]


def my_core(phi, dx, iters, dtau, grad, guard, band_cells, stat='max',
            trace=None):
    """**逐行复制** `windowB_surface._sussman_core`（唯一差异 = `_gmax` 的取法）。"""
    phi0 = phi.copy()
    _g = np.gradient(phi0, dx, edge_order=2)
    _gn = np.sqrt(sum(_gi ** 2 for _gi in _g))
    _sel = None
    if band_cells is not None:
        _sel = np.abs(phi0) <= float(band_cells) * dx
        if not _sel.any():
            _sel = None
    _gm = float(np.median(_gn if _sel is None else _gn[_sel]))
    if _gm > 1e-12 and abs(_gm - 1.0) > 0.2:
        phi = phi / _gm
        phi0 = phi0 / _gm
    S = phi0 / np.sqrt(phi0 ** 2 + dx ** 2)
    if dtau is None:
        dtau = 0.5 * dx / 3.0
    _phi_raw = phi0.copy()
    _lim0 = float(np.max(np.abs(phi0))) + dx
    for _ in range(int(iters)):
        if grad == 'upwind':
            gm = W.upwind_grad(phi, S, dx)
        elif grad == 'upwind2':
            gm = W.upwind_grad2(phi, S, dx)
        elif grad == 'central':
            g = np.gradient(phi, dx, edge_order=2)
            gm = np.sqrt(sum(gi ** 2 for gi in g))
        else:
            gm = W.grad_sym(phi, dx)
        _v = gm if _sel is None else gm[_sel]
        if stat == 'max':
            _gmax = float(np.max(_v))
        elif stat == 'p999':
            _gmax = float(np.percentile(_v, 99.9))
        elif stat == 'p99':
            _gmax = float(np.percentile(_v, 99.0))
        elif stat == 'none':
            _gmax = 1.0
        else:
            raise ValueError(stat)
        if trace is not None:
            trace.append(_gmax)
        _dte = min(dtau, 0.5 * dx / 3.0 / max(_gmax, 1.0))
        _upd = _dte * S * (gm - 1.0)
        phi = phi - np.clip(_upd, -0.5 * dx, 0.5 * dx)
        if guard and float(np.max(np.abs(phi))) > 10.0 * _lim0:
            return _phi_raw, True
    return phi, False


def gcen(f, dx):
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


def main():
    z = np.load(os.path.join(HERE, '_r1_reinit_states.npz'))
    print('=' * 122)
    print('R1 reinit 审计 / `_dte` 节流定位（为什么"几何上只需 36 次"却要 100 次）')
    print('=' * 122)
    gcache = {}
    for key in ('C1_s06', 'C1_s40', 'C2_s06', 'C2_s40'):
        if key not in z.files:
            continue
        phi0 = z[key]
        tag = key.split('_')[0]
        N = phi0.shape[1]
        L, dx = TAGCFG[tag]
        if tag not in gcache:
            gcache[tag] = W.LevelSetMulti(
                N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                df=[0.0] + [DF] * NV, workers=1, reinit_every=0,
                reinit_dt=None, reinit_band_cells=BAND)
        g = gcache[tag]
        reg = np.argmin(phi0, axis=0).astype(np.int8)
        cand = []
        for (k, l) in active_pairs(reg):
            d2 = 0.5 * (phi0[k] - phi0[l])
            near = np.abs(d2) <= BAND * dx
            cand.append((float(np.median(gcen(d2, dx)[near])), int(near.sum()),
                         k, l))
        cand.sort()
        med_in, nb, k, l = cand[0]          # 取**最差**那一对（reinit 最可能真跑）
        d2_in = 0.5 * (phi0[k] - phi0[l])
        near = np.abs(d2_in) <= BAND * dx
        print('\n  #### %s  最差配对 (k=%d,l=%d) 带胞=%d (%.3f%%)  med_in=%.5f'
              % (key, k, l, nb, 100 * nb / d2_in.size, med_in), flush=True)
        # ---- 正对照：my_core(stat='max') == W.sussman_reinit ----
        a1, _ = my_core(d2_in.copy(), dx, 20, None, 'upwind2', True, BAND, 'max')
        a2 = W.sussman_reinit(d2_in.copy(), dx, iters=20, band_cells=BAND)
        bit = bool(np.array_equal(a1, a2))
        print('     [正对照] my_core(max) vs W.sussman_reinit(iters=20)：逐位相同 = %s '
              ' max|Δ|/dx=%.3e  ⇒ %s'
              % (bit, float(np.max(np.abs(a1 - a2))) / dx,
                 '复刻可信' if bit else '★复刻不可信，以下结论全部作废★'), flush=True)
        if not bit:
            print('     （仍继续跑，仅供诊断；不得作为结论）')
        # ---- 带内 gm 分布（节流比）----
        s = np.sign(d2_in)
        s[s == 0] = 1.0
        gu = W.upwind_grad2(d2_in, s, dx)[near]
        gc_ = gcen(d2_in, dx)[near]
        print('     带内 upwind_grad2 分布：中位=%.4f p90=%.3f p99=%.3f p99.9=%.3f '
              'max=%.3f ⇒ **节流比 1/M = %.4f**'
              % (float(np.median(gu)), float(np.percentile(gu, 90)),
                 float(np.percentile(gu, 99)), float(np.percentile(gu, 99.9)),
                 float(gu.max()), 1.0 / max(float(gu.max()), 1.0)), flush=True)
        print('     带内 中心差分   分布：中位=%.4f p90=%.3f p99=%.3f p99.9=%.3f max=%.3f'
              % (float(np.median(gc_)), float(np.percentile(gc_, 90)),
                 float(np.percentile(gc_, 99)), float(np.percentile(gc_, 99.9)),
                 float(gc_.max())), flush=True)
        # ---- 扫 iters × stat ----
        print()
        print('     %6s | %-9s %-9s %-7s %-6s | %-9s %-9s %-7s %-6s | %-9s %-7s %-6s'
              % ('iters', 'max:med', 'max:gmax*', 'max:dV', 'max:gd',
                 'p999:med', 'p999:gmax*', 'p999:dV', 'p999:gd',
                 'none:med', 'none:dV', 'none:gd'))
        print('     (* = 全程 max(_gmax) 的中位；gd = 发散守卫触发)')
        t0 = time.time()
        for n in LAD:
            row = {}
            for stat in ('max', 'p999', 'none'):
                tr = []
                t1 = time.time()
                out, gd = my_core(d2_in.copy(), dx, n, None, 'upwind2', True,
                                  BAND, stat, trace=tr)
                row[stat] = (float(np.median(gcen(out, dx)[near])),
                             float(np.median(tr)), int((out < 0).sum()) -
                             int((d2_in < 0).sum()), gd, time.time() - t1)
            print('     %6d | %-9.5f %-9.4f %-7d %-6s | %-9.5f %-9.4f %-7d %-6s | '
                  '%-9.5f %-7d %-6s'
                  % (n, row['max'][0], row['max'][1], row['max'][2],
                     'Y' if row['max'][3] else '-',
                     row['p999'][0], row['p999'][1], row['p999'][2],
                     'Y' if row['p999'][3] else '-',
                     row['none'][0], row['none'][2],
                     'Y' if row['none'][3] else '-'), flush=True)
        print('     用时 %.1f s' % (time.time() - t0))
    print()
    print('=' * 122)
    return 0


if __name__ == '__main__':
    sys.exit(main())
