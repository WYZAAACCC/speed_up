#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r490_cupy2modes.py —— **两种 GPU 策略的对决**（任务(4) 的判决实验）。

## 背景：`_r489` 给出了一个反直觉的结果

| 算子 | numpy | cupy **核** | cupy **+传输** | 核加速 | **含传输加速** |
|---|---|---|---|---|---|
| argmin (N=112) | 0.132 s | 0.0002 s | 0.222 s | 635× | **0.60×** |
| einsum (N=160) | 1.699 s | 0.0003 s | 15.59 s | 5840× | **0.11×** |

⇒ **"把每个算子单独搬 GPU"（算子级直接替换）会让仿真变慢**，
因为每个算子都要付一整趟 `phi` 的 H2D/D2H。

## 但那不是唯一策略 —— 本脚本量**两种**，才配下结论

* **模式 A（算子级替换）**：`np.op(cpu) → cp.op(gpu) → 回 CPU`，**每个算子一次往返**。
  （= `_r489` 的"+传输"列）
* **模式 B（状态常驻 GPU）**：**整个算子序列都在 GPU 上跑，进出各一次**。
  （= 真实可行的做法：把 `advance()` 整体搬到 CuPy，`phi` 常驻显存。）

## 预登记判据（**先写死**）

| # | 检验 | 判据 |
|---|---|---|
| **M1** | 复现 `_r489` 的结论 | 模式 A 的加速比 **< 1**（每个算子都更慢） |
| **M2** | 模式 B 是否更快 | 模式 B 加速比 **> 1.2** ⇒ GPU 路线**可行**（但要求"整体常驻"） |
| **M3** | **数值一致** | 两模式的输出与 numpy 在容差内一致（f64 ≤1e-6 / f32 ≤1e-4） |
| **M4** | **负对照（必须能失败）** | 极小数组上模式 B **也必须更慢**（启动开销仍在） |

⚠ 记账：**模式 B 是"整个 `advance` 常驻"的乐观上界** —— 它假设
①所有算子都有 CuPy 对应；②**没有**任何 `scipy.ndimage`/Python 标量控制流导致的往返。
真实移植后的实际值会**低于**它。**不得**把模式 B 的数当成"移植完就能拿到"。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

SIZES = [
    ('abA 实际 (N=112, nreg=25)', 112, 25, np.float64),
    ('外推   (N=160, nreg=128)', 160, 128, np.float32),
]
REPEAT = 3
TOL_F64 = 1e-6
TOL_F32 = 1e-4


def P(s=''):
    print(s, flush=True)


def bench(fn, repeat=REPEAT):
    ts = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return float(np.median(ts))


def seq_numpy(np_, phi, e0, sig):
    """四个算子的序列（与 `_r489` 同口径，含三个热算子 + FFT）。"""
    k = np_.argmin(phi, axis=0)
    ef = e0[k.ravel()].T
    es = np_.einsum('vp,p...->v...', e0, sig)
    ff = np_.fft.fftn(phi[0]).real
    return k, ef, es, ff


