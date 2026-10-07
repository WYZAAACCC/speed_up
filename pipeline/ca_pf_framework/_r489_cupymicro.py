#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r489_cupymicro.py —— **CuPy vs numpy 微基准**（任务(4) 的核心取证）。

## 为什么按"算子"量，而不是"整步"

用户已给的 profile（每步 6.30 s）：**`argmin` 18.4% / `eps0_fields` 17.0% /
`einsum` 10.9% / 其他 numpy ~25% / `scipy.fft` 只 2.4%**
⇒ **瓶颈在稠密数组运算，不在 FFT**。所以本基准就量这几个算子。

## ★ 诚实口径（这一条决定读数的意义）

GPU 的**数据传输**（H2D/D2H）常常吃掉全部收益。用户要的是"**确实能加快仿真**"，
所以本基准对每个算子报**两个数**：
* `kernel`：只算 GPU 上的运算；
* **`+transfer`：把输入拷进去、结果拷出来**（**这才是仿真里实际要付的**）。
**只报前者就是自欺。**

## 预登记判据（**先写死，且必须能失败**）

| # | 检验 | 判据 |
|---|---|---|
| **G1** | 各算子给出 `kernel` 与 `+transfer` 两个加速比 | 报数，**不预设谁赢** |
| **G2** | **数值一致** | 同 dtype 下 `max\|cupy − numpy\| / scale ≤ 1e-6`（f64）/ `≤1e-4`（f32） |
| **G3** | ★ **负对照（必须能失败）** | **极小数组**（4 元素）上 cupy **必须更慢**（`加速比 < 1`）⇒ 否则说明基准没在量真实开销 |
| **G4** | **尺寸口径** | 至少覆盖 **abA 实际尺寸**（N=112, nreg=25）与一个**外推尺寸**（N=160, nreg=128） |

