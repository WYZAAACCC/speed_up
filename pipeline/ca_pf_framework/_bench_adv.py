#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bench_adv.py --- 判定 `advance` 是**算力受限**还是**访存带宽受限**

为什么必须测
-----------
实测 `advance` 占总步时 88%（N=192：34.8 s vs elastic_driving 4.7 s），
且它 **CPU/wall ≈ 1.1（完全单线程）**，而机器有 20 核。
但"值不值得并行化它"取决于瓶颈性质：

  * **算力受限** ⇒ 加线程接近线性加速 ⇒ 并行化收益巨大
  * **访存带宽受限** ⇒ 加线程几乎无收益（带宽是共享资源）⇒ 白干

旁证（不利）：N=96→192（胞数 ×8）时 `adv` 耗时 **×12（超线性）**，是访存恶化的迹象。

判定办法：**K 路并发聚合吞吐**
  同时跑 K 个**独立进程**，各自测 `advance` 的 steps/s。
    * 聚合吞吐随 K **线性增长** ⇒ 算力受限
    * 聚合吞吐随 K **持平**     ⇒ 带宽受限
本脚本同时报本机**峰值内存带宽**（triad 微基准），用于交叉验证：
若 `advance` 的等效带宽已接近本机峰值 ⇒ 带宽受限。

用法：python3 _bench_adv.py --L-um 24 --dx-nm 250 --n0 64 --steps 8
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
ap.add_argument('--dx-nm', type=float, default=250.0)
ap.add_argument('--n0', type=int, default=64)
ap.add_argument('--steps', type=int, default=8)
ap.add_argument('--tag', default='')
ap.add_argument('--no-bw', action='store_true')
a = ap.parse_args()


def bw_triad(mb=192, reps=6):
    """本机峰值内存带宽（GiB/s）：`a = b + 2c` ⇒ 3 个数组的流量。"""
    n = mb * 1024 * 1024 // 8
    b = np.full(n, 2.0)
    c = np.full(n, 3.0)
    a_ = np.empty(n)
    a_[:] = b + 2.0 * c                      # 预热 + 触碰页面
    t0 = time.time()
    for _ in range(reps):
        a_[:] = b + 2.0 * c
    dt = (time.time() - t0) / reps
    return 3.0 * n * 8 / dt / 2 ** 30


if not a.no_bw:
    print('BENCH_BW %.2f GiB/s' % bw_triad(), flush=True)

L = a.L_um * 1e-6
dx = a.dx_nm * 1e-9
N = int(round(L / dx))
t0 = time.time()
g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                    df=[0.0] + [DF] * NV, workers=1, reinit_every=0, reinit_dt=None)
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
t_build = time.time() - t0

dt = 0.15 * dx / (MOB * DF)
g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5,
          mob_beta_w=2.3, adv_grad='proj2')          # 预热（也把惰性缓存建起来）
w0, c0 = time.time(), time.process_time()
for _ in range(a.steps):
    g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5,
              mob_beta_w=2.3, adv_grad='proj2')
wall, cpu = time.time() - w0, time.process_time() - c0
print('BENCH_ADV tag=%s N=%d build=%.1fs steps=%d wall=%.2fs cpu=%.2fs '
      'sps=%.4f cpu/wall=%.2f'
      % (a.tag or 'x', N, t_build, a.steps, wall, cpu, a.steps / wall,
         cpu / max(wall, 1e-9)), flush=True)
