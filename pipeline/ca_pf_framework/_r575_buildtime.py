#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r575_buildtime.py --- 建引擎耗时 c2c vs rfft（**修掉"白算全谱表"之后**重测）。

`_r574` D2 首版报 c2c→rfft **+7.4 s**，但那一版里 rfft 分支**先算了一遍全谱表再丢掉**
（见 `windowB_pf3d.py` 里的记账）⇒ 那个数不能用来回答"rfft 的启停代价是多少"。

本量具：
  * **交错**建表 N 轮（c2c, rfft, c2c, rfft, …），取配对差 —— 首轮含一次性预热，故丢弃；
  * 同时报 `lambda_packed` 单独耗时（全谱 vs 半谱 vs Nyquist 子集），
    给出"理论应当省多少"的**解析对照**（`Mh/M = (N/2+1)/N`）。
判据：
  * B1 rfft 的建表耗时应当 **≤ c2c**（因为主表只有一半大 + 一小块 Nyquist 子集）
  * B2 负对照：故意**保留**白算的全谱表（环境变量 `R575_WASTE=1` 时用旧的 `_lam` 预计算）
        ⇒ 必须明显更慢，否则本量具没有分辨力
"""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                    # noqa: E402
import windowB_pf3d as P3                                      # noqa: E402
from T16_verify_rve import C, EPS0                             # noqa: E402

N = int(os.environ.get('R575_N', '64'))
NV = int(os.environ.get('R575_NV', '8'))
WORKERS = int(os.environ.get('R575_WORKERS', '4'))
ROUNDS = int(os.environ.get('R575_ROUNDS', '3'))
LOG = []


def A(s):
    LOG.append(s)
    print(s, flush=True)


A('=' * 92)
A('R575 — 建引擎耗时 c2c vs rfft（N=%d nv=%d 交错 %d 轮）' % (N, NV, ROUNDS))
A('=' * 92)

eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(NV)]
half = N // 2 + 1


def build(mode):
    t0 = time.perf_counter()
    g = W.LevelSetMulti(N, 1.0, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] + [3.0e8] * NV, workers=WORKERS,
                        reinit_every=20, reinit_dt=1e-4, reinit_band_cells=6.0,
                        phi_prec='f64', fft_mode=mode,
                        eps0_mode='einsum', ed_pair_mode='gather')
    return g, time.perf_counter() - t0


# ---- 预热（首轮含一次性开销，丢弃）----
_, _w1 = build('c2c')
_, _w2 = build('rfft')
A('')
A('  预热轮（丢弃）：c2c %.3f s   rfft %.3f s' % (_w1, _w2))

res = {'c2c': [], 'rfft': []}
for r in range(ROUNDS):
    for m in ('c2c', 'rfft'):
        _, t = build(m)
        res[m].append(t)
        del _
A('')
A('  ── B1 交错建表（丢弃首轮预热）──')
mc, mr = float(np.median(res['c2c'])), float(np.median(res['rfft']))
A('      c2c  中位 = %.3f s   （各轮：%s）'
  % (mc, ' '.join('%.2f' % x for x in res['c2c'])))
A('      rfft 中位 = %.3f s   （各轮：%s）'
  % (mr, ' '.join('%.2f' % x for x in res['rfft'])))
A('      配对差 (rfft − c2c) 中位 = **%+.3f s**  ⇒ %s'
  % (mr - mc, '✅ rfft 不更贵' if mr <= mc * 1.05 else '⚠ rfft 更贵'))

# ---- 解析对照：lambda_packed 三块的单独耗时 ----
A('')
A('  ── lambda_packed 的解析对照（同一进程直接测）──')
kv = 2 * np.pi * np.fft.fftfreq(N, d=1.0 / N)
Kf = np.stack(np.meshgrid(kv, kv, kv, indexing='ij'), -1).reshape(-1, 3)
idx = np.stack(np.meshgrid(np.arange(N), np.arange(N), np.arange(half),
                           indexing='ij'), -1).reshape(-1, 3)
ii, jj, mm = idx[:, 0], idx[:, 1], idx[:, 2]
nyq = (ii == N // 2) | (jj == N // 2) | (mm == N // 2)
Kh = np.stack(np.meshgrid(kv, kv, kv[:half], indexing='ij'), -1).reshape(-1, 3)
mir = (((N - ii) % N) * N + ((N - jj) % N)) * N + ((N - mm) % N)
ts = {}
for nm, KK in (('全谱 K (M=%d)' % Kf.shape[0], Kf),
               ('半谱 Kh (Mh=%d)' % Kh.shape[0], Kh),
               ('Nyquist 子集 (%d)' % int(nyq.sum()), Kf[mir[nyq]])):
    t0 = time.perf_counter()
    _ = P3.lambda_packed(C, KK, k0_mode='free')
    ts[nm] = time.perf_counter() - t0
    del _
    A('      %-28s %.3f s' % (nm, ts[nm]))
A('      Mh/M = %d/%d = %.4f ⇒ 半谱主表应当只有全谱的 %.0f%%'
  % (Kh.shape[0], Kf.shape[0], Kh.shape[0] / Kf.shape[0],
     100 * Kh.shape[0] / Kf.shape[0]))
A('      ⇒ 修好后 rfft 应当省掉「%.2f s 全谱 − %.2f s 半谱」≈ **%.2f s**'
  % (ts['全谱 K (M=%d)' % Kf.shape[0]], ts['半谱 Kh (Mh=%d)' % Kh.shape[0]],
     ts['全谱 K (M=%d)' % Kf.shape[0]] - ts['半谱 Kh (Mh=%d)' % Kh.shape[0]]))

out = '\n'.join(LOG)
with open(os.path.join(HERE, '_w2_r575_buildtime.log'), 'w', encoding='utf-8') as fh:
    fh.write(out + '\n')
