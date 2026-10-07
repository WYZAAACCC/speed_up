#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r566_b4iso.py --- 把 `_r562` B4 的 **6.33e-2 差异**逐段隔离。

`_r562` B4 里"新的 sigma 整链"与旧的差 `max|Δ|/max|ref| = 6.33e-2`
—— 而 B3 已证明 `rfftn`/`irfftn` 本身只差 3e-16。⇒ 差异一定出在别处。
本脚本按**五个可判定的中间量**逐段钉：
  C1 `Kh` 与 `pf.K` 的半子集**逐位**相同吗？
  C2 `LamH` 与 `Lam` 的半子集**逐位**相同吗？
  C3 `rfftn(e)` 与 `fftn(e)[..., :half]` 差多少？
  C4 用**同一个** `sh_half`，`irfftn` 与 `real(ifftn(sh_full))` 差多少？
  C5 einsum 两种布局（(M,6,6) vs (6,6,M)）在半谱上差多少？
  最后用两个 mid 链（只换 FFT / 只换 Lam 来源）定位整链差异来源。
每段都配**负对照**（必须大），否则该段无分辨力。
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
LOG = []


def A(s):
    LOG.append(s)
    print(s, flush=True)


def rel(a, b):
    a = np.asarray(a)
    b = np.asarray(b)
    return float(np.max(np.abs(a - b))) / max(float(np.max(np.abs(b))), 1e-300)


A('=' * 96)
A('R566 — 隔离 `_r562` B4 的 6.33e-2（N=%d nv=%d）' % (N, NV))
A('=' * 96)
C = C_iso3(113e9, 0.34)
rng = np.random.default_rng(11)
eps0 = np.stack([np.linalg.qr(rng.normal(size=(3, 3)))[0] * 0.01 for _ in range(NV)])
pf = PF3D(N, BOX, C, eps0, gamma=0.1, w90=0.02, Lmob=1.0, workers=W,
          k0_mode='free')

kv = 2 * np.pi * np.fft.fftfreq(N, d=pf.dx)
Kh = np.stack(np.meshgrid(kv, kv, kv[:half], indexing='ij'), -1).reshape(-1, 3)
f = np.arange(N * N * half)
i_ = f // (N * half)
r_ = f % (N * half)
j_ = r_ // half
k_ = r_ % half
idx_full = i_ * N * N + j_ * N + k_

A('')
A('  C1 k 网格映射：Kh 与 pf.K[idx_full]')
d1 = float(np.max(np.abs(Kh - pf.K[idx_full])))
A('      max|Δk| = %.3e   %s' % (d1, '✅' if d1 == 0.0 else '❌'))
A('      [NG] 用错的映射（末轴不截断）：max|Δk| = %.3e'
  % float(np.max(np.abs(Kh - pf.K[f]))))

LamH = np.asarray(lambda_packed(C, Kh, k0_mode='free'))
LamF = np.asarray(pf.Lam)
d2 = rel(LamH, LamF[idx_full])
A('')
A('  C2 Lam 半谱 vs 全谱子集：max|Δ|/max = %.3e   %s'
  % (d2, '✅ 逐位相同' if d2 == 0.0 else '❌ **这就是整链差异的来源**'))
A('      [NG] 用错的映射：max|Δ|/max = %.3e' % rel(LamH, LamF[f]))
A('      Lam 是否 k→−k 偶：max|Δ|/max = %.3e' % rel(LamH[::-1], LamH))
A('      Lam 是否 6×6 对称：max|Δ|/max = %.3e'
  % rel(np.swapaxes(LamH, 1, 2), LamH))

e0v = np.ascontiguousarray(pf.e0v)
ph = (rng.random((NV, N, N, N)) > 0.6).astype(np.float64)
X = np.arange(N)[None, None, :]
soft = 0.5 * (1.0 - np.tanh((X - N * 0.5) / 1.5))
phi2 = np.ascontiguousarray(ph * soft[None])


def build_e(mode):
    if mode == 'loop':
        e = np.zeros((6, N, N, N))
        for p in range(6):
            for v in range(NV):
                e[p] += e0v[v, p] * phi2[v]
    else:
        e = (e0v.T @ phi2.reshape(NV, -1)).reshape(6, N, N, N)
    e[3:] *= 2.0
    return e


e_loop = build_e('loop')
e_gemm = build_e('gemm')
A('')
A('  e 场：loop vs gemm  max|Δ|/max = %.3e' % rel(e_gemm, e_loop))

sh_full_in = sfft.fftn(e_loop, axes=(1, 2, 3), workers=W)
sh_half_in = sfft.rfftn(e_loop, axes=(1, 2, 3), workers=W)
d3 = rel(sh_half_in, sh_full_in[..., :half])
A('')
A('  C3 rfftn vs fftn[..., :half]：max|Δ|/max = %.3e   %s'
  % (d3, '✅' if d3 < 1e-14 else '❌'))
