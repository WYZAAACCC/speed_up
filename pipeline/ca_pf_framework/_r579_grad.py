#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r579_grad.py --- goal §(6)：`gradient(mode='sliced')` 的**逐位判据 + 负对照 + 微基准**。

## 判据（先写死，必须能失败）
* **P1 逐位（单线程路）**：`ParCtx(nthreads=1).gradient(phi, dx, 2, mode='sliced')`
  与 `np.gradient(phi, dx, edge_order=2)` 三个分量**全部逐位相同**。
* **P2 逐位（并行路）**：`nthreads=4` 与 `nthreads=1` 逐位相同（**线程数不是物理参数**）。
* **P3 边界真的被覆盖**：单独检查**首末两层**逐位相同（内部相同而边界不同是最可能的失败模式）。
* **P4 负对照（必须有分辨力）**：
  (a) 把左边界系数从 `-1.5/dx` 改成 `(-1.5*f0 + 2*f1 - 0.5*f2)/dx` 的"先分子后除"写法
      ⇒ **必须**出现非零差（证明 P1 抓的正是舍入路径）；
  (b) 把边界换成**周期**切片 ⇒ 必须出现**大**差。
* **P5 微基准**：legacy vs sliced，交错配对，报中位与区间。
"""
import os
import statistics
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_par as PAR                                      # noqa: E402

N = int(os.environ.get('R579X_N', '64'))
NT = int(os.environ.get('R579X_NT', '4'))
REPS = int(os.environ.get('R579X_REPS', '11'))
OUT = os.environ.get('R579X_OUT', '_w2_r579_grad.log')


def _naive_edge(f, dx):
    """负对照 (a)：**先算分子再除**的等价数学写法（舍入路径不同）。"""
    nd = f.ndim
    out = []
    for ax in range(nd):
        o = np.empty_like(f)
        base = [slice(None)] * nd

        def _s(i):
            t = list(base)
            t[ax] = i
            return tuple(t)

        o[_s(slice(1, -1))] = (f[_s(slice(2, None))] - f[_s(slice(None, -2))]) / (2. * dx)
        o[_s(0)] = (-1.5 * f[_s(0)] + 2. * f[_s(1)] - 0.5 * f[_s(2)]) / dx
        o[_s(-1)] = (0.5 * f[_s(-3)] - 2. * f[_s(-2)] + 1.5 * f[_s(-1)]) / dx
        out.append(o)
    return out


def _periodic_edge(f, dx):
    """负对照 (b)：边界也用中心差分（**周期**，即切片版的"错"写法）。"""
    nd = f.ndim
    out = []
    for ax in range(nd):
        o = np.empty_like(f)
        base = [slice(None)] * nd

        def _s(i):
            t = list(base)
            t[ax] = i
            return tuple(t)

        o[...] = (np.roll(f, -1, axis=ax) - np.roll(f, 1, axis=ax)) / (2. * dx)
        out.append(o)
    return out


def main():
    L = []
    A = L.append
    rng = np.random.default_rng(17)
    phi = rng.standard_normal((N, N, N))
    # ★★ 判据必须在**生产 dx** 上做，两个原因：
    #   ① `--dx-nm 62.5` ⇒ dx = 6.25e-8 m，**不是 2 的幂** ⇒ 除法会舍入；
    #   ② 我第一版用 `dx = 0.0625 = 2^-4`（**2 的幂**）⇒ `a*f0 + b*f1 + c*f2`
    #      与 `(-1.5f0 + 2f1 − 0.5f2)/dx` 在浮点下**恰好给出同一批位**
    #      （乘 1.5 的舍入一样，除以 2^-4 是精确缩放）
    #      ⇒ 负对照 P4a **恒等于 0、静默失效**。
    #   ⇒ 这正是"量具没有分辨力时，判据全绿也说明不了任何事"的又一例。
    DXS = (('生产 dx = 62.5e-9 m（**非** 2 的幂）', 62.5e-9),
           ('dx = 2^-4（2 的幂，供对照）', 0.0625))
    A('=' * 96)
    A('R579-GRAD — goal §(6) `gradient(mode="sliced")` 判据 (N=%d nthreads=%d)'
      % (N, NT))
    A('=' * 96)
    ok = True
    for lbl, dx in DXS:
        A('')
        A('  ═══ dx：%s ═══' % lbl)
        ref = np.gradient(phi, dx, edge_order=2)
        rmax = max(float(np.max(np.abs(g))) for g in ref) or 1.0

        got1 = PAR.ParCtx(1).gradient(phi, dx, 2, mode='sliced')
        d1 = max(float(np.max(np.abs(a - b))) for a, b in zip(got1, ref)) / rmax
        A('    P1 单线程 sliced vs np.gradient：max|Δ|/max = **%.3e** ⇒ %s'
          % (d1, '✅ 逐位相同' if d1 == 0.0 else '❌ 不等价'))
        ok = ok and (d1 == 0.0)

        got4 = PAR.ParCtx(NT).gradient(phi, dx, 2, mode='sliced')
        d2 = max(float(np.max(np.abs(a - b))) for a, b in zip(got4, got1)) / rmax
        A('    P2 nthreads=%d vs 1：max|Δ|/max = **%.3e** ⇒ %s'
          % (NT, d2, '✅ 逐位相同' if d2 == 0.0 else '❌ 不等价'))
        ok = ok and (d2 == 0.0)
        gl = PAR.ParCtx(NT).gradient(phi, dx, 2, mode='legacy')
        d2b = max(float(np.max(np.abs(a - b))) for a, b in zip(gl, ref)) / rmax
        A('    P2b legacy(nthreads=%d) vs np.gradient：max|Δ|/max = **%.3e** ⇒ %s'
          % (NT, d2b, '✅' if d2b == 0.0 else '❌'))

        db = 0.0
        for a, b in zip(got1, ref):
            db = max(db, float(np.max(np.abs(a[0] - b[0]))),
                     float(np.max(np.abs(a[-1] - b[-1]))),
                     float(np.max(np.abs(a[:, 0] - b[:, 0]))),
                     float(np.max(np.abs(a[:, -1] - b[:, -1]))))
        A('    P3 首末两层单独核：max|Δ| = **%.3e** ⇒ %s'
          % (db, '✅ 边界也对' if db == 0.0 else '❌ 边界错'))
        ok = ok and (db == 0.0)

        naive = _naive_edge(phi, dx)
        dn = max(float(np.max(np.abs(a - b))) for a, b in zip(naive, ref)) / rmax
        A('    P4a 负对照（"先分子后除"）：max|Δ|/max = **%.3e** ⇒ %s'
          % (dn, '✅ 有分辨力（舍入路径确实不同）' if dn > 0
             else '⚠ **无分辨力**（该 dx 下两种分组恰好同位）——如实记账'))
        per = _periodic_edge(phi, dx)
        dp = max(float(np.max(np.abs(a - b))) for a, b in zip(per, ref)) / rmax
        A('    P4b 负对照（边界改周期）：max|Δ|/max = **%.3e** ⇒ %s'
          % (dp, '✅ 有分辨力' if dp > 1e-3 else '❌ 没分辨力'))
        # P4a 在**生产 dx** 上必须有效；在 2 的幂上已知无效（记账，不算失败）
        if dx == DXS[0][1]:
            ok = ok and (dn > 0)
        ok = ok and (dp > 1e-3)

    # ---- P5 微基准（用生产 dx）----
    dx = DXS[0][1]
    A('')
    A('  P5 微基准（nthreads=%d，dx=62.5e-9，交错配对 %d 轮）' % (NT, REPS))
    pc = PAR.ParCtx(NT)
    t_leg, t_sli, ratio = [], [], []
    for _ in range(REPS):
        t0 = time.perf_counter(); pc.gradient(phi, dx, 2, mode='legacy'); t1 = time.perf_counter()
        pc.gradient(phi, dx, 2, mode='sliced'); t2 = time.perf_counter()
        t_leg.append(t1 - t0); t_sli.append(t2 - t1); ratio.append((t1 - t0) / (t2 - t1))
    A('    legacy  min=%.4f ms  中位=%.4f ms'
      % (min(t_leg) * 1e3, statistics.median(t_leg) * 1e3))
    A('    sliced  min=%.4f ms  中位=%.4f ms'
      % (min(t_sli) * 1e3, statistics.median(t_sli) * 1e3))
    A('    交错配对 legacy/sliced 中位 = **%.3fx**  区间 [%.3f, %.3f]'
      % (statistics.median(ratio), min(ratio), max(ratio)))

    A('')
    A('  === RESULT: %s ===' % ('ALL PASS' if ok else 'FAIL'))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, OUT), 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
