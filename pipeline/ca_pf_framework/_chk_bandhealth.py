#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_bandhealth.py —— `W0-5` 仪表 `_band_health.health()` 的**验收判据**（含反向对照）

为什么要单独验收（项目纪律）
----------------------------
`AGENTS.md §3.3 教训 19`：「探针/检查工具**必须先做正对照**」——
拿一个**已知答案**跑通工具，再相信它对未知答案的读数。
本工具会被塞进**每一次心跳**，一旦它自己错了，**所有作业的健康读数都是错的**。

判据（`MEASUREMENT_SPEC R0`：已知答案优先）
-------------------------------------------
* **K-1 已知答案 `|∇d2| ≡ 1`**：把 `φ_0 = −sdf`、`φ_1 = +sdf`（解析板条 SDF）
  ⇒ `d2 = (φ_0−φ_1)/2 = −sdf` ⇒ `|∇d2| = 1` **处处** ⇒ `med_d2` 必须 ≈ **1.000**（±2%）。
* **K-2 已知答案 `|∇d2| ≡ 0.5`**：`φ_0 = −0.5·sdf`、`φ_1 = +0.5·sdf` ⇒ 必须 ≈ **0.500**（±2%）。
  ⇒ K-1/K-2 一起证明**刻度是线性的**（不是"恰好量对了一个点"）。
* **K-3 与既有实现一致**：`health()['med_d2']` 必须与 `_probe_drift_ns.stats()` 的
  （`argsort` 口径）在**同一状态**上一致到 **1e-9**。⇒ 防"新工具偷偷换了口径"。
* **K-4 `bonds` 一致**：与引擎自己的 `_band_bonds(region())` **逐位相同**。
* **K-5 全域量的反向对照**：把 `|∇d2| ≡ 1` 的场**只在一个角落**乘 3
  ⇒ `gmax_all` 必须**跳上去**（≈3），而 `med_d2`（带内）**必须几乎不变**。
  ⇒ 这一条直接证明"**全域统计量对带内退化/污染不敏感**"，也就是 `N1` 的机理本身。
* **K-6 开销**：`health()` 在 N=96 上的单次墙钟必须 **< 1 s**（心跳每 20 步一次，不能拖慢作业）。

