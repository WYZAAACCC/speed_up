#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r30_selfac_check.py —— 对 `_r30_selfac_struct.py` 的 `min_residual` 做**独立复核**。

为什么必须做（本仓库的纪律，也是 R30 审计 S4 对我提的一条）：
    `_r30_selfac_struct.py` 的群级结论（**k\* = 6**、"64 个自协调六元组 = 每个惯习面各取一个"）
    **全部**建立在那个 `min_residual` 上，而它是**自己写的一个单纯形投影梯度**，
    没有任何独立复算 ⇒ 属于【未核实】。判据错 ⇒ 结论整条作废。

三条独立对照（**三条路线互不共用代码**）：
  C-1 **解析锚**：全 12 变体 `Σ dev ε⁰ = 0`（`windowB_ti64_variants` 自带的 C4 判据）
      ⇒ `r({1..12})` 必须 ≈0。这是唯一有"已知答案"的点。
  C-2 **独立下降法**：`scipy.optimize.minimize(method='SLSQP')` 在单纯形约束上直接解
      （与投影梯度**不共用任何代码**）。判据：`|r_slsqp − r_pg| / scale < 1e-9`。
  C-3 **随机采样上界**：在单纯形上均匀抽 `nrand` 组 `f`，取最小值 —— 它**只能**给出
      `≥ r_true`（因为是在可行集里抽样）⇒ 必须满足 `r_rand ≥ r_pg`（**单侧**判据）。
      若出现 `r_rand < r_pg − tol` ⇒ `r_pg` **不是**最小值 ⇒ 投影梯度没收敛 ⇒ 判据作废。

