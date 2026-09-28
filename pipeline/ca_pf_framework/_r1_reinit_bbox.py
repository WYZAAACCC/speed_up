#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_reinit_bbox.py --- ★★★ R1 任务①的**端到端逐位守卫**：子盒 reinit ≡ 全域 reinit

判据（硬失败）
--------------
  B-1 在**真实引擎状态**（多核 RVE，有变体-变体界面）上，
      `reinit_bbox=True`（子盒）与 `False`（全域）跑同一次 `reinitialize()`，
      `phi` 必须**逐位相同**。
  B-2 **正对照**：把 `reinit_bbox_margin` 故意取小（如 1）⇒ 必须**出现差异**
      —— 否则说明这个守卫根本没有分辨力（"两次都一样"可能只是"子盒==全域"）。
  B-3 省了多少：报出每个配对的子盒体积 / 全盒体积，以及 wall 时间比。
  B-4 线程数不变性：`nthreads=1` 与 `nthreads=4` 在 `bbox=True` 下也必须逐位相同。

用法：python3 _r1_reinit_bbox.py --N 48 --dx-nm 125
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
ap.add_argument('--steps', type=int, default=4)
ap.add_argument('--nth', type=int, default=4)
a = ap.parse_args()

dx = a.dx_nm * 1e-9
L = a.N * dx
print('=' * 100)
print('_r1_reinit_bbox  子盒 reinit 端到端逐位守卫   N=%d Δx=%.1f nm L=%.2f µm'
      % (a.N, a.dx_nm, L * 1e6))
print('=' * 100, flush=True)


def build(workers):
    return W.LevelSetMulti(a.N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                           df=[0.0] + [DF] * NV, workers=workers, reinit_every=0,
                           reinit_dt=6.0e-7, reinit_band_cells=6.0)


t0 = time.time()
g = build(a.nth)
print('构造 %.1f s' % (time.time() - t0), flush=True)

rng = np.random.default_rng(3)
ns = 0
for _ in range(a.nseed * 20):
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
print('播种 %d' % ns, flush=True)

# 先跑几步让界面演化出真实的（非 SDF 的）形态 —— 否则 reinit 无活可干，守卫是空的
dt = 0.15 * dx / (MOB * DF)
KW = dict(aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3,
          adv_grad='proj2')
for it in range(a.steps):
    g._t_since_reinit = 0.0
    g.advance(dt, **KW)
print('已推进 %d 步（%.1f s）' % (a.steps, time.time() - t0), flush=True)

phi_ref = g.phi.copy()
fail = []


def run_once(bbox, margin=None, workers=None):
    g.phi = phi_ref.copy()
    g.reinit_bbox = bbox
    g.reinit_bbox_margin = margin
    g._reinit_done = 0
    g._reinit_skipped = 0
    g._reinit_bbox_used = 0
    g._reinit_bbox_frac = float('nan')
    if workers is not None:
        g.par.set_threads(workers)
    t1 = time.time()
    g.reinitialize(band_cells=6, force=True)
    tw = time.time() - t1
    return g.phi.copy(), tw, dict(done=getattr(g, '_reinit_done', 0),
                                  skip=getattr(g, '_reinit_skipped', 0),
                                  bbox_n=getattr(g, '_reinit_bbox_used', 0),
                                  frac=getattr(g, '_reinit_bbox_frac', float('nan')))


def bits(x):
    return np.ascontiguousarray(x).view(np.uint8)


print('\n--- B-1 子盒 vs 全域 ---', flush=True)
p_full, t_full, s_full = run_once(False)
p_sub, t_sub, s_sub = run_once(True)
same = np.array_equal(bits(p_full), bits(p_sub))
print('  全域：%s  用时 %.2f s' % (s_full, t_full))
print('  子盒：%s  用时 %.2f s' % (s_sub, t_sub))
print('  B-1 **phi 逐位相同 = %s**（最大绝对差 %.3e）'
      % (same, 0.0 if same else float(np.max(np.abs(p_full - p_sub)))))
print('  B-3 子盒/全盒体积比（最后一个配对）= %.4f ；wall 加速 = ×%.2f'
      % (s_sub['frac'], t_full / max(t_sub, 1e-9)))
if not same:
    fail.append('B-1 子盒与全域不逐位相同')

print('\n--- B-2 正对照：把 margin 故意取小（1 胞）⇒ **必须**出现差异 ---', flush=True)
p_bad, t_bad, s_bad = run_once(True, margin=1)
diff = not np.array_equal(bits(p_full), bits(p_bad))
print('  margin=1 时与全域不同 = %s（最大绝对差 %.3e）← 必须 True'
      % (diff, float(np.max(np.abs(p_full - p_bad)))))
if not diff:
    fail.append('B-2 正对照无分辨力（margin=1 竟然与全域相同）')

print('\n--- B-4 线程数不变性（bbox=True）---', flush=True)
for nth in (1, 2, a.nth):
    p_n, t_n, s_n = run_once(True, workers=nth)
    okk = np.array_equal(bits(p_n), bits(p_sub))
    print('  nthreads=%-2d 用时 %6.2f s  与 nthreads=%d 逐位相同 = %s'
          % (nth, t_n, a.nth, okk))
    if not okk:
        fail.append('B-4 nthreads=%d 与 %d 不同' % (nth, a.nth))

print('\n' + '=' * 100)
if fail:
    print('✗ reinit 子盒守卫 FAIL：')
    for f in fail:
        print('   -', f)
    sys.exit(1)
print('★ 全部 PASS：子盒 reinit 与全域**逐位相同**，且正对照有分辨力')
print('=' * 100)
