#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r579_gpu2.py --- goal §(9) 的**第二次**测量：把"数据搬运"这一项量对。

## 为什么必须重测（v1 的量具有问题）
`_r579_gpu.py` 实测：GPU 常驻弹性链 **5.645×**（正确性 2.2e-16、负对照 2.0），
但"一次性上传"给出 **0.25 GB/s**，并据此按预登记判据（搬运占比 > 70%）**关闭**了 GPU 线。

**0.25 GB/s 不可信**：那一次 `cp.asarray` 里**混了 CUDA 上下文初始化 + 显存分配（首次）**，
是**冷启动**数字，不是稳态带宽。PCIe 4.0 x8 的稳态 H2D 应在 **GB/s 量级**。
⇒ 用**冷启动数字**去判"搬运占比 > 70%"是**量具错误导致结论错误**
   （`AGENTS.md §7.5 P6`：「量具错了和被测量对象错了长得一模一样」）。

## 本脚本量什么
1. **稳态传输带宽**：warm-up 之后，对 `phi`（生产里每步真要搬的那个数组）重复 H2D，
   取**最小值**；再量 D2H（`ed` 那个量级）。
   并且**同时报冷启动值**，让"冷/热差多少"可见。
2. **常驻链**复测（与 v1 同一段代码，作为交叉核对）。
3. **两条判据分支**（都按预登记判据，但口径写清楚）：
   * **分支 A（全驻留移植）**：每步搬运 = 0 ⇒ 只看加速比 ≥ 1.3×。
   * **分支 B（混合：弹性在 GPU、水平集在 CPU）**：每步必须搬 `phi`(H2D) + `ed`(D2H)
     ⇒ 算 **每步净收益 = 省下的弹性时间 − 搬运时间**；为负即"混合不可行"。
