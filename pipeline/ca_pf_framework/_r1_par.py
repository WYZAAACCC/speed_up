#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_par.py --- ★ R1 任务②：`advance` 为什么只能单核？能不能多核？

判据（全部实测，不推理）
-----------------------
  P-1 **GIL 释放实测**：numpy 的逐元素 ufunc / `np.roll` / `np.where` /
      `np.gradient` / `np.einsum` 在**线程**里到底放不放 GIL？
      做法：把同一个算子按 axis=0 切成 `nth` 个 slab，用 `ThreadPoolExecutor` 跑，
      量 wall 时间随 `nth` 的标度。**真并行 ⇒ 明显下降；纯 GIL 串行 ⇒ 平坦**。
      正对照：`time.sleep`（必然并行）+ 纯 Python 循环（必然串行）。
  P-2 **算子清单**：逐个算子测标度，找出哪些能线程并行、哪些不能。
  P-3 **带宽天花板**：本机实测 triad 带宽，以及"一个 N³ 逐元素 pass"的实测耗时
      ⇒ 反推 `advance` 一步到底做了多少个全场 pass（这是并行的**上限**依据：
      若已到带宽墙，加核无用，必须减少 pass）。
  P-4 **线程 + slab 的正确性**：slab 分解（带 halo）与全盒结果是否**逐位相同**。
      ★ 这一条是硬门槛：不允许"快了但数变了"。

用法：
  python3 _r1_par.py --N 192 --reps 5
