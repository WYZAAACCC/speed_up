#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r559_profile.py —— **在当前代码上重新剖析 `advance()`**（回答"CPU 还有多少余量"）。

## 为什么必须重跑
`R30_AUDIT_LEDGER.md §204` 的剖析（`argmin` 18.4% / **`eps0_fields` 17.0%** / `einsum` 10.9% …）
是**用一个旧配置**做的，而其中 `eps0_fields` **17% 这一条可能已经过时**：

* `windowB_pf3d.py` 里有**两条路**：
  * `eps0_fields()`      —— **慢**：`6 × nv` 次整场乘加
  * `eps0_fields_idx(idx)` —— **快**：**gather**，只要 6 次（`windowB_pf3d.py:242-259`，
    注释说两者**逐位相同**，由 `T3_verify_fastpath.py` T3-3 把关）
* `windowB_surface.py:3439` 的 `advance()` 热路径**传了 `reg`** ⇒ 走**快的 gather**
* 而 `pf3d.py:324/379/559` 那几个**无参**调用是 `forces()` / `E_el()`（测量/工具入口）

⇒ **旧剖析里的 17% 很可能是"T3 之前"的数** ⇒ **不得据此下结论**。
本量具在**当前代码**上重跑，并**明确区分**两条路各被调用了多少次。

## 判据（先写死）
* **Q1**：`eps0_fields`（慢路）在生产热路径上的调用次数必须 **== 0**。
  若 >0 ⇒ **热路径退化到了慢路**，那本身就是一条真缺陷。
* **Q2**：报出 `advance()` 的**函数级** top-15（按 tottime），覆盖旧剖析里那 28% 的"其余"。
* **Q3**：`scipy.fft` 占比 —— 复现"FFT 不是瓶颈"这条旧结论（若已不成立要更正）。
* **Q4 正对照**：剖析**必须看到 `advance` 出现在栈里**（否则量到的是别的东西）。
"""
import cProfile
import io
import os
import pstats
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                    # noqa: E402
import windowB_pf3d as P3                                      # noqa: E402
from T16_verify_rve import C, EPS0                             # noqa: E402

N = 64
NV = 24
DX_UM = 0.0625
STEPS = 6
WORKERS = 4

# ---- 插桩：数两条路各被调了多少次（**只计数，不改行为**）----
COUNT = {'slow': 0, 'fast': 0}
_orig_slow = P3.PF3D.eps0_fields
_orig_fast = P3.PF3D.eps0_fields_idx


def _slow(self):
    COUNT['slow'] += 1
    return _orig_slow(self)


def _fast(self, idx):
    COUNT['fast'] += 1
    return _orig_fast(self, idx)


P3.PF3D.eps0_fields = _slow
P3.PF3D.eps0_fields_idx = _fast


def main():
    L = ['=' * 100,
         'R559 —— 当前代码上的 `advance()` 剖析（N=%d, nv=%d, workers=%d）'
         % (N, NV, WORKERS), '=' * 100]
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(NV)]
    g = W.LevelSetMulti(N, N * DX_UM, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] + [3.0e8] * NV, workers=WORKERS,
                        reinit_every=20, reinit_dt=1e-4, reinit_band_cells=6.0,
                        phi_prec='f64')
    g.init_parent()
    rng = np.random.default_rng(7)
    nrm = np.array([0.0, 0.0, 1.0]); along = np.array([1.0, 0.0, 0.0])
    Lc = N * DX_UM
    for k in (1, 2, 3):
        g.seed_plate(k, rng.random(3) * (Lc * 0.6) + Lc * 0.2, nrm, 120e-9, 300e-9)
    g.advance(dt=1e-8)                       # 预热

    # ---- 手动计时一个"干净"的 s/步（无剖析器开销）----
    ts = []
    for _ in range(STEPS):
        t0 = time.perf_counter()
        g.advance(dt=1e-8)
        ts.append(time.perf_counter() - t0)
    s_per = float(np.median(ts))
    L.append('  干净 s/步 = **%.4f s**（无剖析器开销，%d 步中位数）' % (s_per, STEPS))

    # ---- cProfile ----
    pr = cProfile.Profile()
    pr.enable()
    for _ in range(STEPS):
        g.advance(dt=1e-8)
    pr.disable()
    st = pstats.Stats(pr)
    tot = st.total_tt
    L.append('  剖析总时间 = %.3f s（%d 步 ⇒ %.4f s/步**含剖析开销**）'
             % (tot, STEPS, tot / STEPS))
    L.append('')
    L.append('  ── Q2 函数级 top-15（按 **tottime**，即函数自身耗时） ──')
    L.append('  %-9s %-7s %-9s %s' % ('tottime', '占比', 'ncalls', '函数'))
    rows = sorted(st.stats.items(), key=lambda kv: -kv[1][2])[:15]
    for (fn, _, name), (cc, nc, tt, ct, _) in rows:
        short = '%s:%d(%s)' % (os.path.basename(fn), _ if False else 0, name)
        L.append('  %-9.3f %-6.1f%% %-9d %s'
                 % (tt, 100 * tt / tot, nc, short.split('(')[0] + ':' + name))
    # 按"模块/算子族"聚合（更容易读）
    fam = {}
    for (fn, _, name), (cc, nc, tt, ct, _) in st.stats.items():
        key = name
        fam[key] = fam.get(key, 0.0) + tt
    L.append('')
    L.append('  ── 按**函数名**聚合 top-14 ──')
    for k, v in sorted(fam.items(), key=lambda kv: -kv[1])[:14]:
        L.append('     %-34s %7.3f s  **%5.1f%%**' % (k, v, 100 * v / tot))

    # ---- Q1/Q3/Q4 ----
    L.append('')
    ok1 = COUNT['slow'] == 0
    L.append('  ▶ **Q1 慢路 `eps0_fields` 在热路径上的调用次数 = %d**（判据 == 0）⇒ **%s**'
             % (COUNT['slow'], '✅ PASS' if ok1 else
                '❌ **FAIL ⇒ 热路径退化到慢路，这是一条真缺陷**'))
    L.append('     快路 `eps0_fields_idx` 调用次数 = %d' % COUNT['fast'])
    fft_t = sum(v for k, v in fam.items() if 'fft' in k.lower())
    L.append('  ▶ Q3 `*fft*` 族占比 = **%.1f%%**（旧剖析是 2.4%%）⇒ %s'
             % (100 * fft_t / tot,
                '✅ 复现"FFT 不是瓶颈"' if 100 * fft_t / tot < 10 else
                '⚠ **与旧结论不符，要更正**'))
    has_adv = any('advance' in k for k in fam)
    L.append('  ▶ Q4 正对照（剖析里必须看到 `advance`）：%s'
             % ('✅ PASS' if has_adv else '❌ FAIL ⇒ 量到的是别的东西'))

    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r559_profile.log'), 'w') as fh:
        fh.write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
