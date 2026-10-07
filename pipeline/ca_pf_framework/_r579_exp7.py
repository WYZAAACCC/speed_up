#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r579_exp7.py --- goal §(7) 的两个**便宜的单变量实验**（各只改一个变量）。

## ① 为什么 `eps0_mode='gemm'` 在真引擎里反而更慢？
微基准（`_r562_opbench.py`）里 GEMM 比 einsum **快 18×**，但在真引擎里
`rfft+gemm+gather` (0.2873) **慢于** `rfft+einsum+gather` (0.2544)。
**假说**：`ParCtx` 的 4 个工作线程 + BLAS 自己的线程池**争核**
（GEMM 会开多线程，而 einsum 走的是 numpy 的单线程逐元素路径）。
**只改一个变量**：其余开关固定，只切 `eps0_mode`，并扫 `OPENBLAS_NUM_THREADS ∈ {1,2,4,8}`。

## ② `Λ` 是**实数**而 `Eh` 是**复数** —— numpy 真的走了"2 实乘"还是"4 实乘"？
`sig(k) = -Λ(k) : ε(k)`，`Λ` 实数、`ε` 复数。理论上只需对实部/虚部各做一次实矩阵乘。
现写法 `np.einsum('kpq,qk->pk', Lam_real, Eh_cplx)`。
**单变量**：把 `Eh` 拆成 `Eh.re` / `Eh.im` 分别与 `Λ` 相乘再合成，看是否更快。

