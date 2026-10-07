#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r567_nyqfix.py --- 让"实数 FFT"这条路**逐位等价**于旧的 c2c 路。

## 机理（`_r566` 已判定，这里再复现一次）
`sig = real(ifftn(-Λ ⊙ fftn(e)))`，而 `real(ifftn(X)) = ifftn(Herm(X))`
—— **旧代码一直在隐式地做 Hermite 投影**。
`sh = -Λ⊙Eh` 在**三个 Nyquist 面**（i=N/2、j=N/2、m=N/2）上**不是 Hermite 的**：
在那三面上，索引镜像 `mir3: i→(N−i)%N` 得到的 k **向量**不是 `−κ`
（因为 `kv[N/2] = −π/dx`，它的负 `+π/dx` 不在格点上）⇒ `Λ(κ(mir3 k)) ≠ Λ(κ(k))`。
而 `irfftn(sh[..., :half])` 用的是**未投影**的半谱 ⇒ 与旧结果差 **6.33e-2**。

## 精确修法（**零额外运行时代价**）
    H[k] = ½(sh[k] + conj(sh[mir3 k])) ,  sh[mir3 k] = −Λ(κ(mir3 k))·conj(Eh[k])
    ⇒ H = −½(Λ(κ) + Λ(κ(mir3))) ⊙ Eh
而在**非** Nyquist 面上 `κ(mir3 k) = −κ(k)` ⇒ `Λ(κ(mir3)) = Λ(κ)`（已证）
⇒ **只需在那三面上改 Λ**：
    Λ_eff = Λ(κ)                                    （非 Nyquist）
    Λ_eff = ½[Λ(κ) + Λ(κ(mir3))]                    （Nyquist 面）
则 `irfftn(−Λ_eff ⊙ rfftn(e)) ≡ real(ifftn(−Λ ⊙ fftn(e)))`（到舍入）。
**Λ_eff 在建引擎时算一次** ⇒ 热路径一个字节都不多花。

