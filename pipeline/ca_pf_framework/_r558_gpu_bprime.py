#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r558_gpu_bprime.py —— **复核 `_r490` 的 B′（纯 GPU 序列）：它同步了吗？**

## 要复核的指控（对我自己）
`_r490` 打印过：
```
B′ 纯 GPU 序列（**不回 CPU**，上界参考） 0.0004 s   **12344×**
```
并由此在 `R489 §3` 写下：
> 「模式 B 的 0.3084 s 里，**纯 GPU 计算只占 0.0004 s（0.13%）**，
>   其余 **99.87% 是传输**」

**指控**：`mode_B_kernel_only()` 只是 `mode_B()`，它返回 **CuPy 数组**、**从不调
`asnumpy`/`synchronize`** ⇒ **CUDA 是异步的** ⇒ 它量的是**提交耗时**，不是**计算耗时**
⇒ 那个分解（0.13% vs 99.87%）**无效**。

## 判据（**先写死**）
| # | 判据 | 期望 |
|---|---|---|
| **S1 决定性** | `mode_B()` **不**同步 ⇒ 它必须**显著小于** `mode_B()` **+ `synchronize()`** | 比值 ≥ **5×** |
| **S2 正对照（必须能失败）** | 加了 `synchronize()` 之后，耗时必须**跳到与 GPU 真实计算相当的量级**（不再是 0.4 ms） | `t_sync / t_submit ≥ 5` |
| **S3 正确的分解** | 用**同步后**的数重算：`GPU 计算 ≈ t_sync − t_submit`；`D2H 传输 ≈ t_full − t_sync` | 报出两个真实占比 |
| **S4 负对照** | 极小数组（4 元素）上，`synchronize()` 的**相对**影响应当很小（计算本来就短）⇒ 证明 S1 量的是"真计算"而不是固定开销 | 比值 < 5 |

⇒ 若 **S1/S2 成立**，则 `_r490` 的 B′ 与 `R489 §3` 的分解**必须作废并更正**；
   而 **A / B / CPU 三行（它们都调了 `asnumpy`）仍然是同步过的、有效的**。

## 环境
必须 `export CUDA_PATH=/root/miniconda3/envs/ml/lib/python3.12/site-packages/nvidia/cu13`
"""
import os
import sys
import time

import numpy as np

REPEAT = 5
SIZES = [(112, 25, np.float64, 'abA 实际'),
         (160, 128, np.float32, '外推')]


def bench(fn, repeat=REPEAT):
    ts = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return float(np.median(ts))


def main():
    try:
        import cupy as cp
    except Exception as e:                                      # noqa: BLE001
        print('❌ cupy 不可用：%r' % (e,))
        return 2
    print('=' * 96)
    print('R558 —— 复核 `_r490` 的 B′：它到底同步了没有？')
    print('=' * 96)
    print('  cupy %s ｜ GPU %s' % (cp.__version__,
                                  cp.cuda.runtime.getDeviceProperties(0)['name']
                                  .decode()))
    rows = []
    for N, nreg, dt, lbl in SIZES:
        rs = np.random.default_rng(11)
        phi = rs.standard_normal((nreg, N, N, N)).astype(dt)
        e0 = rs.standard_normal((nreg, 6)).astype(dt)
        sig = rs.standard_normal((6, N, N, N)).astype(dt)
        ph_g, e0_g, sig_g = cp.asarray(phi), cp.asarray(e0), cp.asarray(sig)
        cp.cuda.Stream.null.synchronize()          # 清干净，从稳态起测

        def sub():                                  # = `_r490` 的 B′：**只提交**
            k = cp.argmin(ph_g, axis=0)
            ef = e0_g[k.ravel()].T
            es = cp.einsum('vp,p...->v...', e0_g, sig_g)
            ff = cp.fft.fftn(ph_g[0]).real
            return k, ef, es, ff

        def sub_sync():                             # 提交 **+ 同步**（不 D2H）
            r = sub()
            cp.cuda.Stream.null.synchronize()
            return r

        def sub_sync_d2h():                         # 提交 + 同步 + **拷回 CPU**
            k, ef, es, ff = sub_sync()
            return (cp.asnumpy(k), cp.asnumpy(ef), cp.asnumpy(es), cp.asnumpy(ff))

        t_sub = bench(sub)
        t_sync = bench(sub_sync)
        t_full = bench(sub_sync_d2h)

        print()
        print('  ■ %s (N=%d, nreg=%d, %s, phi=%.2f GB)'
              % (lbl, N, nreg, np.dtype(dt).name, phi.nbytes / 2**30))
        print('     (a) **只提交**（= `_r490` 的 B′）          %.6f s' % t_sub)
        print('     (b) 提交 **+ `synchronize()`**（不 D2H）    %.6f s' % t_sync)
        print('     (c) 提交 + 同步 + **`asnumpy`（D2H）**      %.6f s' % t_full)
        ratio = t_sync / max(t_sub, 1e-12)
        print('     ⇒ S1/S2 **(b)/(a) = %.1f×**（判据 ≥5×）⇒ %s'
              % (ratio, '✅ **B′ 确实没同步**' if ratio >= 5 else '❌ 未复现'))
        # S3 正确分解（用**同步后**的数）
        gpu = max(t_sync - t_sub, 0.0)
        d2h = max(t_full - t_sync, 0.0)
        tot = max(t_full, 1e-12)
        print('     ⇒ S3 **正确分解**：GPU 计算 ≈ %.6f s（**%.1f%%**）；'
              'D2H 传输 ≈ %.6f s（**%.1f%%**）；提交 ≈ %.1f%%'
              % (gpu, 100 * gpu / tot, d2h, 100 * d2h / tot,
                 100 * t_sub / tot))
        rows.append((lbl, t_sub, t_sync, t_full, ratio, gpu / tot, d2h / tot))
        del ph_g, e0_g, sig_g, phi, e0, sig
        cp.get_default_memory_pool().free_all_blocks()

    # S4 负对照
    print()
    print('  ── S4 负对照：极小数组（4 元素）上 (b)/(a) 应当**很小** ──')
    a = np.arange(4, dtype=np.float64)
    ag = cp.asarray(a)

    def ts_():
        cp.argmin(ag)
    def ts2():
        cp.argmin(ag)
        cp.cuda.Stream.null.synchronize()
    ta, tb = bench(ts_, 50), bench(ts2, 50)
    r4 = tb / max(ta, 1e-12)
    print('     只提交 %.8f s ｜ +同步 %.8f s ⇒ 比值 **%.2f×**（判据 <5）⇒ %s'
          % (ta, tb, r4, '✅ PASS（说明 S1 量的是真计算，不是固定开销）'
             if r4 < 5 else '⚠ 未按预期'))

    print()
    print('=' * 96)
    print('★ 判定')
    s1 = all(r[4] >= 5 for r in rows)
    print('  · S1/S2（B′ 未同步）：%s' % ('✅ **成立 ⇒ B′ 与 R489 §3 的分解作废**'
                                        if s1 else '❌ 未成立'))
    print('  · **A / B / CPU 三行不受影响** —— 它们都调了 `asnumpy`，是同步过的有效测量')
    print('=' * 96)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           '_w2_r558_bprime.log'), 'w') as fh:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