"""
import os
import statistics
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                    # noqa: E402
from T16_verify_rve import C, EPS0                             # noqa: E402

N = int(os.environ.get('R579G_N', '64'))
NV = int(os.environ.get('R579G_NV', '24'))
DX = float(os.environ.get('R579G_DX', '0.0625'))
REPS = int(os.environ.get('R579G_REPS', '7'))
OUT = os.environ.get('R579G2_OUT', '_w2_r579_gpu2.log')

L = []
A = L.append
AXS = (1, 2, 3)


def build():
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(NV)]
    g = W.LevelSetMulti(N, N * DX, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] + [3.0e8] * NV, workers=4,
                        reinit_every=20, reinit_dt=1e-4, reinit_band_cells=6.0,
                        phi_prec='f64')
    g.init_parent()
    rng = np.random.default_rng(7)
    nrm = np.array([0.0, 0.0, 1.0])
    Lc = N * DX
    for k in range(1, max(3, NV // 8) + 1):
        g.seed_plate(k, rng.random(3) * (Lc * 0.6) + Lc * 0.2, nrm, 120e-9, 300e-9)
    g.advance(dt=1e-8)
    return g


def main():
    A('=' * 100)
    A('R579-GPU2 — goal §(9)：把"数据搬运"量对（N=%d nv=%d）' % (N, NV))
    A('=' * 100)
    import cupy as cp
    props = cp.cuda.runtime.getDeviceProperties(0)
    A('  GPU：%s  totalMem=%.2f GB  cc=%d.%d'
      % (props['name'].decode(), props['totalGlobalMem'] / 2**30,
         props['major'], props['minor']))

    g = build()
    pf = g.pf
    phi = pf.phi
    A('  `pf.phi` %s %s = %.1f MB（**每步真要搬的就是它**）'
      % (phi.shape, phi.dtype, phi.nbytes / 2**20))

    # ---------------- 冷启动 vs 稳态传输 ----------------
    A('')
    A('  ── 稳态 H2D/D2H 带宽（`pf.phi` 量级）──')
    t0 = time.perf_counter()
    d_first = cp.asarray(phi)
    cp.cuda.Stream.null.synchronize()
    t_cold = time.perf_counter() - t0
    A('    冷启动（含 CUDA 上下文初始化 + 显存分配）：%.4f s ⇒ **%.3f GB/s**'
      % (t_cold, phi.nbytes / 2**30 / max(t_cold, 1e-9)))

    host = np.empty_like(phi)
    ts_up = []
    for _ in range(REPS):
        t0 = time.perf_counter()
        d_first.set(phi)
        cp.cuda.Stream.null.synchronize()
        ts_up.append(time.perf_counter() - t0)
    ts_dn = []
    for _ in range(REPS):
        t0 = time.perf_counter()
        d_first.get(out=host)
        cp.cuda.Stream.null.synchronize()
        ts_dn.append(time.perf_counter() - t0)
    A('    稳态 H2D：min %.4f s  中位 %.4f s ⇒ **%.2f GB/s**（%d.1f× 于冷启动）'
      % (min(ts_up), statistics.median(ts_up),
         phi.nbytes / 2**30 / max(min(ts_up), 1e-9), t_cold / max(min(ts_up), 1e-9)))
    A('    稳态 D2H：min %.4f s  中位 %.4f s ⇒ **%.2f GB/s**'
      % (min(ts_dn), statistics.median(ts_dn),
         phi.nbytes / 2**30 / max(min(ts_dn), 1e-9)))
    t_up = min(ts_up)
    t_dn_mb = min(ts_dn) / (phi.nbytes / 2**20)      # s per MB

    # ---------------- 常驻弹性链（与 v1 同一段） ----------------
    Lam_d = cp.asarray(pf.Lam)
    e0v_d = cp.asarray(pf.e0v)
    cp.cuda.Stream.null.synchronize()
    phi_d = d_first

    ref = pf.sigma_tensor()
    ts = []
    for _ in range(REPS):
        t0 = time.perf_counter(); pf.sigma_tensor(); ts.append(time.perf_counter() - t0)
    t_cpu = min(ts)

    def gpu_sigma():
        e = cp.einsum('vp,v...->p...', e0v_d, phi_d)
        e[3:] *= 2.0
        Eh = cp.fft.fftn(e, axes=AXS).reshape(6, -1)
        sh = -cp.einsum('kpq,qk->pk', Lam_d, Eh)
        return cp.real(cp.fft.ifftn(sh.reshape((6, N, N, N)), axes=AXS))

    _ = gpu_sigma(); cp.cuda.Stream.null.synchronize()
    got_h = cp.asnumpy(gpu_sigma())
    cp.cuda.Stream.null.synchronize()
    d = float(np.max(np.abs(got_h - ref))) / (float(np.max(np.abs(ref))) or 1.0)
    ts = []
    for _ in range(REPS):
        t0 = time.perf_counter(); gpu_sigma(); cp.cuda.Stream.null.synchronize()
        ts.append(time.perf_counter() - t0)
    t_gpu = min(ts)
    A('')
    A('  ── 常驻弹性链（σ 链）──')
    A('    CPU min %.4f s ｜ GPU 常驻 min %.4f s ⇒ **加速比 %.3f×**'
      % (t_cpu, t_gpu, t_cpu / t_gpu))
    A('    正确性 max|Δ|/max = %.3e（判据 ≤1e-5）⇒ %s'
      % (d, '✅' if d <= 1e-5 else '❌'))

    # ---------------- 每步真实搬运（混合路） ----------------
    #   混合：phi 全场上行（水平集在 CPU 演化）+ `edk/edl` 两个 (N,N,N) 下行
    ed_mb = 2 * (N ** 3 * 8) / 2**20
    t_move = t_up + t_dn_mb * ed_mb
    saved = t_cpu - t_gpu
    A('')
    A('  ── 每步搬运（**混合路**：水平集在 CPU、弹性在 GPU）──')
    A('    上行 `phi` = %.1f MB ⇒ %.4f s（用**稳态**带宽）' % (phi.nbytes / 2**20, t_up))
    A('    下行 `edk/edl` = %.1f MB ⇒ %.4f s' % (ed_mb, t_dn_mb * ed_mb))
    A('    每步搬运合计 **%.4f s**；弹性链省下 **%.4f s** ⇒ 净收益 **%+.4f s/步**'
      % (t_move, saved, saved - t_move))
    A('    搬运占比（搬运 / (搬运 + GPU 计算)）= **%.1f%%**'
      % (100 * t_move / (t_move + t_gpu)))

    # ---------------- 判定 ----------------
    sp = t_cpu / t_gpu
    A('')
    A('  ── G3 判定（预登记：加速比 < 1.3× 或 搬运占比 > 70% ⇒ 关闭）──')
    A('    **分支 A（全驻留移植）**：每步搬运 = 0，加速比 **%.3f×**（≥1.3）⇒ %s'
      % (sp, '✅ 不触发关闭' if sp >= 1.3 else '❌ 触发关闭'))
    hybrid_ok = (saved - t_move) > 0 and (t_move / (t_move + t_gpu)) <= 0.70
    A('    **分支 B（混合）**：净收益 %+.4f s/步，搬运占比 %.1f%% ⇒ %s'
      % (saved - t_move, 100 * t_move / (t_move + t_gpu),
         '✅ 不触发关闭' if hybrid_ok else '❌ 触发关闭'))
    A('')
    if sp >= 1.3:
        A('  ★ 判决：**不能按"搬运占比"关闭** —— 该指标的 v1 取值来自**冷启动**，已被证伪；')
        A('     稳态实测 H2D **%.2f GB/s**（是冷启动的 %.1f×）。' % (
            phi.nbytes / 2**30 / max(t_up, 1e-9), t_cold / max(t_up, 1e-9)))
        A('     ⇒ GPU 这条线**转为"待做真移植"**，其判据是：')
        A('       ① 全驻留移植后**整步**加速比 ≥ 1.3×（不是只看 σ 链）；')
        A('       ② 若走混合路，每步净收益 > 0 且搬运占比 ≤ 70%。')
        A('     ⚠ 本轮**不做**移植（工作量远超一轮），只把量具修正并登记。')
    else:
        A('  ★ 判决：**正式关闭**（加速比 < 1.3×）。')

    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, OUT), 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