## 判据
* **N1** `irfftn(−Λ_eff ⊙ rfftn(e))` vs 旧路 ≤ 1e-13（相对 max|σ|）
* **N2 负对照** 不做 Nyquist 修正（`Λ_eff = Λ`）必须 **大**（≈6.33e-2）—— 否则本判据没分辨力
* **N3** 修正项只在 3 个面上非零（其余**逐位**为 0）—— 证明代价为零
* **N4** 提速比（整链）
"""
import os
import sys

import numpy as np
from scipy import fft as sfft

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from windowB_pf3d import PF3D, C_iso3, lambda_packed   # noqa: E402

N, NV, W = 64, 24, 4
BOX = 1.0
half = N // 2 + 1
NYQ = N // 2
LOG = []


def A(s):
    LOG.append(s)
    print(s, flush=True)


def rel(a, b):
    a = np.asarray(a)
    b = np.asarray(b)
    return float(np.max(np.abs(a - b))) / max(float(np.max(np.abs(b))), 1e-300)


A('=' * 96)
A('R567 — Nyquist 面 Hermite 修正：让 rfft 路**逐位等价**于 c2c 路')
A('=' * 96)
C = C_iso3(113e9, 0.34)
rng = np.random.default_rng(11)
eps0 = np.stack([np.linalg.qr(rng.normal(size=(3, 3)))[0] * 0.01 for _ in range(NV)])
pf = PF3D(N, BOX, C, eps0, gamma=0.1, w90=0.02, Lmob=1.0, workers=W,
          k0_mode='free')

# ---------- 半谱 k 网格与镜像 ----------
kv = 2 * np.pi * np.fft.fftfreq(N, d=pf.dx)
g = np.stack(np.meshgrid(np.arange(N), np.arange(N), np.arange(half),
                         indexing='ij'), -1).reshape(-1, 3)
Kh = np.stack(np.meshgrid(kv, kv, kv[:half], indexing='ij'), -1).reshape(-1, 3)
Kfull = pf.K.astype(np.float64)

i_, j_, m_ = g[:, 0], g[:, 1], g[:, 2]
mir3_flat = (((N - i_) % N) * N + ((N - j_) % N)) * N + ((N - m_) % N)
Kh_mir = Kfull[mir3_flat]
nyq = (i_ == NYQ) | (j_ == NYQ) | (m_ == NYQ)
A('')
A('  Nyquist 面掩码：%d / %d 个半谱点 = %.2f%%'
  % (int(nyq.sum()), nyq.size // 3, 100.0 * nyq.sum() / (nyq.size // 3)))
A('  非 Nyquist 点上 κ(mir3 k) 是否 == −κ(k)：max|Δ| = %.3e   %s'
  % (float(np.max(np.abs(Kh_mir[~nyq] + Kh[~nyq]))),
     '✅ 逐位（⇒ Λ_mir == Λ，代价为零）'
     if float(np.max(np.abs(Kh_mir[~nyq] + Kh[~nyq]))) == 0.0 else '❌'))
A('  Nyquist 面上 κ(mir3 k) vs −κ(k)：max|Δ| = %.3e   （应当 ≠0，这正是差异来源）'
  % float(np.max(np.abs(Kh_mir[nyq] + Kh[nyq]))))
A('      [NG] 全格点上 κ(mir3 k) vs −κ(k)：max|Δ| = %.3e'
  % float(np.max(np.abs(Kh_mir + Kh))))

Lam = np.asarray(lambda_packed(C, Kh, k0_mode='free'))
Lam_eff = Lam.copy()
_n = int(nyq.sum())
Lam_eff[nyq] = 0.5 * (Lam[nyq] + np.asarray(lambda_packed(C, Kh_mir[nyq],
                                                          k0_mode='free')))
dLam = Lam_eff - Lam
A('')
A('  N3 修正项只在 Nyquist 面非零：非 Nyquist 处 max|ΔΛ|/max|Λ| = %.3e   %s'
  % (rel(Lam_eff[~nyq], Lam[~nyq]),
     '✅ 逐位 0' if rel(Lam_eff[~nyq], Lam[~nyq]) == 0.0 else '❌'))
_mx = float(np.max(np.abs(dLam))) / float(np.max(np.abs(Lam)))
A('     Nyquist 面上 |ΔΛ|/max|Λ| = %.3e（%d 点，占 %.2f%%）'
  % (_mx, _n, 100.0 * _n / Lam.shape[0]))

# ---------- e 场 ----------
e0v = np.ascontiguousarray(pf.e0v)
ph = (rng.random((NV, N, N, N)) > 0.6).astype(np.float64)
X = np.arange(N)[None, None, :]
phi2 = np.ascontiguousarray(ph * 0.5 * (1.0 - np.tanh((X - N * 0.5) / 1.5))[None])
e = np.zeros((6, N, N, N))
for p in range(6):
    for v in range(NV):
        e[p] += e0v[v, p] * phi2[v]
e[3:] *= 2.0


def old_chain():
    Eh_ = sfft.fftn(e, axes=(1, 2, 3), workers=W).reshape(6, -1)
    sh = -np.einsum('kpq,qk->pk', np.asarray(pf.Lam), Eh_)
    return np.real(sfft.ifftn(sh.reshape((6, N, N, N)), axes=(1, 2, 3), workers=W))


def new_chain(LamUse):
    Eh_ = sfft.rfftn(e, axes=(1, 2, 3), workers=W).reshape(6, -1)
    sh = -np.einsum('kpq,qk->pk', LamUse, Eh_)
    return sfft.irfftn(sh.reshape((6, N, N, half)), axes=(1, 2, 3),
                       s=(N, N, N), workers=W)


import time


def bench(fn, rep=9, warm=2):
    for _ in range(warm):
        fn()
    ts = []
    for _ in range(rep):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return float(np.median(ts))


r_old = old_chain()
d_fix = rel(new_chain(Lam_eff), r_old)
d_ng = rel(new_chain(Lam), r_old)
A('')
A('  ── 判据 ──')
A('  N1 `irfftn(−Λ_eff⊙rfftn(e))` vs 旧 c2c 路：max|Δ|/max = %.3e   %s'
  % (d_fix, '✅ PASS' if d_fix < 1e-13 else '❌ FAIL'))
A('  N2 负对照（不做 Nyquist 修正）：max|Δ|/max = %.3e   %s'
  % (d_ng, '✅ 有分辨力（必须大）' if d_ng > 1e-3 else '❌ 判据没分辨力'))
A('  N2b 额外负对照（e 的因子 2 只加一半）：max|Δ|/max = %.3e'
  % rel(new_chain(Lam_eff) * 1.0,
        np.real(sfft.ifftn((-np.einsum('kpq,qk->pk', np.asarray(pf.Lam),
                                       sfft.fftn(e, axes=(1, 2, 3),
                                                 workers=W).reshape(6, -1) * 1.001)
                            ).reshape((6, N, N, N)), axes=(1, 2, 3), workers=W))))
t_o = bench(old_chain)
t_n = bench(lambda: new_chain(Lam_eff))
A('')
A('  N4 整链：旧(c2c,全谱 Λ)=%.4f s   新(rfft,半谱 Λ_eff)=%.4f s   **%.2f×**'
  % (t_o, t_n, t_o / t_n))
_eB = (6 * N ** 3) * 8
A('     谱内存：全谱 (6,N,N,N)complex128 = %.1f MB → 半谱 %.1f MB；'
  'Λ 常驻 %.1f → %.1f MB'
  % (_eB / 2 ** 20, _eB * half / N / 2 ** 20,
     np.asarray(pf.Lam).nbytes / 2 ** 20, Lam.nbytes / 2 ** 20))

out = '\n'.join(LOG)
with open(os.path.join(HERE, '_w2_r567_nyqfix.log'), 'w', encoding='utf-8') as fh:
    fh.write(out + '\n')
