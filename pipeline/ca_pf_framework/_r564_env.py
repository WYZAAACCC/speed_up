#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r564_env.py --- **在哪台机器/哪个解释器上量**，这本身是一个必须钉住的量具前提。

## 为什么必须查
`_r559` 归档：N=64/nv=24 干净单步 = **0.3768 s**，`eps0_fields` = 0.048 s/次。
`_r561`(Windows Anaconda python3.13) 与 `_r562` 两次独立测得：
单步 **1.32 s**、`eps0_fields` **0.167–0.179 s/次**。
**同一份代码、同一配置、差 3.5×** ⇒ 在知道"量在哪个解释器上"之前，
任何加速比都不可信（`AGENTS §3.11`：看到的可能是错的那个进程）。

本脚本只做一件事：把**解释器身份 + 单算子基准**打出来，Windows 与 WSL 两侧各跑一次。
判据：若两侧差 > 1.5×，则**所有基准必须在 WSL 侧做**（生产链路在 WSL）。
"""
import os
import platform
import sys
import time

import numpy as np

print('=' * 88)
print('R564 环境指纹 + 单算子基准')
print('=' * 88)
print('  platform      : %s' % platform.platform())
print('  python        : %s' % sys.version.replace('\n', ' '))
print('  executable    : %s' % sys.executable)
print('  numpy         : %s' % np.__version__)
try:
    import scipy
    print('  scipy         : %s' % scipy.__version__)
except Exception as e:
    print('  scipy         : ?? %r' % (e,))
print('  cpu_count     : %s (logical)' % os.cpu_count())
try:
    with open('/proc/cpuinfo') as fh:
        for line in fh:
            if line.startswith('model name'):
                print('  cpu model     : %s' % line.split(':', 1)[1].strip())
                break
except Exception:
    pass
print('  /mnt/f 可达   : %s' % os.path.isdir('/mnt/f/speed_up'))

# ---- 基准 1：eps0_fields 的现行实现（6×nv 次整场 +=）----
N, NV = 64, 24
rng = np.random.default_rng(0)
phi = np.ascontiguousarray(rng.random((NV, N, N, N)))
e0v = np.ascontiguousarray(rng.normal(size=(NV, 6)) * 0.01)


def loop():
    e = np.zeros((6, N, N, N))
    for p in range(6):
        for v in range(NV):
            e[p] += e0v[v, p] * phi[v]
    return e


def gemm():
    return (e0v.T @ phi.reshape(NV, -1)).reshape(6, N, N, N)


def bench(fn, rep=5):
    fn()
    ts = []
    for _ in range(rep):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return float(np.median(ts))


t_loop = bench(loop)
t_gemm = bench(gemm)
d = float(np.max(np.abs(loop() - gemm()))) / float(np.max(np.abs(loop())))
print('')
print('  eps0_fields(N=%d,nv=%d)： loop=%.4f s   gemm=%.4f s   **%.2f×**   max|Δ|/max=%.2e'
      % (N, NV, t_loop, t_gemm, t_loop / t_gemm, d))

# ---- 基准 2：纯内存带宽（区分"机器慢"与"代码慢"）----
A = np.ascontiguousarray(rng.random((64, 64, 64)))
B = np.empty_like(A)


def copyb():
    np.copyto(B, A)


t_cp = bench(copyb, rep=20)
gb = 2.0 * A.nbytes / 2 ** 30
print('  内存带宽（copy 2 MB 数组）：%.4f s/次 ⇒ **%.1f GB/s**'
      % (t_cp, gb / t_cp))

# ---- 基准 3：BLAS dgemm（区分 BLAS 后端）----
M1 = np.ascontiguousarray(rng.random((512, 512)))
M2 = np.ascontiguousarray(rng.random((512, 512)))


def mm():
    return M1 @ M2


t_mm = bench(mm, rep=10)
print('  BLAS dgemm 512³：%.4f s ⇒ **%.2f GFLOPS**' % (t_mm, 2 * 512 ** 3 / t_mm / 1e9))
print('=' * 88)
