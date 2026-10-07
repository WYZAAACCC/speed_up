#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r579_gpu.py --- goal §(9)：GPU 这条线的**正式处置**。

## 预登记的硬判据（写死在 goal 里，不许事后改）
> 要么把**状态驻留**路径做成真移植并实测，要么按硬判据正式关闭：
> **实测加速比 < 1.3×** 或 **数据搬运占比 > 70%** 即关闭。

## 本脚本量什么（与历史上那条"合成上界"的区别）
历史结论里有一个 **1.493×/1.578× 的"状态驻留上界"**，但那是**合成**的
（用算子级计时拼出来的，不是移植后的 `advance()`）。`B'` 那条 1200× 则是**异步计时错误**。

本脚本走"**真·状态驻留**"的最小可判路径：
  1. 在 CPU 上把引擎建好（N=64/nv=24，与记账剖面同一构型）；
  2. 把**常驻状态**（`phi`、`Lam`、`e0v`）整体上一次性地搬到 GPU —— 并且**之后不再搬**；
  3. 在 GPU 上跑**弹性链**（`eps0_fields` → 工程应变 ×2 → `rfftn` → `Λ` 缩并 → `irfftn`），
     全程 `cupy`，**每步零 host↔device 传输**；
  4. 与 CPU 上**同一条链**（`sigma_tensor`）的墙钟比。
  5. 另外单独量"**一次性上传**整个状态"的耗时与字节 ⇒ 就是"数据搬运"这一项。

## 判据（先写死，必须能失败）
* **G1** 正确性：GPU 链的输出与 CPU 的 `sigma_tensor()` 必须一致到
  `max|Δ|/max|ref| ≤ 1e-5`（float32 GPU 运算 + 不同 FFT 实现 ⇒ 不要求逐位）。
* **G2** 分辨力负对照：故意把 `Lam` 的符号翻掉，G1 必须 **FAIL**。
* **G3** 结论：按预登记判据给出 **开启 / 关闭**；两个条件**任一**命中即关闭：
  加速比 < 1.3×，或 数据搬运占比 > 70%。
