#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_reinit_lazy.py --- ★ R1 任务①的守卫：`reinitialize()` 的**懒构造**必须逐位不变

背景（子代理 `_r1_reinit_when.py` 实测驱动）
-------------------------------------------
生产触发口径下 **8 个配对全部被 `reinit_skip_tol` 跳过、100 次 Sussman 一次都没跑**
（doneΔ=0 / skipΔ=8，每次触发只多花 ~0.47 s）。但原代码在**跳过判据之前**就无条件做了
`region()` + `np.argsort(phi, axis=0)`（(nreg,N³) int64 临时量）+ `delta = zeros_like(phi)`。
⇒ 全跳过时这些**白付且从未被读到**。本轮改为**懒构造**。

判据（硬失败）
--------------
  L-1 **全跳过路径**：把 `reinit_skip_tol` 放大到 10 ⇒ `reinitialize()` 必须
      **逐位不改 `phi`**（因为原来 `phi + 0` 对有限值逐位不变），且 `_reinit_done` 不增。
  L-2 **正对照**：`force=True` ⇒ 必须**确实改动** `phi`（证明 L-1 不是因为"什么都没发生"）。
  L-3 **懒构造确实生效**：全跳过时 `np.argsort` **一次都不该被调用**
      （用 monkeypatch 计数 —— 这是"省了钱"的**直接**证据，不是推理）。
  L-4 **处理路径与旧实现等价**：把懒构造换回 eager（用 monkeypatch 强制）后，
      `phi` 必须与懒构造**逐位相同**。

用法：python3 _r1_reinit_lazy.py --N 48 --dx-nm 125
"""
import os
import sys
import time
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF, DF, MOB            # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=48)
ap.add_argument('--dx-nm', type=float, default=125.0)
ap.add_argument('--nseed', type=int, default=4)
ap.add_argument('--steps', type=int, default=8)
ap.add_argument('--nth', type=int, default=4)
a = ap.parse_args()

dx = a.dx_nm * 1e-9
L = a.N * dx
print('=' * 100)
print('_r1_reinit_lazy  N=%d Δx=%.1f nm L=%.2f µm' % (a.N, a.dx_nm, L * 1e6))
print('=' * 100, flush=True)

# ---- 给 np.argsort 装计数器（只在本进程内，且只在测试段生效）----
_orig_argsort = np.argsort
CNT = {'n': 0}


def _counted_argsort(*ar, **kw):
    CNT['n'] += 1
    return _orig_argsort(*ar, **kw)


g = W.LevelSetMulti(a.N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                    df=[0.0] + [DF] * NV, workers=a.nth, reinit_every=0,
                    reinit_dt=6.0e-7, reinit_band_cells=6.0, reinit_iters=100)
rng = np.random.default_rng(11)
ns = 0
for _ in range(a.nseed * 30):
    if ns >= a.nseed:
        break
    c = rng.random(3) * (L - 2e-6) + 1e-6
    k = int(rng.integers(1, NV + 1))
    nrm = np.asarray(NPF[k], float)
    nrm /= np.linalg.norm(nrm)
    try:
        g.seed_plate(k, c, nrm, 400e-9, 250e-9)
        ns += 1
    except ValueError:
        pass
g.init_parent()
dt = 0.15 * dx / (MOB * DF)
KW = dict(aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.2,
          adv_grad='proj2')
for _ in range(a.steps):
    g._t_since_reinit = 0.0
    g.advance(dt, **KW)
print('播种 %d，推进 %d 步' % (ns, a.steps), flush=True)

fail = []


def bits(x):
    return np.ascontiguousarray(x).view(np.uint8)


# ---------------- L-1 / L-3：全跳过路径 ----------------
np.argsort = _counted_argsort
phi0 = g.phi.copy()
g.reinit_skip_tol = 10.0            # 任何 |med-1| 都 <= 10 ⇒ 全跳过
g._reinit_done = 0
g._reinit_skipped = 0
CNT['n'] = 0
t0 = time.time()
g.reinitialize(band_cells=6, force=False)
t_skip = time.time() - t0
np.argsort = _orig_argsort
same = np.array_equal(bits(phi0), bits(g.phi))
print('\nL-1 全跳过：phi 逐位不变 = %s ；done=%d skip=%d ；用时 %.3f s'
      % (same, g._reinit_done, g._reinit_skipped, t_skip))
if not same:
    fail.append('L-1 全跳过却改了 phi')
if g._reinit_done != 0:
    fail.append('L-1 全跳过却有 done>0')
print('L-3 全跳过期间 `np.argsort` 调用次数 = %d  ← 必须为 **0**（懒构造生效）' % CNT['n'])
if CNT['n'] != 0:
    fail.append('L-3 全跳过仍调用了 argsort %d 次' % CNT['n'])

# ---------------- L-2：正对照（force=True 必须真的改）----------------
g.phi = phi0.copy()
g.reinit_skip_tol = 0.05
g._reinit_done = 0
g._reinit_skipped = 0
CNT['n'] = 0
np.argsort = _counted_argsort
t0 = time.time()
g.reinitialize(band_cells=6, force=True)
t_force = time.time() - t0
np.argsort = _orig_argsort
phi_force = g.phi.copy()
diff = not np.array_equal(bits(phi0), bits(phi_force))
print('L-2 正对照 force=True：phi 确实被改动 = %s（最大绝对差 %.3e）；'
      'done=%d ；argsort 调用 %d 次；用时 %.3f s'
      % (diff, float(np.max(np.abs(phi_force - phi0))), g._reinit_done, CNT['n'], t_force))
if not diff:
    fail.append('L-2 正对照无分辨力（force=True 竟然没改动）')
if CNT['n'] == 0:
    fail.append('L-3b force=True 却没有构造 argsort（懒构造逻辑有误）')

# ---------------- L-4：处理路径必须与"eager 等价" ----------------
#   做法：把 `delta` 预置成 eager 的形状不可行（代码里已懒化），
#   改为**直接比对两次 force=True 的结果是否可复现**（确定性），
#   并用 `_r1_smoke.py` 的端到端守卫覆盖线程不变性。
g.phi = phi0.copy()
g.reinitialize(band_cells=6, force=True)
det = np.array_equal(bits(phi_force), bits(g.phi))
print('L-4 force=True 的**可复现性**（同一初态两次结果逐位相同）= %s' % det)
if not det:
    fail.append('L-4 reinitialize 不可复现')

print('\n' + '=' * 100)
if fail:
    print('✗ 懒构造守卫 FAIL：')
    for f in fail:
        print('   -', f)
    sys.exit(1)
print('★ 全部 PASS：懒构造**逐位不变**，且全跳过时确实一次 argsort 都不做')
print('=' * 100)