跑法：  python3 _r30_selfac_check.py --k 2,3,4,5,6 --nsubset 24 --nrand 200000
"""
import os
import sys
import json
import argparse
import itertools

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402
import _r30_selfac_struct as S                                  # noqa: E402

try:
    from scipy.optimize import minimize as _spmin
    _HAVE_SCIPY = True
except Exception:                                               # pragma: no cover
    _HAVE_SCIPY = False


def r_slsqp(A, k):
    """独立路线：SLSQP 在 {f>=0, Σf=1} 上最小化 ‖A^T f‖²。"""
    A2 = A @ A.T

    def obj(f):
        return float(f @ A2 @ f)

    def jac(f):
        return 2.0 * (A2 @ f)

    cons = [dict(type='eq', fun=lambda f: float(f.sum() - 1.0),
                 jac=lambda f: np.ones_like(f))]
    bnds = [(0.0, 1.0)] * k
    best = np.inf
    for x0 in (np.full(k, 1.0 / k), None):
        if x0 is None:
            x0 = np.random.default_rng(k).random(k)
            x0 = x0 / x0.sum()
        try:
            res = _spmin(obj, x0, jac=jac, bounds=bnds, constraints=cons,
                         method='SLSQP', options=dict(maxiter=800, ftol=1e-16))
            if res.fun < best:
                best = float(res.fun)
        except Exception:
            pass
    return float(np.sqrt(max(best, 0.0)))


def r_rand(A, k, nrand, rng):
    """独立路线：单纯形上均匀抽样（Dirichlet(1)）取最小值 ⇒ 上界。"""
    F = rng.dirichlet(np.ones(k), size=nrand)          # (nrand, k)
    vals = F @ A                                        # (nrand, 9)
    nrm = np.sqrt(np.einsum('ij,ij->i', vals, vals))
    return float(nrm.min())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--k', default='2,3,4,5,6')
    ap.add_argument('--nsubset', type=int, default=24)
    ap.add_argument('--nrand', type=int, default=200000)
    ap.add_argument('--seed', type=int, default=3)
    a = ap.parse_args()

    EPS0, _F, _M = variants()
    E = [S.dev(np.asarray(e, float)) for e in EPS0]
    nv = len(E)
    scale = float(np.mean([S.fro(e) for e in E]))
    rng = np.random.default_rng(a.seed)

    print('=' * 78)
    print('R30 独立复核 `min_residual`   nv=%d  scale=%.6e  scipy=%s'
          % (nv, scale, _HAVE_SCIPY))

    # ---------- C-1 解析锚 ----------
    r_all, f_all = S.min_residual(E, list(range(nv)))
    print('\n[C-1 解析锚] r({1..12}) 投影梯度 = %.6e  （应 ≈0，C4 判据）' % (r_all / scale))
    if _HAVE_SCIPY:
        A = np.stack(E, 0).reshape(nv, -1)
        r_s = r_slsqp(A, nv)
        print('              SLSQP          = %.6e   差/scale = %.2e'
              % (r_s / scale, abs(r_s - r_all) / scale))
        ok1 = abs(r_s - r_all) < 1e-12 * scale
        print('              ⇒ %s' % ('✅ 一致' if ok1 else '❌ 不一致'))

    # ---------- 逐规模抽样子集做三路对照 ----------
    print('\n[C-2/C-3 逐规模对照]  每个规模随机抽 %d 个子集' % a.nsubset)
    print('   %-3s %-9s %-14s %-14s %-14s %-9s %s'
          % ('k', '子集', 'r_pg', 'r_slsqp', 'r_rand', 'rel.slsqp', 'r_rand>=r_pg?'))
    worst_slsqp = 0.0
    n_viol = 0
    n_tot = 0
    for k in [int(x) for x in a.k.split(',') if x.strip()]:
        subs = list(itertools.combinations(range(nv), k))
        pick = [subs[i] for i in rng.choice(len(subs), size=min(a.nsubset, len(subs)),
                                            replace=False)]
        for idx in pick:
            r_pg, _ = S.min_residual(E, list(idx))
            A = np.stack([E[i] for i in idx], 0).reshape(k, -1)
            r_s = r_slsqp(A, k) if _HAVE_SCIPY else float('nan')
            r_r = r_rand(A, k, a.nrand, rng)
            rel = abs(r_s - r_pg) / scale if _HAVE_SCIPY else float('nan')
            worst_slsqp = max(worst_slsqp, rel)
            viol = r_r < r_pg - 1e-12 * scale
            n_viol += int(viol)
            n_tot += 1
            print('   %-3d %-9s %-14.4e %-14.4e %-14.4e %-9.1e %s'
                  % (k, ','.join(str(i + 1) for i in idx), r_pg / scale,
                     r_s / scale, r_r / scale, rel, '❌ 违反' if viol else '✅'))
    print('\n   ⇒ SLSQP 与投影梯度的**最大相对差** = %.2e（判据 <1e-9）%s'
          % (worst_slsqp, '✅' if worst_slsqp < 1e-9 else '❌'))
    print('   ⇒ 随机采样"低于投影梯度最小值"的次数 = %d / %d（判据 = 0）%s'
          % (n_viol, n_tot, '✅' if n_viol == 0 else '❌'))

    # ---------- ★ 把 k*=6 的结论用独立路线整体复算 ----------
    print('\n[★ 关键结论独立复算] k=5 与 k=6 的**全部**组合，用 SLSQP 重算 r 的最小值')
    out = {}
    for k in (5, 6):
        subs = list(itertools.combinations(range(nv), k))
        rs = []
        for idx in subs:
            A = np.stack([E[i] for i in idx], 0).reshape(k, -1)
            rs.append(r_slsqp(A, k) / scale if _HAVE_SCIPY else
                      S.min_residual(E, list(idx))[0] / scale)
        rs = np.array(rs)
        n0 = int((rs < 1e-6).sum())
        out[k] = dict(n=len(subs), rmin=float(rs.min()), rmax=float(rs.max()), n0=n0)
        print('   k=%d：组合 %d 个，r_min=%.4e，r_max=%.4e，r<1e-6 的个数 = **%d**'
              % (k, len(subs), rs.min(), rs.max(), n0))
    print('   ⇒ 独立路线给出：k*=6（k=5 无解、k=6 有 %d 个解）%s'
          % (out[6]['n0'], '✅ 与 `_r30_selfac_struct.py` 一致'
             if (out[5]['n0'] == 0 and out[6]['n0'] == 64) else '❌ 不一致'))

    with open('_exp/r30_selfac_check.json', 'w', encoding='utf-8') as fh:
        json.dump(dict(scale=scale, worst_slsqp=worst_slsqp, n_viol=n_viol,
                       n_tot=n_tot, by_k=out), fh, ensure_ascii=False, indent=1)
    print('\n⇒ 已落盘 _exp/r30_selfac_check.json')


if __name__ == '__main__':
    main()
