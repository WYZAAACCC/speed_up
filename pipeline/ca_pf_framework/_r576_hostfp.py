#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r576_hostfp.py --- **宿主指纹**：不只是版本号，还有**实测算力**。

## 为什么必须有它（本仓库已经栽过一次，本轮又栽了一次）

`AGENTS.md`/R564 的教训：同一个算子在 Windows numpy 2.1.3 与 WSL numpy 2.5.3 上
差 **2.1×**，我因此量错过两轮。而**同一个宿主**也会漂：本机是**笔记本**
（RTX 4060 Laptop）⇒ 温度墙 / 电源策略会让整机算力在几分钟内掉一半。

**实测证据（2026-10-02 本轮）**：
    00:41  `build.lam.c2c` = **6.39 s**   N=64
    01:00  `build.lam.c2c` = **15.6 s**   N=64（同一台机器、同一份代码、同一命令）
⇒ 期间所有"绝对秒数"都不可比。**没有算力指纹的墙钟数字一律作废。**

## 指纹怎么算

三个互补探针（都不依赖 BLAS 线程数，取**最好一次**以避开调度噪声）：
  * `py_loop`  —— 纯 Python 整数循环（**单核频率**的代理）
  * `np_axpy`  —— `a*b+c` 在 4 MB 数组上重复（**单核内存带宽**的代理）
  * `np_matmul`—— 512³ 双精度矩阵乘（**多核 + BLAS** 的代理）

输出一行 `HOSTFP py_loop=… np_axpy=… np_matmul=…`，供脚本之间的**可比性判据**使用。
"""
import sys
import time

import numpy as np


def _best(fn, reps=5):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return min(ts)


def main():
    def py_loop():
        s = 0
        for i in range(3000000):
            s += i * 3
        return s

    a = np.ones(1 << 19, dtype=np.float64)
    b = np.full(1 << 19, 1.0000001, dtype=np.float64)
    c = np.empty_like(a)

    def np_axpy():
        for _ in range(200):
            np.multiply(a, b, out=c)
            np.add(c, a, out=c)

    m1 = np.random.default_rng(0).random((512, 512))
    m2 = np.random.default_rng(1).random((512, 512))

    def np_matmul():
        for _ in range(3):
            m1 @ m2

    t1 = _best(py_loop)
    t2 = _best(np_axpy)
    t3 = _best(np_matmul, reps=3)
    print('HOSTFP py_loop=%.4f np_axpy=%.4f np_matmul=%.4f'
          % (t1, t2, t3))
    print('HOSTFP_DERIVED py_ops_per_s=%.1f axpy_GB_per_s=%.2f matmul_GFLOP_per_s=%.1f'
          % (3000000 / t1, (200 * 3 * (1 << 19) * 8) / t2 / 1e9,
             (3 * 2 * 512 ** 3) / t3 / 1e9))
    return 0


if __name__ == '__main__':
    sys.exit(main())
