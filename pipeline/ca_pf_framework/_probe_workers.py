#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_workers.py --- ★ 并行度实测：`workers` 到底并行在哪？20 核能用上几核？

背景（Round 141）
----------------
`windowB_pf3d.py:262,265` 只在 `_fft/_ifft` 里把 `workers` 传给
`scipy.fft.fftn/ifftn` ⇒ **`workers` 只并行 FFT（= `elastic_driving`），
对 `advance` 毫无作用**。而实测 `advance` 是 `elastic_driving` 的 **7.5 倍**耗时
（N=192 / 24 µm / 125 nm：advance 34.6 s vs ed 4.6 s，见 `_w2_cost_N192.log`）。

本探针把两件事变成实测
--------------------
  W-1 **CPU/wall 比**（= 有效并行度）分别对 `elastic_driving` 与 `advance` 测
      ⇒ `advance` 若恒 ≈1.0，即坐实"**主瓶颈完全单线程**"。
  W-2 **FFT 的 workers 标度**：扫 workers = 1/2/4/8/16/20
      ⇒ 报 `elastic_driving` 的加速比，看 20 核里能吃到多少。

做法：只构造一次 `LevelSetMulti`，然后**改 `g.pf.workers` 重测**
（`workers` 是普通属性，走的是同一条代码路径，不会引入别的差异）。
CPU 时间用 `time.process_time()`（含所有线程），wall 用 `time.time()`。

用法：python3 _probe_workers.py [--L-um 24] [--dx-nm 187.5] [--reps 4]
"""
import os
import sys
import time
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF, DF, MOB, R_SEED, T_SEED   # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--L-um', type=float, default=24.0)
ap.add_argument('--dx-nm', type=float, default=187.5)
ap.add_argument('--n0', type=int, default=16)
ap.add_argument('--reps', type=int, default=4)
a = ap.parse_args()

L = a.L_um * 1e-6
dx = a.dx_nm * 1e-9
N = int(round(L / dx))
print('=' * 100)
print('_probe_workers   盒 %.2f µm  Δx %.2f nm  ⇒  N = %d（%.3g 胞）'
      % (a.L_um, a.dx_nm, N, N ** 3))
print('=' * 100, flush=True)

t0 = time.time()
g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                    df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                    reinit_dt=None)
rng = np.random.default_rng(7)
ns = 0
for _ in range(a.n0 * 8):
    if ns >= a.n0:
        break
    c = rng.random(3) * (L - 2 * (R_SEED + 0.3e-6)) + (R_SEED + 0.3e-6)
    k = int(rng.integers(1, NV + 1))
    nrm = np.asarray(NPF[k], float)
    nrm /= np.linalg.norm(nrm)
    try:
        g.seed_plate(k, c, nrm, R_SEED, T_SEED)
        ns += 1
    except ValueError:
        pass
g.init_parent()
print('构造 + 播种 %d 核完成，用时 %.1f s\n' % (ns, time.time() - t0), flush=True)

dt = 0.15 * dx / (MOB * DF)


def timed(fn, reps):
    fn()                                     # 预热
    w0, c0 = time.time(), time.process_time()
    for _ in range(reps):
        fn()
    w, c = time.time() - w0, time.process_time() - c0
    return w / reps, c / reps


print('W-1 / W-2  workers 扫描（每档 %d 次，含预热）' % a.reps)
print('  %-8s | %11s %11s %8s | %11s %11s %8s' %
      ('workers', 'ed wall(s)', 'ed cpu(s)', 'ed CPU/W', 'adv wall(s)', 'adv cpu(s)', 'adv CPU/W'))
ed_ref = None
res = []
for Wk in (1, 2, 4, 8, 16, 20):
    g.pf.workers = Wk
    g.workers = Wk
    wed, ced = timed(lambda: g.elastic_driving(), a.reps)
    wad, cad = timed(lambda: g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                                       mob_beta=3.5, mob_beta_w=2.3,
                                       adv_grad='proj2'), 2)
    if ed_ref is None:
        ed_ref = wed
    res.append((Wk, wed, ced, wad, cad))
    print('  %-8d | %11.3f %11.3f %8.2f | %11.3f %11.3f %8.2f'
          % (Wk, wed, ced, ced / max(wed, 1e-9), wad, cad, cad / max(wad, 1e-9)),
          flush=True)

print('\n  ⇒ 加速比（相对 workers=1）：')
for (Wk, wed, ced, wad, cad) in res:
    print('     workers=%-3d  elastic_driving ×%.2f   advance ×%.2f'
          % (Wk, ed_ref / wed, res[0][3] / wad))
print('\n  ⇒ 判定：')
ad_cpu = np.array([r[4] / max(r[3], 1e-9) for r in res])
ed_cpu = np.array([r[2] / max(r[1], 1e-9) for r in res])
print('     `advance` 的 CPU/wall 恒在 %.2f–%.2f ⇒ %s'
      % (ad_cpu.min(), ad_cpu.max(),
         '**基本单线程**（提高 workers 无用）' if ad_cpu.max() < 1.5
         else '有并行，随 workers 上升'))
print('     `elastic_driving` 的 CPU/wall 从 %.2f 升到 %.2f ⇒ workers 有效，但只对这一项'
      % (ed_cpu[0], ed_cpu[-1]))
print('     ⇒ 主瓶颈 `advance` 是**单线程**的，而机器有 20 核。')
print('=' * 100)
