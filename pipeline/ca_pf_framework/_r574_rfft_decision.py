#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r574_rfft_decision.py --- "rfft 要不要进生产"的**决策量具**。

## 为什么不能让单步墙钟说了算
单步墙钟 run-to-run 抖动 ~10%（`_r572` 三次测同一 BEFORE 得 0.2653/0.2980/0.3275）。
⇒ 本量具用**交错轮次**（A,B,C,A,B,C,…）消除机器漂移，取**配对差**而不是绝对值。

## 三个臂
  A = loop / full / c2c        （归档旧路）
  B = einsum / gather / c2c    （**逐位相同**的那一档）
  C = einsum / gather / rfft   （加实数 FFT）

## 判据
* **D1 边际提速**：C 相对 B 的配对中位数（**这才是"rfft 值多少"**）
* **D2 启停代价**：建引擎耗时 c2c vs rfft
* **D3 确定性**：`rfftn(workers=4)` 连跑两次**逐位**相同？（并行 FFT 是否确定）
* **D4 内存**：`Λ`、谱数组、`_wmask` 的实际字节
* **D5 等价性复核**：σ 与 `E_el` 的相对差（须 ≤1e-13）
* **D6 C5 影响**：用内存定律 `a·nv·N³ + c·N³` **推算**新 `nv_max`
  （⚠ **推算，未实测** —— 标出来，不许当成实测数）
