#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_nestchk.py --- 结清任务 2 的最后一个未决项：嵌套 `map0` **不是逐位相同**是不是缺陷？

现象（`_r1_partest.py --mode selftest`）
----------------------------------------
  * 15 个核逐个与串行参考**逐位相同** ✅
  * 但"嵌套 `map0`"那一项打印 `嵌套结果仍逐位相同 = False`

两种可能，**必须分开**：
  (a) **缺陷**：并行层在"嵌套调用"时算错了；
  (b) **测试设计问题**：那个测试把 `x[lo:hi]`（**切片**）喂给 `p.gradient(..., edge_order=2)`，
      再与**整数组**的 `np.gradient(x, ...)` 比 —— 切片的**边界**本来就用单边差分，
      与整数组在同样位置的内点差分**必然不同** ⇒ 差异是**切片**造成的，不是并行层。

判据（决定性）
--------------
  N-1 `p.gradient(x[lo:hi])` vs `np.gradient(x[lo:hi])`（**同一个切片**，并行 vs 串行）
      ⇒ 必须**逐位相同**。若相同 ⇒ 并行层无罪，(b) 成立。
  N-2 `np.gradient(x[lo:hi])` vs `np.gradient(x)`（**切片 vs 整数组**，都用 numpy）
      ⇒ 若**不同** ⇒ 证明差异来自切片边界，与并行无关。
  N-3 顺带量一次**真实盒子进程的并行度**（CPU 时间 / 墙钟），作为任务 2
      「在计算盒子中仿真时实现了并行计算」的**现场证据**。
"""
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_par as P                                                # noqa: E402

N = 64
x = np.random.default_rng(7).standard_normal((N, N, N))
p = P.ParCtx(4)

print('=' * 96)
print('N-1 并行 vs 串行，**同一个切片**（决定性对照）')
print('-' * 96)
ok_all = True
for lo, hi in ((0, 16), (16, 32), (24, 40), (48, 64)):
    a = np.asarray(p.gradient(x[lo:hi], 1e-7)[0])
    b = np.gradient(x[lo:hi], 1e-7, edge_order=2)[0]
    same = np.array_equal(a.view(np.uint8), b.view(np.uint8))
    ok_all &= same
    print('   切片 [%2d,%2d)  p.gradient vs np.gradient ：逐位相同 = %-5s  最大差 %.3e'
          % (lo, hi, same, float(np.abs(a - b).max())))
print('   ⇒ %s' % ('✅ **并行层与 numpy 在切片上逐位相同** ⇒ 并行层无罪'
                   if ok_all else '⛔ 并行层在切片上就有差异 ⇒ **真缺陷**'))

print('\nN-2 切片 vs 整数组（**都用 numpy**，与并行无关）')
print('-' * 96)
diff_slab = False
for lo, hi in ((0, 16), (16, 32), (24, 40), (48, 64)):
    full = np.gradient(x, 1e-7, edge_order=2)[0][lo:hi]
    slab = np.gradient(x[lo:hi], 1e-7, edge_order=2)[0]
    d = float(np.abs(full - slab).max())
    if d > 0:
        diff_slab = True
    print('   切片 [%2d,%2d)  整数组取出的那段 vs 切片自己算 ：最大差 %.3e  %s'
          % (lo, hi, d, '（不同）' if d > 0 else '（相同）'))
print('   ⇒ %s' % ('✅ 切片与整数组**本就不同**（边界单边差分）⇒ 嵌套测试的"不同"是**测试设计**造成的'
                   if diff_slab else '⚠ 两者相同 ⇒ 差异另有来源，需继续查'))
p.close()

print('\nN-3 真实盒子进程的并行度（CPU 时间 / 墙钟）')
print('-' * 96)
try:
    out = subprocess.run(['ps', '-e', '-o', 'pid,etimes,time,args', '--no-headers'],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        if '_r1_exp.py --out' not in line:
            continue
        f = line.split()
        pid, et = f[0], int(f[1])
        ct = f[2]
        parts = [float(z) for z in ct.replace('-', ':').split(':')]
        cpu = parts[-1] + 60 * parts[-2] + (3600 * parts[-3] if len(parts) > 2 else 0)
        name = [z for z in f if z.startswith('_exp/')]
        print('   %-14s 墙钟 %5d s   CPU %8.1f s  ⇒ **%.2f 核在跑**'
              % (name[0][5:] if name else pid, et, cpu, cpu / max(et, 1)))
    print('   （>1 即为**盒子内**并发工作的直接证据；`--nthreads 4`）')
except Exception as e:                                                   # noqa: BLE001
    print('   ⚠ 量不到：%s' % e)
print('=' * 96)