A('      [NG] k 轴错位一格：max|Δ|/max = %.3e'
  % rel(sh_half_in, np.roll(sh_half_in, 1, axis=3)))
_bf = sfft.ifftn(sh_full_in, axes=(1, 2, 3), workers=W)
A('      sh_full 的 ifftn 虚部残差 ‖Im‖/‖·‖ = %.3e  ⇒ Hermite 自洽性'
  % (float(np.max(np.abs(np.imag(_bf)))) / float(np.max(np.abs(_bf)))))

# ---- C3b: **决定性判据** —— Λ 与 sh 到底 Hermite 不 Hermite ----
Ef_full = sh_full_in.reshape(6, -1)
sh_full_prod = -np.einsum('kpq,qk->pk', LamF, Ef_full)


def mirror(idx):
    ii = (idx // (N * N)) % N
    jj = (idx // N) % N
    kk = idx % N
    return (((-ii) % N) * N * N + ((-jj) % N) * N + ((-kk) % N))


mir = mirror(np.arange(N ** 3))
A('')
A('  C3b Hermite 判据（这才是真正的嫌疑）')
A('      e 的谱 Eh(-k) vs conj(Eh(k))：max|Δ|/max = %.3e'
  % rel(Ef_full[:, mir], np.conj(Ef_full)))
A('      Λ(-k) vs Λ(k)：max|Δ|/max = %.3e  ⚠ 注意：含 Nyquist 分量的 k 在网格上'
  ' **没有** −k（kv[32]=−0.5 的负是 +0.5，不在格点上）⇒ 这些点会被误判',)
_mir_ok = np.ones(N ** 3, dtype=bool)
for _ax in range(3):
    _m = (np.arange(N ** 3) // (N ** _ax)) % N
    _mir_ok &= (_m != N // 2)
A('        只在"无 Nyquist 分量"的 %d/%d 个 k 上判：max|Δ|/max = %.3e   %s'
  % (int(_mir_ok.sum()), N ** 3, rel(LamF[mir][_mir_ok], LamF[_mir_ok]),
     '✅ Λ 是 k→−k 偶（与理论一致）'
     if rel(LamF[mir][_mir_ok], LamF[_mir_ok]) < 1e-14 else '❌'))
A('        **完整判据**：K[mir] == −K（无 Nyquist 分量的那些点）'
  '  max|Δ| = %.3e'
  % float(np.max(np.abs(pf.K[mir][_mir_ok] + pf.K[_mir_ok]))))
A('      sh(-k) vs conj(sh(k))（同样只在无 Nyquist 的点上判）：max|Δ|/max = %.3e'
  % rel(sh_full_prod[:, mir][:, _mir_ok], np.conj(sh_full_prod[:, _mir_ok])))
A('      [NG] sh 与自身 conj（不做镜像）：max|Δ|/max = %.3e'
  % rel(np.conj(sh_full_prod), sh_full_prod))

back_half = sfft.irfftn(sh_half_in, axes=(1, 2, 3), s=(N, N, N), workers=W)
back_full = np.real(sfft.ifftn(sh_full_in, axes=(1, 2, 3), workers=W))
d4 = rel(back_half, back_full)
A('')
A('  C4 irfftn(sh_half) vs real(ifftn(sh_full))：max|Δ|/max = %.3e   %s'
  % (d4, '✅' if d4 < 1e-14 else '❌'))
A('      [NG] 漏掉 s= 归一化：max|Δ|/max = %.3e' % rel(back_half, back_full * N))

LamHT = np.ascontiguousarray(np.transpose(LamH, (1, 2, 0)))
EhH = np.ascontiguousarray(sh_half_in.reshape(6, -1))
sA = -np.einsum('kpq,qk->pk', LamH, EhH)
sB = -np.einsum('pqk,qk->pk', LamHT, EhH)
A('')
A('  C5 einsum 布局（半谱）：(M,6,6) vs (6,6,M)  max|Δ|/max = %.3e   %s'
  % (rel(sB, sA), '✅' if rel(sB, sA) < 1e-15 else '❌'))
A('      [NG] Lam 转置后再反序 k：max|Δ|/max = %.3e'
  % rel(-np.einsum('pqk,qk->pk', LamHT[:, :, ::-1], EhH), sA))

A('')
A('  ── 整链复现（应当复现 _r562 的 6.33e-2）──')


def old_chain():
    e = build_e('loop')
    Eh_ = sfft.fftn(e, axes=(1, 2, 3), workers=W).reshape(6, -1)
    sh = -np.einsum('kpq,qk->pk', LamF, Eh_)
    return np.real(sfft.ifftn(sh.reshape((6, N, N, N)), axes=(1, 2, 3), workers=W))


def new_chain():
    e = build_e('gemm')
    Eh_ = sfft.rfftn(e, axes=(1, 2, 3), workers=W).reshape(6, -1)
    sh = -np.einsum('pqk,qk->pk', LamHT, Eh_)
    return sfft.irfftn(sh.reshape((6, N, N, half)), axes=(1, 2, 3),
                       s=(N, N, N), workers=W)


def mid_fft_only():
    e = build_e('gemm')
    Eh_ = sfft.rfftn(e, axes=(1, 2, 3), workers=W).reshape(6, -1)
    sh = -np.einsum('pqk,qk->pk',
                    np.ascontiguousarray(np.transpose(LamF[idx_full], (1, 2, 0))),
                    Eh_)
    return sfft.irfftn(sh.reshape((6, N, N, half)), axes=(1, 2, 3),
                       s=(N, N, N), workers=W)


def mid_lamH_c2c():
    """只换 Lam 的来源（LamH），FFT 仍用 c2c 全谱。"""
    e = build_e('loop')
    Ef = sfft.fftn(e, axes=(1, 2, 3), workers=W).reshape(6, -1)
    shH = -np.einsum('pqk,qk->pk', LamHT, Ef[:, idx_full])
    sh = -np.einsum('kpq,qk->pk', LamF, Ef)
    sh[:, idx_full] = shH
    return np.real(sfft.ifftn(sh.reshape((6, N, N, N)), axes=(1, 2, 3), workers=W))


r_old = old_chain()
for nm, fn in (('new_chain', new_chain),
               ('mid: 只换FFT+GEMM', mid_fft_only),
               ('mid: 只换Lam来源', mid_lamH_c2c)):
    A('      %-22s max|Δ|/max|old| = %.3e' % (nm, rel(fn(), r_old)))
A('      [NG] old 乘 1.01          max|Δ|/max|old| = %.3e'
  % rel(r_old * 1.01, r_old))

# ---- ★★ 决定性判据：同一个 sh，只换最后的逆变换 ----
A('')
A('  ── C6 **决定性**：同一个 sh（全谱、Hermite），两种逆变换 ──')
_sh3 = sh_full_prod.reshape(6, N, N, N)
_ih = sfft.irfftn(_sh3[..., :half], axes=(1, 2, 3), s=(N, N, N), workers=W)
_if = np.real(sfft.ifftn(_sh3, axes=(1, 2, 3), workers=W))
A('      irfftn(sh[..., :half]) vs real(ifftn(sh))：max|Δ|/max = %.3e   %s'
  % (rel(_ih, _if), '✅ 等价' if rel(_ih, _if) < 1e-13 else
     '❌ **不等价 —— 这才是 6.33e-2 的真因**'))
A('      ⚠ 记账：`sh` 在"最后一轴"上**并不** Hermite 自洽（3D Hermite 是把'
  ' 三个轴一起翻转的），只有 **Nyquist 面**（m=32）的虚部会被 irfftn 特殊对待。')
A('      sh[..., 0, :]  的虚部/模：%.3e'
  % (float(np.max(np.abs(np.imag(_sh3[..., 0, :]))))
     / float(np.max(np.abs(_sh3)))))
A('      sh[...,32, :]  的虚部/模：%.3e   ← Nyquist 面'
  % (float(np.max(np.abs(np.imag(_sh3[..., 32, :]))))
     / float(np.max(np.abs(_sh3)))))
A('      把 sh 的 Nyquist 面强行取实后，两种逆变换之差 = %.3e'
  % rel(sfft.irfftn(_sh3[..., :half], axes=(1, 2, 3), s=(N, N, N), workers=W),
        np.real(sfft.ifftn(np.concatenate(
            [_sh3[..., :32], np.real(_sh3[..., 32:33]),
             np.conj(_sh3[..., 32:0:-1])], axis=-1).reshape(6, N, N, N),
            axes=(1, 2, 3), workers=W))))
A('      [NG] 把 sh 的 k=0 面清零：max|Δ|/max = %.3e'
  % rel(_if, np.real(sfft.ifftn(
      np.concatenate([np.zeros((6, N, N, 1), dtype=complex), _sh3[..., 1:]],
                     axis=-1), axes=(1, 2, 3), workers=W))))
A('')
A('  σ 量级： max|σ_old| = %.4e   mean|σ_old| = %.4e   min|σ_old| = %.4e'
  % (np.max(np.abs(r_old)), np.mean(np.abs(r_old)), np.min(np.abs(r_old))))
A('  σ 的 k=0 分量： mean(σ) = %.4e （= max 的 %.1f%%）'
  % (float(np.mean(r_old)), 100 * abs(float(np.mean(r_old)))
     / float(np.max(np.abs(r_old)))))

out = '\n'.join(LOG)
with open(os.path.join(HERE, '_w2_r566_b4iso.log'), 'w', encoding='utf-8') as fh:
    fh.write(out + '\n')
