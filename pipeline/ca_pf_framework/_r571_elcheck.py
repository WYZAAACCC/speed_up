#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r571_elcheck.py --- 把 `E_el()` 半谱求和的**配对权重**直接量出来。

`_r570` 冒烟在真实路径上抓到 `E_el_J` 差 37.7%（加了权重后 9.4%）。
本脚本不猜，直接把每-k 的被加项 `q(k) = Re(conj(ε(k)):Λ:ε(k))` 摊开：
  E1  `Σ_full q`（c2c，全谱 Λ）—— 真值
  E2  `Σ_half q`（rfft，半谱 Λ_eff）
  E3  `q_half[k]` 与 `q_full[k]` 在半谱位置上是否逐点相同
  E4  k→−k 的对称残差 `max|q_full − q_full[mirror]|`
  E5  按"另一半 = 镜像"重算权重：`w=1` 当 `m∈{0, N/2}`，否则 2
  E6  更一般的权重：`w=1` 当 mirror(k) 仍在半谱里（即 m==N/2）
"""
import os
import sys

import numpy as np
from scipy import fft as sfft

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from windowB_pf3d import PF3D, C_iso3   # noqa: E402

N, NV = 32, 6
half = N // 2 + 1
LOG = []


def A(s):
    LOG.append(s)
    print(s, flush=True)


A('=' * 92)
A('R571 — `E_el()` 半谱配对权重直测（N=%d nv=%d）' % (N, NV))
A('=' * 92)
C = C_iso3(113e9, 0.34)
rng = np.random.default_rng(3)
eps0 = np.stack([np.linalg.qr(rng.normal(size=(3, 3)))[0] * 0.01 for _ in range(NV)])

pf_c = PF3D(N, 1.0, C, eps0, gamma=0.1, w90=0.02, Lmob=1.0, workers=4,
            k0_mode='free', fft_mode='c2c')
pf_r = PF3D(N, 1.0, C, eps0, gamma=0.1, w90=0.02, Lmob=1.0, workers=4,
            k0_mode='free', fft_mode='rfft')

ph = (rng.random((NV, N, N, N)) > 0.6).astype(float)
for v in range(NV):
    pf_c.phi[v] = ph[v]
    pf_r.phi[v] = ph[v]

Eh_full = pf_c._epsh().reshape(6, -1) / pf_c.N3
Eh_half = np.ascontiguousarray(pf_r._epsh_r()).reshape(6, -1) / pf_r.N3
q_full = np.real(np.einsum('pk,kpq,qk->k', np.conj(Eh_full), pf_c.Lam, Eh_full))
q_half = np.real(np.einsum('pk,kpq,qk->k', np.conj(Eh_half), pf_r.Lam, Eh_half))

# 半谱扁平索引 → 全谱扁平索引
f = np.arange(N * N * half)
i_ = f // (N * half)
r_ = f % (N * half)
j_ = r_ // half
m_ = r_ % half
idx_full = i_ * N * N + j_ * N + m_
mir_full = (((N - i_) % N) * N + ((N - j_) % N)) * N + ((N - m_) % N)
# 镜像点在全谱里的扁平索引 → 它是否落在半谱里（m <= N//2）
mir_in_half = ((N - m_) % N) <= (N // 2)

S_full = float(q_full.sum())
S_half = float(q_half.sum())
A('')
A('  E1  Σ_full q（c2c 真值）      = %.8e' % S_full)
A('  E2  Σ_half q（rfft）          = %.8e   比值 = %.6f'
  % (S_half, S_half / S_full))
A('  E3  q_half vs q_full（半谱位置）max|Δ|/max|q| = %.3e   %s'
  % (float(np.max(np.abs(q_half - q_full[idx_full])))
     / float(np.max(np.abs(q_full))),
     '✅ 逐点相同' if np.allclose(q_half, q_full[idx_full], rtol=0, atol=0)
     else '（有差）'))
A('  E4  q 的 k→−k 对称残差（半谱点上）max|q_half−q_full[mirror]|/max|q| = %.3e'
  % (float(np.max(np.abs(q_half - q_full[mir_full])))
     / float(np.max(np.abs(q_full)))))
A('  E5  半谱里 mirror 也落在半谱内的点数 = %d / %d（条件 m==N/2：%d）'
  % (int(mir_in_half.sum()), q_half.size, int((m_ == N // 2).sum())))
A('      （非镜像半边的点数 = %d，应等于 Σ_{m=N/2+1..N-1} N² = %d）'
  % (int((~mir_in_half).sum()), (N - half) * N * N))

# ---- ★ 正确配方：`q` 必须用**未做 Nyquist 平均**的 Λ_true ----
from windowB_pf3d import lambda_packed                     # noqa: E402
kv = 2 * np.pi * np.fft.fftfreq(N, d=pf_c.dx)
Kh = np.stack(np.meshgrid(kv, kv, kv[:half], indexing='ij'),
              -1).reshape(-1, 3)
Lam_true = np.asarray(lambda_packed(C, Kh, k0_mode='free'))
q_true = np.real(np.einsum('pk,kpq,qk->k', np.conj(Eh_half), Lam_true, Eh_half))
A('')
A('  E6  Λ_true vs Λ_eff 在半谱上：max|ΔΛ|/max|Λ| = %.3e（只应在 Nyquist 面 ≠0）'
  % (float(np.max(np.abs(Lam_true - pf_r.Lam)))
     / float(np.max(np.abs(Lam_true)))))
_nyq = (i_ == N // 2) | (j_ == N // 2) | (m_ == N // 2)
A('      非 Nyquist 面上：max|ΔΛ|/max|Λ| = %.3e   %s'
  % (float(np.max(np.abs(Lam_true[~_nyq] - pf_r.Lam[~_nyq])))
     / float(np.max(np.abs(Lam_true))),
     '✅ 逐位 0' if np.array_equal(Lam_true[~_nyq], pf_r.Lam[~_nyq]) else '⚠'))
A('  E7  q_true vs q_full（半谱位置）max|Δ|/max|q| = %.3e   %s'
  % (float(np.max(np.abs(q_true - q_full[idx_full])))
     / float(np.max(np.abs(q_full))),
     '✅ 逐点相同' if np.allclose(q_true, q_full[idx_full], rtol=1e-13, atol=0)
     else '❌'))
A('')
A('  ── 用不同权重重建 Σ_full（**用 q_true**）──')
_cands = [('w=2 全体', np.full(q_half.size, 2.0)),
          ('w=1 当 i/j/m 任一 =N/2',
           np.where((i_ == N // 2) | (j_ == N // 2) | (m_ == N // 2), 1.0, 2.0)),
          ('w=1 当 m==N/2', np.where(m_ == N // 2, 1.0, 2.0)),
          ('**w=1 当 m∈{0,N/2}**（推导值）',
           np.where((m_ == 0) | (m_ == N // 2), 1.0, 2.0)),
          ('w=1 当 mirror 仍在半谱（=m==N/2）', np.where(mir_in_half, 1.0, 2.0))]
for nm, w in _cands:
    est = float((w * q_true).sum())
    A('      %-36s Σ/Σ_full = %.8f   %s'
      % (nm, est / S_full, '✅' if abs(est / S_full - 1.0) < 1e-12 else ''))
A('')
A('  ── 反面对照：如果用 Λ_eff 的 q（错的那个）配推导权重 ──')
_w = np.where((m_ == 0) | (m_ == N // 2), 1.0, 2.0)
A('      Σ_half w·q_eff / Σ_full = %.8f   ← 应当 **≠ 1**（证明 q 必须用 Λ_true）'
  % (float((_w * q_half).sum()) / S_full))
out = '\n'.join(LOG)
with open(os.path.join(HERE, '_w2_r571_elcheck.log'), 'w', encoding='utf-8') as fh:
    fh.write(out + '\n')