退出码：0 = 全 PASS。
"""
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402
from _band_health import health, fmt                             # noqa: E402

N, dx = 64, 50e-9
L = N * dx
g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                    df=[0.0] + [3.5e8] * NV, workers=1, reinit_every=0)

# 解析板条 SDF（与 seed_plate 同族：法向 n、半厚 t/2、面内 R）
nrm = np.asarray(NPF[1], float)
nrm = nrm / np.linalg.norm(nrm)
cen = np.array([L / 2] * 3)
ax_ = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(ax_ - cen[0], ax_ - cen[1], ax_ - cen[2], indexing='ij')
proj = X * nrm[0] + Y * nrm[1] + Z * nrm[2]
other = np.sqrt(np.maximum(X ** 2 + Y ** 2 + Z ** 2 - proj ** 2, 0.0))
sdf = np.maximum(np.abs(proj) - 100e-9, other - 300e-9)      # 圆柱状板条，负=内部

fails = []


def build(scale):
    ph = np.full((g.nreg,) + sdf.shape, 1e-3)
    ph[0] = -scale * sdf
    ph[1] = +scale * sdf
    g.phi = ph
    return ph


# ---------------------------------------------------------------- K-1 / K-2
print('=' * 100)
print('_chk_bandhealth —— W0-5 仪表验收（含反向对照）')
print('=' * 100)
for tag, sc, truth in (('K-1', 1.0, 1.000), ('K-2', 0.5, 0.500)):
    build(sc)
    h = health(g)
    ok = abs(h['med_d2'] - truth) < 0.02 * truth
    print('\n【%s 已知答案】|∇d2| ≡ %.3f（把 φ_0/φ_1 设成 ∓%.2f·sdf）' % (tag, truth, sc))
    print('   实测 `med_d2` = **%.4f**（真值 %.3f，判据 ±2%%）⇒ %s'
          % (h['med_d2'], truth, 'PASS' if ok else 'FAIL'))
    if not ok:
        fails.append(tag)

# ---------------------------------------------------------------- K-3 与既有实现一致
build(1.0)
h = health(g)
# 既有实现（`_probe_drift_ns.stats` 的口径：argsort 取两个最小场）
o = np.argsort(g.phi, axis=0)
d2r = 0.5 * (np.take_along_axis(g.phi, o[0][None], 0)[0]
             - np.take_along_axis(g.phi, o[1][None], 0)[0])
gr = np.gradient(d2r, g.dx)
gnr = np.sqrt(gr[0] ** 2 + gr[1] ** 2 + gr[2] ** 2)
nrr = np.abs(d2r) <= 6.0 * g.dx
ref = float(np.median(gnr[nrr]))
ok = abs(h['med_d2'] - ref) < 1e-9
print('\n【K-3 与既有实现一致】`partition` 口径 %.10f  vs  `argsort` 口径 %.10f'
      % (h['med_d2'], ref))
print('   差 = %.2e（判据 < 1e-9）⇒ %s' % (abs(h['med_d2'] - ref), 'PASS' if ok else 'FAIL'))
if not ok:
    fails.append('K-3')

# ---------------------------------------------------------------- K-4 bonds 一致
refb = g._band_bonds(g.region())
ok = h['bonds'] == refb
print('\n【K-4 `bonds` 一致】health=%d  vs  引擎 `_band_bonds`=%d ⇒ %s'
      % (h['bonds'], refb, 'PASS' if ok else 'FAIL'))
if not ok:
    fails.append('K-4')

# ---------------------------------------------------------------- K-5 全域量的反向对照
build(1.0)
h_clean = health(g)
ph = g.phi.copy()
ph[:, 5:15, 5:15, 5:15] *= 3.0        # 只在一个角落放大 3×（远离板条与界面）
g.phi = ph
h_dirty = health(g)
ok_gmax = h_dirty['gmax_all'] > 2.5 * max(h_clean['gmax_all'], 1e-9)
ok_med = abs(h_dirty['med_d2'] - h_clean['med_d2']) < 0.02
print('\n【K-5 全域量 vs 带内量的**反向对照**】在一个远离界面的角落把场乘 3×')
print('   `gmax_all`  %.4f → **%.4f**（应跳上去）⇒ %s' % (h_clean['gmax_all'],
                                                          h_dirty['gmax_all'],
                                                          'PASS' if ok_gmax else 'FAIL'))
print('   `med_d2`    %.4f → **%.4f**（带内，应几乎不变）⇒ %s'
      % (h_clean['med_d2'], h_dirty['med_d2'], 'PASS' if ok_med else 'FAIL'))
print('   ★ 这条正是 `N1` 的机理：**全域统计量看不见带内的真实状态**。')
if not ok_gmax:
    fails.append('K-5a')
if not ok_med:
    fails.append('K-5b')

# ---------------------------------------------------------------- K-6 开销
build(1.0)
_t = time.time()
for _ in range(3):
    health(g)
dt = (time.time() - _t) / 3.0
ok = dt < 1.0
print('\n【K-6 开销】`health()` 在 N=%d 上单次 **%.4f s**（判据 < 1 s）⇒ %s'
      % (N, dt, 'PASS' if ok else 'FAIL'))
print('   （心跳每 20 步一次 ⇒ 相对步时 ~1–60 s 可忽略）')
if not ok:
    fails.append('K-6')

# ---------------------------------------------------------------- 抽样展示
print('\n【格式化抽样】')
print('   ' + fmt(h_clean, base=h_clean))
print('   ' + fmt(h_dirty, base=h_clean))
print('\n' + '=' * 100)
print('=== 仪表验收 %s ===' % ('全部 PASS' if not fails else ('FAIL: ' + ','.join(fails))))
sys.exit(0 if not fails else 1)