判据：两个实验都**允许结论是"无收益"**，但**必须给出实测数**（goal 原文）。
"""
import os
import statistics
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MODE = os.environ.get('R579E_MODE', 'both')
N = int(os.environ.get('R579E_N', '64'))
REPS = int(os.environ.get('R579E_REPS', '9'))
OUT = os.environ.get('R579E_OUT', '_w2_r579_exp7.log')


def exp2():
    """② Λ(实) × Eh(复) 的两种写法。"""
    L = []
    rng = np.random.default_rng(2)
    K = N ** 3
    Lam = rng.standard_normal((K, 6, 6))
    Eh = rng.standard_normal((6, K)) + 1j * rng.standard_normal((6, K))

    def way_a():        # 现写法
        return -np.einsum('kpq,qk->pk', Lam, Eh)

    def way_b():        # 拆实虚
        r = -np.einsum('kpq,qk->pk', Lam, Eh.real)
        i = -np.einsum('kpq,qk->pk', Lam, Eh.imag)
        return r + 1j * i

    ra, rb = way_a(), way_b()
    d = float(np.max(np.abs(ra - rb))) / (float(np.max(np.abs(ra))) or 1.0)
    ta, tb, ratio = [], [], []
    for _ in range(REPS):
        t0 = time.perf_counter(); way_a(); t1 = time.perf_counter()
        way_b(); t2 = time.perf_counter()
        ta.append(t1 - t0); tb.append(t2 - t1); ratio.append((t1 - t0) / (t2 - t1))
    L.append('  ── ② Λ(实) × Eh(复)：einsum 一次 vs 拆实/虚两次 ──')
    L.append('     N=%d（K=%d）' % (N, K))
    L.append('     现写法  min=%.4f s  中位=%.4f s'
             % (min(ta), statistics.median(ta)))
    L.append('     拆实虚  min=%.4f s  中位=%.4f s'
             % (min(tb), statistics.median(tb)))
    L.append('     逐位差 max|Δ|/max = %.3e  ⇒ %s'
             % (d, '✅ 等价' if d < 1e-12 else '⚠ 不等价（%.3e）' % d))
    L.append('     交错配对 现写法/拆实虚 中位 = **%.3fx**  区间 [%.3f, %.3f]'
             % (statistics.median(ratio), min(ratio), max(ratio)))
    L.append('     ⇒ 结论：%s'
             % ('**无收益**（numpy 已经在走实数路径）' if statistics.median(ratio) < 1.05
                else '**有收益**，值得做成开关'))
    return L


SUB = r'''
import os, sys, time, statistics
sys.path.insert(0, %(here)r)
import numpy as np
import _r561_opfacct as AC
AC.N, AC.NV, AC.WORKERS = %(N)d, 24, 4
import windowB_pf3d as P3, windowB_acct as acct
acct.enable(); acct.reset()
t0 = time.perf_counter()
g = AC.build()
tb = time.perf_counter() - t0
g.advance(dt=1e-8)
acct.reset(); AC.T.clear(); AC.CNT.clear()
ts = []
for _ in range(%(STEPS)d):
    t0 = time.perf_counter(); g.advance(dt=1e-8); ts.append(time.perf_counter() - t0)
T, C = acct.totals()
print('RESULT mode=%%s blas=%%s med=%%.5f e0=%%.5f e0n=%%.0f' %% (
    os.environ.get('R561_EPS0','loop'), os.environ.get('OPENBLAS_NUM_THREADS','-'),
    statistics.median(ts),
    (T.get('el.eps0_fields', 0.0) + T.get('el.e0.gemm', 0.0) + T.get('el.e0.einsum', 0.0)),
    (C.get('el.eps0_fields', 0) + C.get('el.e0.gemm', 0) + C.get('el.e0.einsum', 0))))
'''


def exp1():
    """① eps0_mode × OPENBLAS_NUM_THREADS（每个组合一个独立进程，避免线程池状态污染）。"""
    L = []
    L.append('  ── ① `eps0_mode` × `OPENBLAS_NUM_THREADS`（每个组合独立进程）──')
    L.append('     ⚠ 单变量：其余开关固定为归档旧路（c2c / ed_pair=full）')
    steps = int(os.environ.get('R579E_STEPS', '5'))
    res = {}
    for mode in ('loop', 'einsum', 'gemm'):
        for nblas in ('1', '4'):
            env = dict(os.environ)
            env['R561_EPS0'] = mode
            env['OPENBLAS_NUM_THREADS'] = nblas
            env['OMP_NUM_THREADS'] = nblas
            env['MKL_NUM_THREADS'] = nblas
            env['R561_N'] = str(N)
            env['R561_NV'] = '24'
            env['R561_WORKERS'] = '4'
            p = subprocess.run([sys.executable, '-c',
                                SUB % dict(here=HERE, N=N, STEPS=steps)],
                               env=env, capture_output=True, text=True)
            line = [x for x in p.stdout.splitlines() if x.startswith('RESULT')]
            if not line:
                L.append('     %-7s blas=%s  ❌ 失败：%s'
                         % (mode, nblas, (p.stderr or '')[-200:]))
                continue
            d = dict(kv.split('=') for kv in line[0].split()[1:])
            res[(mode, nblas)] = float(d['med'])
            L.append('     %-7s blas=%s  ⇒ 单步中位 **%.4f s**   （ε⁰ 项 %.4f s，%s 次）'
                     % (mode, nblas, float(d['med']), float(d['e0']), d['e0n']))
    if ('einsum', '1') in res and ('gemm', '1') in res:
        L.append('     ⇒ 限 BLAS 线程后 gemm/einsum = %.3f（<1 ⇒ gemm 仍更慢）'
                 % (res[('gemm', '1')] / res[('einsum', '1')]))
    if ('einsum', '4') in res and ('gemm', '4') in res:
        L.append('     ⇒ 不限时        gemm/einsum = %.3f'
                 % (res[('gemm', '4')] / res[('einsum', '4')]))
    L.append('     ⇒ 结论：%s'
             % ('**线程争用假说成立**（限 BLAS 线程后 gemm 追上或反超）'
                if ('gemm', '1') in res and ('einsum', '1') in res
                and res[('gemm', '1')] <= res[('einsum', '1')] else
                '**线程争用假说未获支持**（限线程后 gemm 仍更慢）——如实记录'))
    return L


def main():
    L = ['=' * 100,
         'R579-EXP7 — goal §(7) 的两个单变量实验（N=%d）' % N, '=' * 100]
    if MODE in ('both', '2'):
        L += exp2()
        L.append('')
    if MODE in ('both', '1'):
        L += exp1()
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, OUT), 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