"""
import os
import sys
import time
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=192)
ap.add_argument('--reps', type=int, default=5)
ap.add_argument('--maxth', type=int, default=20)
a = ap.parse_args()

N = a.N
NTH = [1, 2, 4, 8, 16, 20]
NTH = [t for t in NTH if t <= a.maxth]

print('=' * 100)
print('_r1_par   N = %d   N³ = %.4g   数组 = %.1f MB/个 (float64)'
      % (N, N ** 3, N ** 3 * 8 / 2 ** 20))
print('  线程上限 = %d ；numpy %s ；线程后端 = %s'
      % (a.maxth, np.__version__, threading.current_thread().__class__.__module__))
print('=' * 100)


def best(fn, reps):
    """跑 reps 次取**最小** wall（最小比平均更抗调度抖动）。"""
    t = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        t.append(time.perf_counter() - t0)
    return min(t)


def slabs(n, nth, halo=0):
    """把 [0,n) 切成 nth 段（尽量均匀），每段外扩 halo，返回 (lo,hi) 列表。"""
    edges = [int(round(i * n / nth)) for i in range(nth + 1)]
    out = []
    for i in range(nth):
        lo, hi = edges[i], edges[i + 1]
        out.append((max(0, lo - halo), min(n, hi + halo), lo, hi))
    return out


def run_slabs(fn, n, nth, halo=0, pool=None):
    """fn(lo, hi) 处理 [lo,hi)；返回每段结果（调用者自己裁剪）。"""
    segs = slabs(n, nth, halo)
    if nth == 1:
        return [fn(lo, hi) for (lo, hi, _, _) in segs]
    with ThreadPoolExecutor(max_workers=nth) as ex:
        futs = [ex.submit(fn, lo, hi) for (lo, hi, _, _) in segs]
        return [f.result() for f in futs]


# ---------------------------------------------------------------- P-1 正/负对照
print('\n' + '-' * 100)
print('P-1 正/负对照（确认量具本身能分辨"真并行"与"纯串行"）')
print('-' * 100)


def ctrl_sleep(nth):
    def one(_lo, _hi):
        time.sleep(0.05)
        return None
    t0 = time.perf_counter()
    run_slabs(one, 1000, nth)
    return time.perf_counter() - t0


def ctrl_pyloop(nth):
    arr = list(range(400000))

    def one(lo, hi):
        s = 0
        for v in arr[lo:hi]:
            s += v * v
        return s
    t0 = time.perf_counter()
    run_slabs(one, len(arr), nth)
    return time.perf_counter() - t0


print('  %-34s %s' % ('测试', ' '.join('%8d' % t for t in NTH)))
_r = [ctrl_sleep(t) for t in NTH]
print('  %-34s %s   ← 应 ~1/N（真并行）'
      % ('[正对照] time.sleep×%d' % 1, ' '.join('%8.4f' % v for v in _r)))
_r = [ctrl_pyloop(t) for t in NTH]
print('  %-34s %s   ← 应平坦（GIL 串行）'
      % ('[负对照] 纯 Python 循环', ' '.join('%8.4f' % v for v in _r)))

# ---------------------------------------------------------------- P-2 逐算子标度
print('\n' + '-' * 100)
print('P-2 逐算子线程标度（N=%d；比值 = t(1)/t(nth)，>1 即真并行）' % N)
print('-' * 100)

x = np.random.default_rng(0).standard_normal((N, N, N))
y = np.empty_like(x)
V3 = [np.random.default_rng(i + 1).standard_normal((N, N, N)) for i in range(3)]
out_full = {}


def mk_ufunc(op):
    def f(lo, hi):
        return op(x[lo:hi])
    return f


def mk_roll(_ax):
    def f(lo, hi):
        return np.roll(x[lo:hi], 1, axis=_ax)
    return f


def mk_grad(halo, ax):
    def f(lo, hi):
        return np.gradient(x[lo:hi], 1e-7, edge_order=2)[ax]
    return f


def mk_flux(order):
    def f(lo, hi):
        return W.upwind_flux_vec(x[lo:hi], [v[lo:hi] for v in V3], 1e-7, order=order)
    return f


def mk_argmin():
    st = np.stack([x] + [x * (i + 1) for i in range(12)])   # 13 个场

    def f(lo, hi):
        return np.argmin(st[:, lo:hi], axis=0)
    return f


def mk_runnerup():
    st = np.stack([x] + [x * (i + 1) for i in range(12)])

    def f(lo, hi):
        nreg = st.shape[0]
        karr = np.argmin(st[:, lo:hi], axis=0)
        larr = np.empty(karr.shape, dtype=karr.dtype)
        _b = np.full(karr.shape, np.inf)
        for j in range(nreg):
            pj = st[j, lo:hi]
            mj = (karr != j) & (pj < _b)
            larr[mj] = j
            _b[mj] = pj[mj]
        return larr
    return f


def mk_einsum():
    a3 = np.stack(V3, -1)

    def f(lo, hi):
        return np.einsum('...i,...i->...', a3[lo:hi], a3[lo:hi])
    return f


def mk_norm():
    a3 = np.stack(V3, -1)

    def f(lo, hi):
        return np.linalg.norm(a3[lo:hi], axis=-1)
    return f


def mk_minmod():
    def f(lo, hi):
        return W._minmod(x[lo:hi], np.roll(x[lo:hi], 1, 0))
    return f


def mk_npwhere():
    def f(lo, hi):
        return np.where(x[lo:hi] > 0, x[lo:hi], -x[lo:hi])
    return f


CASES = [
    ('np.exp (ufunc)',              mk_ufunc(np.exp),            0),
    ('x*x+2*x (ufunc chain)',       mk_ufunc(lambda z: z * z + 2.0 * z), 0),
    ('np.roll(axis=0)',             mk_roll(0),                  0),
    ('np.roll(axis=2)',             mk_roll(2),                  2),
    ('np.gradient()[0]',            mk_grad(1, 0),               1),
    ('np.gradient()[2]',            mk_grad(1, 2),               2),
    ('np.where',                    mk_npwhere(),                0),
    ('_minmod(a,roll(a))',          mk_minmod(),                 1),
    ('einsum ...i,...i->...',       mk_einsum(),                 0),
    ('np.linalg.norm(axis=-1)',     mk_norm(),                   0),
    ('upwind_flux_vec order=1',     mk_flux(1),                  2),
    ('upwind_flux_vec order=2',     mk_flux(2),                  2),
    ('argmin over 13 fields',       mk_argmin(),                 0),
    ('winner+runner-up (13 场)',    mk_runnerup(),               0),
]

print('  %-28s %8s | %s' % ('算子', 't1 (s)', ' '.join('%8d' % t for t in NTH)))
print('  ' + '-' * 74)
TAB = {}
for name, fn, halo in CASES:
    ts = []
    for nth in NTH:
        t = best(lambda: run_slabs(fn, N, nth, halo=halo), a.reps)
        ts.append(t)
    TAB[name] = ts
    print('  %-28s %8.4f | %s' % (name, ts[0], ' '.join('%8.4f' % v for v in ts)))
print('\n  ---- 加速比 t(1)/t(nth) ----')
print('  %-28s %8s | %s' % ('算子', 't1 (s)', ' '.join('%8s' % t for t in NTH)))
for name, ts in TAB.items():
    print('  %-28s %8.4f | %s'
          % (name, ts[0],
             ' '.join('%8.2f' % (ts[0] / max(v, 1e-9)) for v in ts)))

# ---------------------------------------------------------------- P-3 带宽
print('\n' + '-' * 100)
print('P-3 内存带宽天花板（triad: a = b + s*c，3 个 N³ 数组）')
print('-' * 100)
bb = np.random.default_rng(9).standard_normal((N, N, N))
cc = np.random.default_rng(10).standard_normal((N, N, N))


def triad():
    np.add(bb, 2.5 * cc, out=y)


t1 = best(triad, a.reps)
nbytes = 3 * N ** 3 * 8          # 读 b, 读 c, 写 a
print('  单线程 triad：%.4f s  ⇒  **%.2f GB/s**（3×N³×8 = %.0f MB）'
      % (t1, nbytes / t1 / 2 ** 30, nbytes / 2 ** 20))
for nth in NTH[1:]:
    tt = best(lambda: run_slabs(lambda lo, hi: np.add(bb[lo:hi], 2.5 * cc[lo:hi],
                                                      out=y[lo:hi]), N, nth), a.reps)
    print('    nth=%-2d  %.4f s  ⇒  %.2f GB/s  （×%.2f）'
          % (nth, tt, nbytes / tt / 2 ** 30, t1 / tt))

# ---------------------------------------------------------------- P-4 正确性
print('\n' + '-' * 100)
print('P-4 slab 分解的**逐位正确性**（halo 足够时，内部必须与全盒逐位相同）')
print('-' * 100)


def cmp_bits(tag, full, parts, halo, nth):
    """把各段（去掉 halo）拼回去，与全盒逐位比较。"""
    segs = slabs(N, nth, halo)
    acc = np.empty_like(full)
    for (lo, hi, clo, chi), p in zip(segs, parts):
        inner = p[clo - lo: chi - lo]
        acc[clo:chi] = inner
    same = np.array_equal(acc.view(np.uint8), full.view(np.uint8))
    md = float(np.max(np.abs(acc - full))) if not same else 0.0
    print('  %-30s halo=%d nth=%-2d  逐位相同 = %-5s   最大绝对差 = %.3e'
          % (tag, halo, nth, same, md))
    return same


ok_all = True
for nth in (2, 4, 8):
    f_full = W.upwind_flux_vec(x, V3, 1e-7, order=2)
    parts = run_slabs(lambda lo, hi: W.upwind_flux_vec(
        x[lo:hi], [v[lo:hi] for v in V3], 1e-7, order=2), N, nth, halo=2)
    ok_all &= cmp_bits('upwind_flux_vec order=2', f_full, parts, 2, nth)

for nth in (2, 4, 8):
    g_full = np.gradient(x, 1e-7, edge_order=2)[1]
    parts = run_slabs(lambda lo, hi: np.gradient(x[lo:hi], 1e-7, edge_order=2)[1],
                      N, nth, halo=1)
    ok_all &= cmp_bits('np.gradient edge_order=2', g_full, parts, 1, nth)

print('\n  ⇒ P-4 总判定：%s' % ('★ 逐位相同（slab 分解安全）' if ok_all
                                else '✗ 有差异（分解不安全）'))

# ---------------------------------------------------------------- P-5 反推 pass 数
print('\n' + '-' * 100)
print('P-5 由实测带宽反推 `advance` 一步做了多少个"全场 pass"')
print('-' * 100)
BW = nbytes / t1 / 2 ** 30
T_MEAS = {96: (11.31, 250.0), 192: (34.81, 125.0)}
print('  实测单线程 triad 带宽 = %.2f GB/s' % BW)
for nn, (tadv, dxn) in sorted(T_MEAS.items()):
    per_pass = 3 * nn ** 3 * 8 / (BW * 2 ** 30)     # 一个"读2写1"pass 的时间
    print('  N=%-4d advance = %6.2f s/步（Δx=%.1f nm）'
          '  ⇒  约 %6.0f 个"读2写1"pass   （单 pass %.1f ms）'
          % (nn, tadv, dxn, tadv / per_pass, per_pass * 1e3))
print('=' * 100)
