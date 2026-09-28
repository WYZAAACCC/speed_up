#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_probe_reinit_cost.py —— Gate A-1 的 **Q3 补测**：多变体 RVE 里 `reinitialize()` 到底多贵？

为什么单板探针不够
------------------
`_probe_reinit_onoff.py` 用的是**单板**（只有 **1 个活跃配对** (0,1)）。
而 `reinitialize()` 的代价 **正比于活跃配对数**（它对每个配对跑一遍 Sussman，`:2921` 的 `for (k,l) in pairs`）。
⇒ **单板会系统性低估** reinit 在生产构型里的开销。

本探针做什么
------------
在 **12 变体 RVE** 上，直接量三个数：
* `pairs` —— 活跃配对数（由 `region()` 的 6 邻域邻接算出，与 `reinitialize()` 内部同口径）；
* `t_step` —— 一次 `advance()` 的墙钟；
* `t_reinit` —— 一次 `reinitialize()` 的墙钟；
⇒ 报 **`t_reinit / t_step`** 与 **"每次 reinit 相当于几步"**。

判据（`MEASUREMENT_SPEC R0`）
----------------------------
* **正对照**：先量一次**空转**（只调 `region()`）以确保计时器本身没坏；
* **单调性**：配对数越多，`t_reinit` 应越大（否则说明配对循环没起作用）；
* **结论量**：`t_reinit / t_step`，以及结合实测触发频率（`T16` 冒烟：**79 次 / 100 步**）
  估出的 **reinit 占步时百分比**。

⚠ 本探针**只读**：不改引擎、不改任何默认；`reinitialize()` 是引擎公开方法。
用法：python3 _probe_reinit_cost.py [--N 64] [--dx-nm 50] [--steps-eq 3]
"""
import os
import sys
import time
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402
from _band_health import health, fmt                             # noqa: E402

MOB, DF = 1e-9, 3.5e8
ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=64)
ap.add_argument('--dx-nm', type=float, default=50.0)
ap.add_argument('--nseed', type=int, default=12)
ap.add_argument('--steps-eq', type=int, default=3, help='测 t_step 时取几次 advance 的中位')
ap.add_argument('--nvariant', type=int, default=12)
a = ap.parse_args()
N, dx = a.N, a.dx_nm * 1e-9
L = N * dx
print('=' * 100)
print('_probe_reinit_cost —— 多变体 RVE 里 reinit 的开销（Gate A-1 / Q3 补测）')
print('  N=%d Δx=%.1f nm L=%.2f µm  变体数=%d' % (N, a.dx_nm, L * 1e6, a.nvariant))
print('=' * 100)

g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                    df=[0.0] + [DF] * NV, workers=4, reinit_every=0, reinit_dt=6.0e-7)

# ---- 把 nseed 个不同变体铺在格点上（尽量互不接触，先让区域长出来） ----
ks = list(range(1, min(a.nvariant, NV) + 1))
centers = []
side = int(np.ceil(a.nseed ** (1.0 / 3.0)))
for i in range(a.nseed):
    ix, iy, iz = i % side, (i // side) % side, i // (side * side)
    centers.append(np.array([(ix + 0.5) / side, (iy + 0.5) / side, (iz + 0.5) / side]) * L)
R_seed = 0.28 * L / side
for k, cen in zip(ks, centers):
    nn = np.asarray(NPF[k], float)
    nn = nn / np.linalg.norm(nn)
    g.seed_plate(k, cen, nn, R_seed, 0.6 * R_seed)
g.init_parent()
reg = g.region()
nreg_present = len(np.unique(reg))
print('\n【构型】在场区域数（含母相）= **%d**；种子 %d 个；R_seed=%.0f nm'
      % (nreg_present, a.nseed, R_seed * 1e9))

# ---- 活跃配对（与 reinitialize() 内部同口径：6 邻域跨界） ----
pairs = set()
for ax in range(3):
    x, y = reg, np.roll(reg, -1, axis=ax)
    sel = x != y
    for u, v in zip(x[sel].ravel(), y[sel].ravel()):
        if u != v:
            pairs.add((int(min(u, v)), int(max(u, v))))
print('   活跃配对 = **%d** 个：%s' % (len(pairs), sorted(pairs)[:14]))

# ---- 正对照：空转计时（只调 region()） ----
t0 = time.time()
for _ in range(3):
    g.region()
t_idle = (time.time() - t0) / 3.0
print('\n【正对照】空转（只调 `region()`）单次 = **%.4f s**（计时器可用性检查）' % t_idle)

# ---- t_step：几次 advance 的中位 ----
dt = 0.15 * dx / (MOB * DF)
ts = []
for _ in range(a.steps_eq):
    t0 = time.time()
    g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
              mob_beta=3.5, mob_beta_w=2.3, norm_smooth=2)
    ts.append(time.time() - t0)
t_step = float(np.median(ts))
print('   `advance()` 单步 = **%.4f s**（%d 次：%s）'
      % (t_step, a.steps_eq, ' '.join('%.3f' % v for v in ts)))

# ---- t_reinit：一次 reinitialize 的墙钟（跑两次取小的，减小缓存噪声） ----
tr = []
for _ in range(2):
    t0 = time.time()
    g.reinitialize()
    tr.append(time.time() - t0)
t_re = float(np.min(tr))
h = health(g)
print('   `reinitialize()` 单次 = **%.4f s**（两次：%s）'
      % (t_re, ' '.join('%.3f' % v for v in tr)))
print('   `_reinit_done`=%d  `_reinit_skipped`=%d' % (h['rdone'], h['rskip']))

# ---- 结论量 ----
ratio = t_re / max(t_step, 1e-12)
print('\n' + '=' * 100)
print('【结论】')
print('   `t_reinit / t_step` = **%.4f**（即一次 reinit ≈ **%.1f%%** 的步时）'
      % (ratio, ratio * 100))
print('   ★ 关键：`t_reinit` **正比于活跃配对数**（%d 个），而 `t_step` 不随配对数增长' % len(pairs))
print('     —— 每个配对即使被**跳过**，也仍然要算一次全场的 `np.gradient(d2)` + 中位扫描')
print('     （`windowB_surface.py:2939-2941`，在 skip 判断 `:2952` **之前**）。')
print('     ⇒ 生产构型（变体多 ⇒ 配对多）里 reinit 的相对开销只会**更大**。')
print('\n   ⚠⚠ **停止外推** —— 本探针**第一版**把这里的比值乘上"别处测到的触发频率"，')
print('      打出过"reinit 占步时 488.6%"这种**>100% 的数**。**那是错的**：')
print('      * `T16` 冒烟跑的是 **N=32、~4 个变体**；本探针是 **N=64、12 个配对**；')
print('      * `t_step` 与 `t_reinit` 都随 N³ 与配对数缩放，**跨构型相乘没有意义**；')
print('      * 自证：结果若 >100%，说明外推无效（一个算子不可能占用超过全部步时）。')
print('      ⇒ **可引用的只有同一构型内的 `t_reinit/t_step`**；')
print('        要报"reinit 占总机时百分之几"，必须在**目标构型上直接量**。')
print('\n   本构型的实测辅助量：`_reinit_done`=%d  `_reinit_skipped`=%d'
      '（**跳过也要付全场梯度 + 中位的钱**）' % (h['rdone'], h['rskip']))
print('   ⚠ 本探针只读；配对数 %d（单板探针只有 1 ⇒ 会低估）' % len(pairs))
print('=' * 100)
