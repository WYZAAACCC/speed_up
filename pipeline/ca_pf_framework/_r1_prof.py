#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_prof.py --- ★ R1 任务②：`advance` 的**完整**开销归因（cProfile，无死角）

为什么必须重做
--------------
此前手工计时的结论是"只归因了 47%，53% 未归因"。未归因的部分恰恰是改造的靶子，
所以必须拿到**逐函数**的账。`cProfile` 会把 numpy 的 C 函数也记进来
（`numpy.roll` / `numpy.gradient` / `numpy.einsum` / `{method 'argmin' ...}` …），
因此可以做到无死角。

用法：
  python3 _r1_prof.py --N 192 --steps 2 --n0 64 --tag prof192
"""
import os
import sys
import time
import cProfile
import pstats
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF, DF, MOB, R_SEED, T_SEED   # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=192)
ap.add_argument('--L-um', type=float, default=24.0)
ap.add_argument('--n0', type=int, default=64)
ap.add_argument('--steps', type=int, default=2)
ap.add_argument('--warmup', type=int, default=0)
ap.add_argument('--adv', default='proj2')
ap.add_argument('--reinit-band', type=float, default=6.0)
ap.add_argument('--worker-el', type=int, default=4)
ap.add_argument('--tag', default='prof')
ap.add_argument('--top', type=int, default=45)
a = ap.parse_args()

L = a.L_um * 1e-6
dx = L / a.N


def rss_gb():
    cur = hwm = float('nan')
    with open('/proc/self/status') as f:
        for ln in f:
            if ln.startswith('VmRSS:'):
                cur = float(ln.split()[1]) / 1048576.0
            elif ln.startswith('VmHWM:'):
                hwm = float(ln.split()[1]) / 1048576.0
    return cur, hwm


print('=' * 100)
print('_r1_prof  N=%d  L=%.2f µm  Δx=%.1f nm  steps=%d' % (a.N, a.L_um, dx * 1e9, a.steps))
print('=' * 100, flush=True)

t0 = time.time()
g = W.LevelSetMulti(a.N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                    df=[0.0] + [DF] * NV, workers=a.worker_el, reinit_every=0,
                    reinit_dt=6.0e-7,
                    reinit_band_cells=(None if a.reinit_band == 0 else a.reinit_band))
print('构造 %.1f s ；RSS %.2f GB' % (time.time() - t0, rss_gb()[0]), flush=True)

rng = np.random.default_rng(7)
ns = 0
for _ in range(a.n0 * 8):
    if ns >= a.n0:
        break
    c = rng.random(3) * (L - 2 * (R_SEED + 0.3e-6)) + (R_SEED + 0.3e-6)
    k = int(rng.integers(1, NV + 1))
    nrm = np.asarray(NPF[k], float)
    nrm = nrm / np.linalg.norm(nrm)
    try:
        g.seed_plate(k, c, nrm, R_SEED, T_SEED)
        ns += 1
    except ValueError:
        pass
g.init_parent()
print('播种 %d ；RSS %.2f GB' % (ns, rss_gb()[0]), flush=True)

dt = 0.15 * dx / (MOB * DF)
KW = dict(aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3,
          adv_grad=a.adv)

# ---- warmup（把首次的 import/JIT/缓存分配等一次性开销排除在归因之外）----
for _ in range(a.warmup):
    g.elastic_driving()
    g.advance(dt, **KW)
    g._t_since_reinit = 0.0          # 强制不触发 reinit

# ---- 分离计时：elastic_driving / advance 各自 ----
print('\n--- 分离计时（不含 reinit）---', flush=True)
t_ed = t_ad = 0.0
for it in range(a.steps):
    g._t_since_reinit = 0.0
    t1 = time.time()
    g.elastic_driving()
    t2 = time.time()
    g.advance(dt, **KW)
    t3 = time.time()
    t_ed += t2 - t1
    t_ad += t3 - t2
    print('  step %d: elastic_driving %.2f s   advance %.2f s' % (it + 1, t2 - t1, t3 - t2),
          flush=True)
print('  平均：elastic_driving %.2f s + advance %.2f s = %.2f s/步'
      % (t_ed / a.steps, t_ad / a.steps, (t_ed + t_ad) / a.steps), flush=True)

# ---- reinit 单次计时（强制触发一次，量它到底多贵）----
print('\n--- reinit 单次（force=True）---', flush=True)
t1 = time.time()
g.reinitialize(band_cells=6, force=True)
t_re = time.time() - t1
print('  一次 reinitialize = %.2f s  =  %.2f 个 advance 步' % (t_re, t_re / (t_ad / a.steps)),
      flush=True)
print('  实际做了 %d 对，跳过 %d 对，region 翻转 %d 胞'
      % (getattr(g, '_reinit_done', 0), getattr(g, '_reinit_skipped', 0),
         getattr(g, '_reinit_reg_flips', 0)), flush=True)

# ---- cProfile 归因 ----
print('\n--- cProfile：advance 一步的逐函数归因 ---', flush=True)
g._t_since_reinit = 0.0
pr = cProfile.Profile()
pr.enable()
g.advance(dt, **KW)
pr.disable()
st = pstats.Stats(pr)
out = '_w2_%s.pstats' % a.tag
st.dump_stats(out)
print('  pstats 已写 %s' % out, flush=True)


def show(sortkey, title):
    print('\n  ===== 按 %s 排序 top%d =====' % (title, a.top), flush=True)
    st2 = pstats.Stats(pr)
    st2.sort_stats(sortkey)
    lines = []
    import io
    buf = io.StringIO()
    st2.stream = buf
    st2.print_stats(a.top)
    txt = buf.getvalue().splitlines()
    for ln in txt:
        if ln.strip().startswith('ncalls') or (ln.strip() and not ln.startswith('  ')):
            lines.append(ln)
        elif ln.strip():
            lines.append(ln)
    for ln in lines:
        print('  ' + ln, flush=True)


show('tottime', 'tottime（自身耗时，最能看到"谁在烧 CPU"）')
show('cumtime', 'cumtime（含子调用）')
print('=' * 100, flush=True)