"""
import os
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
REPS = int(os.environ.get('R579G_REPS', '5'))
OUT = os.environ.get('R579G_OUT', '_w2_r579_gpu.log')

L = []
A = L.append


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
    A('R579-GPU — goal §(9) 正式处置：(N=%d nv=%d) 的**状态驻留**弹性链 vs CPU' % (N, NV))
    A('=' * 100)
    A('  宿主：python %s  numpy %s' % (sys.version.split()[0], np.__version__))

    try:
        import cupy as cp
    except Exception as e:                                     # noqa: BLE001
        A('  ❌ 无法导入 cupy（%r）⇒ 按预登记判据**正式关闭** GPU 这条线' % (e,))
        _emit(out_verdict='CLOSED(no-cupy)')
        return 0

    try:
        dev = cp.cuda.Device(0)
        props = cp.cuda.runtime.getDeviceProperties(0)
        A('  GPU：%s  totalMem=%.2f GB  cc=%d.%d'
          % (props['name'].decode(), props['totalGlobalMem'] / 2**30,
             props['major'], props['minor']))
    except Exception as e:                                     # noqa: BLE001
        A('  ❌ 无法访问 CUDA 设备（%r）⇒ 正式关闭' % (e,))
        _emit(out_verdict='CLOSED(no-device)')
        return 0

    g = build()
    pf = g.pf
    A('  CPU 引擎已建好：pf.phi %s %s' % (pf.phi.shape, pf.phi.dtype))

    # ---------------- CPU 参照 ----------------
    ref = pf.sigma_tensor()
    ts = []
    for _ in range(REPS):
        t0 = time.perf_counter()
        pf.sigma_tensor()
        ts.append(time.perf_counter() - t0)
    t_cpu = min(ts)
    A('')
    A('  ── CPU（c2c）σ 链：min %.4f s（%d 次）' % (t_cpu, REPS))

    # ---------------- 一次性上传（"数据搬运"这一项） ----------------
    t0 = time.perf_counter()
    phi_d = cp.asarray(pf.phi)
    Lam_d = cp.asarray(pf.Lam)
    e0v_d = cp.asarray(pf.e0v)
    cp.cuda.Stream.null.synchronize()
    t_h2d = time.perf_counter() - t0
    bytes_up = pf.phi.nbytes + pf.Lam.nbytes + pf.e0v.nbytes
    A('  一次性上传状态：%.4f s（%.1f MB ⇒ %.2f GB/s）'
      % (t_h2d, bytes_up / 2**20, bytes_up / 2**30 / max(t_h2d, 1e-9)))

    # ---------------- GPU 常驻链 ----------------
    axs = (1, 2, 3)
    half = N // 2 + 1
    # 半谱 Λ（与 CPU rfft 路同一张表）—— 直接用 c2c 的 Λ，GPU 上走 c2c FFT
    def gpu_sigma():
        e = cp.einsum('vp,v...->p...', e0v_d, phi_d)
        e[3:] *= 2.0
        Eh = cp.fft.fftn(e, axes=axs).reshape(6, -1)
        sh = -cp.einsum('kpq,qk->pk', Lam_d, Eh)
        sh = sh.reshape((6, N, N, N))
        return cp.real(cp.fft.ifftn(sh, axes=axs))

    got = gpu_sigma()
    cp.cuda.Stream.null.synchronize()
    got_h = cp.asnumpy(got)
    rmax = float(np.max(np.abs(ref))) or 1.0
    d = float(np.max(np.abs(got_h - ref))) / rmax
    g1 = d <= 1e-5
    A('')
    A('  ── GPU 常驻链 ──')
    A('    G1 正确性：max|Δ|/max|ref| = **%.3e**（判据 ≤1e-5）⇒ %s'
      % (d, '✅ PASS' if g1 else '❌ FAIL'))

    # G2 负对照
    Lam_bad = cp.asarray(-pf.Lam)
    _save = Lam_d
    Lam_d = Lam_bad
    got_bad = cp.asnumpy(gpu_sigma())
    cp.cuda.Stream.null.synchronize()
    dBad = float(np.max(np.abs(got_bad - ref))) / rmax
    Lam_d = _save
    A('    G2 负对照（把 Λ 取负）：max|Δ|/max|ref| = **%.3e** ⇒ %s'
      % (dBad, '✅ 量具有分辨力' if dBad > 1e-5 else '❌ 量具没有分辨力'))

    ts = []
    for _ in range(REPS):
        t0 = time.perf_counter()
        gpu_sigma()
        cp.cuda.Stream.null.synchronize()      # ★ 必须**同步**再停表（历史 1200× 的错就是漏了它）
        ts.append(time.perf_counter() - t0)
    t_gpu = min(ts)
    A('    GPU 常驻链：min %.4f s（%d 次，**含同步**）' % (t_gpu, REPS))

    # ---------------- 判定 ----------------
    sp = t_cpu / max(t_gpu, 1e-12)
    # "数据搬运占比"：状态驻留时每步传输 = 0；但把**一次性上传**摊到"相当于多少步"上更有意义
    #   ⇒ 定义：搬迁占比 = t_h2d / (t_h2d + t_gpu)（**单步**口径：若每步都搬全状态会怎样）
    move_frac = t_h2d / (t_h2d + max(t_gpu, 1e-12))
    A('')
    A('  ── G3 判定（预登记：加速比 < 1.3× 或 搬运占比 > 70% ⇒ 关闭）──')
    A('    弹性链加速比 CPU/GPU = **%.3fx**' % sp)
    A('    数据搬运占比（若每步都搬全状态）= **%.1f%%**' % (100 * move_frac))
    close = (sp < 1.3) or (move_frac > 0.70)
    A('    ⇒ **%s**' % ('❌ 正式关闭 GPU 这条线' if close else '✅ 允许继续（需做完整 advance 移植）'))
    if not g1:
        A('    ⚠ 但 G1 未过 ⇒ 上面的加速比**无意义**，结论应取"关闭"（正确性优先）')
        close = True
    _emit(out_verdict='CLOSED(criterion)' if close else 'OPEN',
          extra=dict(t_cpu=t_cpu, t_gpu=t_gpu, t_h2d=t_h2d, speedup=sp,
                     move_frac=move_frac, g1_diff=d, g2_diff=dBad))
    return 0


def _emit(out_verdict, extra=None):
    A('')
    A('  ★ GPU 判决：**%s**' % out_verdict)
    if extra:
        A('    %r' % (extra,))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, OUT), 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')


if __name__ == '__main__':
    sys.exit(main())