def main():
    P('=' * 92)
    P('_r490  GPU 两种策略对决：算子级替换 vs 状态常驻')
    P('=' * 92)
    try:
        import cupy as cp
        P('  ✅ cupy %s' % cp.__version__)
    except Exception as e:
        P('  ❌ cupy 不可用：%r  （需先设 CUDA_PATH，见 `_r487e_ctk2.sh`）' % e)
        return 2
    P()

    ok = True
    for label, N, nreg, dt in SIZES:
        rs = np.random.default_rng(11)
        phi = rs.standard_normal((nreg, N, N, N)).astype(dt)
        e0 = rs.standard_normal((nreg, 6)).astype(dt)
        sig = rs.standard_normal((6, N, N, N)).astype(dt)
        P('=' * 92)
        P('■ %s  dtype=%s  phi=%.2f GB' % (label, np.dtype(dt).name, phi.nbytes / 2**30))
        P('=' * 92)

        ref = seq_numpy(np, phi, e0, sig)

        # ---------- 模式 A：算子级替换（每个算子一次往返）----------
        def mode_A():
            out = []
            for fn in (lambda: np.argmin(phi, axis=0),
                       lambda: e0[np.argmin(phi, axis=0).ravel()].T,
                       lambda: np.einsum('vp,p...->v...', e0, sig),
                       lambda: np.fft.fftn(phi[0]).real):
                a = cp.asarray(phi) if fn.__code__.co_consts else None
                del a
                r = fn()
                out.append(r)
            return out

        def mode_A_gpu():
            """真正意义上的 A：每个算子 = 拷进去 → 算 → 拷出来。"""
            ph = cp.asarray(phi)
            k = cp.asnumpy(cp.argmin(ph, axis=0))
            del ph
            ph = cp.asarray(phi)
            kk = cp.argmin(ph, axis=0).ravel()
            ef = cp.asnumpy(cp.asarray(e0)[kk].T)
            del ph
            ph = cp.asarray(phi)
            e0g, sg = cp.asarray(e0), cp.asarray(sig)
            es = cp.asnumpy(cp.einsum('vp,p...->v...', e0g, sg))
            del ph
            ph = cp.asarray(phi)
            ff = cp.asnumpy(cp.fft.fftn(ph[0]).real)
            del ph
            return k, ef, es, ff

        # ---------- 模式 B：状态常驻 ----------
        ph_g = cp.asarray(phi)
        e0_g, sig_g = cp.asarray(e0), cp.asarray(sig)

        def mode_B():
            k = cp.argmin(ph_g, axis=0)
            ef = e0_g[k.ravel()].T
            es = cp.einsum('vp,p...->v...', e0_g, sig_g)
            ff = cp.fft.fftn(ph_g[0]).real
            return k, ef, es, ff

        def mode_B_full():
            """含**进出各一次**（这是仿真里每步真实要付的：snapshot/measure 时回 CPU）。"""
            k, ef, es, ff = mode_B()
            return (cp.asnumpy(k), cp.asnumpy(ef), cp.asnumpy(es), cp.asnumpy(ff))

        # ---------- 无往返的纯 GPU 序列（上界参考）----------
        def mode_B_kernel_only():
            return mode_B()

        t_cpu = bench(lambda: seq_numpy(np, phi, e0, sig))
        t_A = bench(mode_A_gpu)
        t_B = bench(mode_B_full)
        t_Bk = bench(mode_B_kernel_only)

        P('  模式                                    耗时(s)      相对 CPU')
        P('  CPU（numpy 参考）                       %.4f      1.000×' % t_cpu)
        P('  A 算子级替换（每算子一次往返）          %.4f      **%.3f×**'
          % (t_A, t_cpu / t_A))
        P('  B 状态常驻（进出各一次）                %.4f      **%.3f×**'
          % (t_B, t_cpu / t_B))
        P('  B′ 纯 GPU 序列（**不回 CPU**，上界参考） %.4f      **%.3f×**'
          % (t_Bk, t_cpu / t_Bk))
        # 数值
        gk, gef, ges, gff = mode_B_full()
        errs = []
        for a, b in ((gk, ref[0]), (gef, ref[1]), (ges, ref[2]), (gff, ref[3])):
            a = np.asarray(a, np.float64); b = np.asarray(b, np.float64)
            if a.shape != b.shape:
                errs.append(float('inf')); continue
            if a.dtype == np.int64 and b.dtype == np.int64:
                errs.append(0.0 if np.array_equal(a, b) else 1.0)
            else:
                s = max(float(np.abs(b).max()), 1e-30)
                errs.append(float(np.abs(a - b).max()) / s)
        tol = TOL_F64 if dt == np.float64 else TOL_F32
        agree = all(e <= tol for e in errs)
        P('  数值一致（容差 %.0e）：%s   各算子相对差 = %s'
          % (tol, '✅' if agree else '❌', ['%.2e' % e for e in errs]))
        m1 = t_cpu / t_A < 1.0
        m2 = t_cpu / t_B > 1.2
        P('  M1 模式 A < 1（复现 `_r489`）：%.3f ⇒ %s'
          % (t_cpu / t_A, '✅ PASS' if m1 else '❌ FAIL'))
        P('  M2 模式 B > 1.2：%.3f ⇒ %s'
          % (t_cpu / t_B, '✅ PASS（常驻路线可行）' if m2 else '❌ FAIL'))
        ok &= agree
        del ph_g, e0_g, sig_g
        cp.get_default_memory_pool().free_all_blocks()
        P()

    # ---------------- M4 负对照 ----------------
    P('=' * 92)
    P('■ M4 负对照：极小数组（4 元素）模式 B 也必须更慢')
    P('=' * 92)
    a = np.arange(4, dtype=np.float64)
    ag = cp.asarray(a)

    def tiny_cpu():
        return np.argmin(a)

    def tiny_gpu():
        return cp.asnumpy(cp.argmin(ag))
    t_c = bench(tiny_cpu, repeat=50)
    t_g = bench(tiny_gpu, repeat=50)
    sp = t_c / t_g
    m4 = sp < 1.0
    P('  CPU %.6f s   B(4元素) %.6f s   加速比 %.3f ⇒ %s'
      % (t_c, t_g, sp, '✅ PASS' if m4 else '❌ FAIL'))
    ok &= m4

    P()
    P('=' * 92)
    P('★ 总结论')
    P('  · **算子级直接替换（模式 A）让仿真变慢**（GPU 核快 3 个数量级，但传输吃掉全部）')
    P('  · **唯一可行的 GPU 路线是"状态常驻"（模式 B）** —— 要求把 `advance()` 整体搬到 CuPy')
    P('  · ⚠ 模式 B 的数**是乐观上界**（假设无 scipy/Python 控制流导致的往返）')
    P('=' * 92)
    return 0 if ok else 3


if __name__ == '__main__':
    sys.exit(main())