⚠ 显存只有 **8 GB**（实测空闲 ~6.9 GB）⇒ 大尺寸必须用 **f32**，且要报显存占用。
"""
from __future__ import annotations

import sys
import time

import numpy as np

NPS = np

SIZES = [
    ('abA 实际 (N=112, nreg=25)', 112, 25, np.float64),
    ('外推   (N=160, nreg=128)', 160, 128, np.float32),
]
TINY = 4
TOL_G2_F64 = 1e-6
TOL_G2_F32 = 1e-4
REPEAT = 3


def P(s=''):
    print(s, flush=True)


def bench(fn, repeat=REPEAT):
    ts = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return float(np.median(ts))


def main():
    P('=' * 92)
    P('_r489  CuPy vs numpy 微基准（按算子，含**数据传输**）')
    P('=' * 92)
    try:
        import cupy as cp
        P('  ✅ cupy %s' % cp.__version__)
        free, total = cp.cuda.Device(0).mem_info
        P('  显存 空闲 %.2f / 共 %.2f GB' % (free / 2**30, total / 2**30))
    except Exception as e:
        P('  ❌ cupy 不可用：%r' % e)
        P('  ⇒ 本基准无法进行；任务(4) 的结论只能是"CuPy 路径未能实测"。')
        return 2
    P()

    ok_all = True
    rows = []

    for label, N, nreg, dt in SIZES:
        rs = np.random.default_rng(11)
        # ---------- 造数据（CPU）----------
        phi_np = rs.standard_normal((nreg, N, N, N)).astype(dt)
        e0_np = rs.standard_normal((nreg, 6)).astype(dt)
        sig_np = rs.standard_normal((6, N, N, N)).astype(dt)
        mem_gb = phi_np.nbytes / 2**30
        P('=' * 92)
        P('■ %s   dtype=%s   phi 占 %.2f GB' % (label, np.dtype(dt).name, mem_gb))
        P('=' * 92)

        # ---------- 各算子的 numpy 参考 ----------
        def np_argmin():
            return np.argmin(phi_np, axis=0)

        def np_eps0fields():
            # `eps0_fields()` 的实质：按 winner 索引把 (nreg,6) 展开成 (6,N³)
            k = np.argmin(phi_np, axis=0).ravel()
            return e0_np[k].T.copy()

        def np_einsum():
            return np.einsum('vp,p...->v...', e0_np, sig_np)

        def np_fft():
            return np.fft.fftn(phi_np[0]).real

        ref = {'argmin': np_argmin(), 'eps0_fields': np_eps0fields(),
               'einsum': np_einsum(), 'fft': np_fft()}

        # ---------- GPU ----------
        phi_g = cp.asarray(phi_np)
        e0_g = cp.asarray(e0_np)
        sig_g = cp.asarray(sig_np)

        def g_argmin():
            return cp.argmin(phi_g, axis=0)

        def g_eps0fields():
            k = cp.argmin(phi_g, axis=0).ravel()
            return e0_g[k].T.copy()

        def g_einsum():
            return cp.einsum('vp,p...->v...', e0_g, sig_g)

        def g_fft():
            return cp.fft.fftn(phi_g[0]).real

        cases = [('argmin', np_argmin, g_argmin, ref['argmin']),
                 ('eps0_fields', np_eps0fields, g_eps0fields, ref['eps0_fields']),
                 ('einsum', np_einsum, g_einsum, ref['einsum']),
                 ('fft', np_fft, g_fft, ref['fft'])]

        P('  %-13s %-11s %-11s %-11s %-11s %s'
          % ('算子', 'numpy(s)', 'cupy核(s)', 'cupy+传输', '核加速比', '+传输加速比'))
        for nm, fn_np, fn_g, r0 in cases:
            t_np = bench(fn_np)
            t_k = bench(fn_g)

            def with_transfer():
                a = cp.asarray(phi_np)
                b = fn_g()
                return cp.asnumpy(b)
            t_t = bench(with_transfer)

            # G2 数值一致
            try:
                got = cp.asnumpy(fn_g()).astype(np.float64)
                exp = np.asarray(r0, np.float64)
                if nm == 'argmin':
                    agree = bool(np.array_equal(got.astype(np.int64),
                                                exp.astype(np.int64)))
                    err = 0.0 if agree else 1.0
                else:
                    scale = max(float(np.abs(exp).max()), 1e-30)
                    err = float(np.abs(got - exp).max()) / scale
                    agree = err <= (TOL_G2_F64 if dt == np.float64 else TOL_G2_F32)
            except Exception as e:
                agree, err = False, float('nan')
                P('     ⚠ %s 核对失败：%r' % (nm, e))
            P('  %-13s %-11.4f %-11.4f %-11.4f %-11.3f %-11.3f  %s'
              % (nm, t_np, t_k, t_t, t_np / t_k if t_k else float('nan'),
                 t_np / t_t if t_t else float('nan'),
                 '✅一致' if agree else '❌不一致(err=%.2e)' % err))
            ok_all &= bool(agree)
            rows.append((label, nm, t_np, t_k, t_t, agree))

        del phi_g, e0_g, sig_g
        cp.get_default_memory_pool().free_all_blocks()
        P()

    # ---------------- G3 负对照：极小数组 ----------------
    P('=' * 92)
    P('■ G3 负对照：极小数组（%d 元素）—— cupy **必须更慢**' % TINY)
    P('=' * 92)
    a_np = np.arange(TINY, dtype=np.float64)
    a_g = cp.asarray(a_np)
    t_np = bench(lambda: np.argmin(a_np), repeat=20)
    t_g = bench(lambda: cp.argmin(a_g), repeat=20)
    sp = t_np / t_g if t_g else float('nan')
    g3 = sp < 1.0
    P('  numpy %.6f s   cupy %.6f s   ⇒ 加速比 **%.3f**' % (t_np, t_g, sp))
    P('  ⇒ 判据（必须 < 1，即 cupy 更慢）⇒ **%s**'
      % ('✅ PASS（基准确实量到了开销）' if g3
         else '❌ FAIL（连 4 元素都"更快" ⇒ 基准在骗人）'))
    ok_all &= g3

    # ---------------- 汇总 ----------------
    P()
    P('=' * 92)
    P('★ 汇总')
    win_k = [r for r in rows if r[3] and r[2] / r[3] > 1.2]
    win_t = [r for r in rows if r[4] and r[2] / r[4] > 1.2]
    P('  算子-尺寸 组合数 = %d' % len(rows))
    P('  **核层面**加速 > 1.2× 的：%d 个' % len(win_k))
    for r in win_k:
        P('     %-30s %-13s 核 %.2f×   含传输 %.2f×'
          % (r[0], r[1], r[2] / r[3], r[2] / r[4]))
    P('  **含传输**加速 > 1.2× 的：%d 个' % len(win_t))
    for r in win_t:
        P('     %-30s %-13s 核 %.2f×   含传输 %.2f×'
          % (r[0], r[1], r[2] / r[3], r[2] / r[4]))
    P()
    P('  ⇒ **判读**：只有当"含传输"也 > 1.2× 时，**整步**才可能真的变快；')
    P('     核快而含传输不快 ⇒ 该算子**不能**搬 GPU（传输吃掉全部收益）。')
    P('  全体数值一致 = %s' % ('✅' if ok_all else '❌'))
    P('=' * 92)
    return 0


if __name__ == '__main__':
    sys.exit(main())