* **D7 负对照**：给 rfft 臂关掉 Nyquist 修正，D5 必须**大**（否则 D5 没分辨力）
"""
import os
import sys
import time

import numpy as np
from scipy import fft as sfft

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                    # noqa: E402
import windowB_pf3d as P3                                      # noqa: E402
from T16_verify_rve import C, EPS0                             # noqa: E402

N = int(os.environ.get('R574_N', '64'))
NV = int(os.environ.get('R574_NV', '24'))
DX_UM = float(os.environ.get('R574_DX', '0.0625'))
WORKERS = int(os.environ.get('R574_WORKERS', '4'))
ROUNDS = int(os.environ.get('R574_ROUNDS', '5'))
STEPS_PER_ROUND = int(os.environ.get('R574_STEPS', '3'))
LOG = []


def A(s):
    LOG.append(s)
    print(s, flush=True)


def rel(a, b):
    a = np.asarray(a)
    b = np.asarray(b)
    return float(np.max(np.abs(a - b))) / max(float(np.max(np.abs(b))), 1e-300)


A('=' * 96)
A('R574 — rfft 进不进生产？（N=%d nv=%d workers=%d 交错 %d 轮 × %d 步）'
  % (N, NV, WORKERS, ROUNDS, STEPS_PER_ROUND))
A('=' * 96)


def build(fft_mode='c2c', eps0='einsum', edpair='gather'):
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(NV)]
    t0 = time.perf_counter()
    g = W.LevelSetMulti(N, N * DX_UM, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] + [3.0e8] * NV, workers=WORKERS,
                        reinit_every=20, reinit_dt=1e-4, reinit_band_cells=6.0,
                        phi_prec='f64', fft_mode=fft_mode,
                        eps0_mode=eps0, ed_pair_mode=edpair)
    t_build = time.perf_counter() - t0
    g.init_parent()
    rng = np.random.default_rng(7)
    nrm = np.array([0.0, 0.0, 1.0])
    Lc = N * DX_UM
    for k in range(1, max(2, NV // 4) + 1):
        g.seed_plate(k, rng.random(3) * (Lc * 0.6) + Lc * 0.2, nrm, 120e-9, 300e-9)
    g.advance(dt=1e-8)                                  # 预热
    return g, t_build


ARMS = [('A loop/full/c2c', dict(fft_mode='c2c', eps0='loop', edpair='full')),
        ('B einsum/gather/c2c', dict(fft_mode='c2c', eps0='einsum', edpair='gather')),
        ('C einsum/gather/rfft', dict(fft_mode='rfft', eps0='einsum', edpair='gather'))]

# ---------------- D2 启停代价 ----------------
A('')
A('  ── D2 建引擎耗时（含 Nyquist 修正那一次额外 `lambda_packed`）──')
gs, tbs = [], {}
for nm, kw in ARMS:
    g, tb = build(**kw)
    gs.append(g)
    tbs[nm] = tb
    A('      %-22s %.3f s' % (nm, tb))
A('      c2c → rfft 的建表差 = %+.3f s（rfft 多算一次 Nyquist 子集）'
  % (tbs[ARMS[2][0]] - tbs[ARMS[1][0]]))

# ---------------- D1 交错配对计时 ----------------
A('')
A('  ── D1 交错配对计时（每轮每臂 %d 步，消机器漂移）──' % STEPS_PER_ROUND)
per = {nm: [] for nm, _ in ARMS}
for r in range(ROUNDS):
    for (nm, _), g in zip(ARMS, gs):
        t0 = time.perf_counter()
        for _ in range(STEPS_PER_ROUND):
            g.advance(dt=1e-8)
        per[nm].append((time.perf_counter() - t0) / STEPS_PER_ROUND)
med = {nm: float(np.median(v)) for nm, v in per.items()}
for nm, _ in ARMS:
    A('      %-22s 中位 = %.4f s/步   （各轮：%s）'
      % (nm, med[nm], ' '.join('%.3f' % x for x in per[nm])))
d_BA = med[ARMS[1][0]] / med[ARMS[0][0]]
d_CB = med[ARMS[2][0]] / med[ARMS[1][0]]
d_CA = med[ARMS[2][0]] / med[ARMS[0][0]]
A('')
A('      **A→B（逐位档）**      = %.4f / %.4f = **%.3f×**'
  % (med[ARMS[0][0]], med[ARMS[1][0]], 1 / d_BA))
A('      **B→C（rfft 的边际）**  = %.4f / %.4f = **%.3f×**  ← 这才是"rfft 值多少"'
  % (med[ARMS[1][0]], med[ARMS[2][0]], 1 / d_CB))
A('      **A→C（全开）**        = **%.3f×**' % (1 / d_CA))
_pd = [(b - c) / b for b, c in zip(per[ARMS[1][0]], per[ARMS[2][0]])]
A('      逐轮配对差 (B−C)/B：%s ⇒ 中位 **%.1f%%**'
  % (' '.join('%.1f%%' % (100 * x) for x in _pd), 100 * float(np.median(_pd))))

# ---------------- D3 确定性 ----------------
A('')
A('  ── D3 `rfftn(workers=%d)` 确定性 ──' % WORKERS)
e6 = np.ascontiguousarray(np.random.default_rng(1).normal(size=(6, N, N, N)))
r1 = sfft.rfftn(e6, axes=(1, 2, 3), workers=WORKERS)
r2 = sfft.rfftn(e6, axes=(1, 2, 3), workers=WORKERS)
A('      连跑两次逐位相同：%s' % ('✅ 是' if np.array_equal(r1, r2) else '❌ 否'))
_n1 = sfft.irfftn(r1, axes=(1, 2, 3), s=(N, N, N), workers=WORKERS)
_n2 = sfft.irfftn(r1, axes=(1, 2, 3), s=(N, N, N), workers=WORKERS)
A('      `irfftn` 连跑两次逐位相同：%s' % ('✅ 是' if np.array_equal(_n1, _n2) else '❌ 否'))
A('      半轴 = 最后一个轴？实测 rfftn 出形 %s（应为 (6,%d,%d,%d)）'
  % (r1.shape, N, N, N // 2 + 1))

# ---------------- D4 内存 ----------------
A('')
A('  ── D4 内存（N=%d，单位 B/胞 = 字节/(N³)）──' % N)
gc, gr = gs[1], gs[2]
A('      Λ   常驻：c2c %s %.1f MB (%.0f B/胞)  →  rfft %s %.1f MB (%.0f B/胞)'
  % (gc.pf.Lam.shape, gc.pf.Lam.nbytes / 2 ** 20,
     gc.pf.Lam.nbytes / N ** 3, gr.pf.Lam.shape, gr.pf.Lam.nbytes / 2 ** 20,
     gr.pf.Lam.nbytes / N ** 3))
A('      _wmask    ：%.2f MB (%.2f B/胞)'
  % (gr.pf._wmask.nbytes / 2 ** 20, gr.pf._wmask.nbytes / N ** 3))
_n3 = N ** 3
A('      σ 链瞬时：Eh+sh 全谱 %.0f MB → 半谱 %.0f MB（各 (6,M)c128）'
  % (2 * 6 * _n3 * 16 / 2 ** 20, 2 * 6 * _n3 * (N // 2 + 1) / N * 16 / 2 ** 20))

# ---------------- D5 等价性 + D7 负对照 ----------------
A('')
A('  ── D5 等价性（σ 与 E_el）──')
_karr, _larr = gc.par.argmin2(gc.phi)
for g in gs:
    pass
_sB = gs[1].pf.sigma_tensor(None)
_sC = gs[2].pf.sigma_tensor(None)
A('      σ   ：B vs C  max|Δ|/max = %.3e   %s'
  % (rel(_sC, _sB), '✅ ≤1e-13' if rel(_sC, _sB) <= 1e-13 else '❌'))
_LB = gs[1].pf.E_el()
_LC = gs[2].pf.E_el()
A('      E_el：B = %.8e  C = %.8e  相对差 = %.3e   %s'
  % (_LB, _LC, abs(_LC - _LB) / abs(_LB),
     '✅ ≤1e-12' if abs(_LC - _LB) / abs(_LB) <= 1e-12 else '❌'))
# D7 负对照：临时把 rfft 的 Λ 换成**未做 Nyquist 平均**的
_Lbak = gs[2].pf.Lam
_kv = 2 * np.pi * np.fft.fftfreq(N, d=gs[2].pf.dx)
_Kh = np.stack(np.meshgrid(_kv, _kv, _kv[:N // 2 + 1], indexing='ij'),
               -1).reshape(-1, 3)
gs[2].pf.Lam = np.asarray(P3.lambda_packed(C, _Kh, k0_mode='free'))
_d_ng = rel(gs[2].pf.sigma_tensor(None), _sB)
gs[2].pf.Lam = _Lbak
A('      [D7 负对照] 关掉 Nyquist 修正：max|Δ|/max = %.3e   %s'
  % (_d_ng, '✅ 有分辨力' if _d_ng > 1e-3 else '❌ D5 没分辨力'))

# ---------------- D6 C5 影响（推算） ----------------
A('')
A('  ── D6 对 C5（填满 10 µm 盒）的影响 —— ⚠ **推算，未实测** ──')
A('      内存定律（`R550` 修正后，实测）：数组合计(MB) = a·nv·N³/2²⁰ + c·N³/2²⁰')
A('        f64: a=16.0   f32: a=12.0    c=311.8（其中 ~94%% 是 `pf.Lam` = 288 B/胞）')
A('      标定预算：N=160 时 f64 nv_max=359、f32 nv_max=478 ⇒ 隐含预算 ≈ 23.1 GiB')
_n3m = (160 ** 3) / 2 ** 20
for tag, a_, c_ in (('f64', 16.0, 311.8), ('f32', 12.0, 311.8)):
    nv0 = (23655.5 - c_ * _n3m) / (a_ * _n3m)
    c2 = c_ - 144.0                       # Λ 288 → 144 B/胞
    nv1 = (23655.5 - c2 * _n3m) / (a_ * _n3m)
    A('      %s：c 311.8 → %.1f B/胞 ⇒ nv_max %.0f → **%.0f**（**%+.1f%%**）'
      % (tag, c2, nv0, nv1, 100 * (nv1 / nv0 - 1)))
A('      ⇒ **内存侧只值 +2.5%% 左右的 nv 上限** —— 我上一份报告写"直接缓解 C5 内存墙"')
A('         是**夸大的**，正确说法是"省 ~0.6 GB/有限提升上限"。')
A('      ⚠ 真正的新 `nv_max` 必须用 `_r550`/`_r553` 式量具**重测**，本段只是量级估算。')

out = '\n'.join(LOG)
with open(os.path.join(HERE, '_w2_r574_rfft.log'), 'w', encoding='utf-8') as fh:
    fh.write(out + '\n')
