#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r562_opbench.py --- **算子替身擂台**：同一个数学量，多种 numpy 实现，同时量
「正确性差异」与「墙钟」。

## 纪律（本项目最贵的三条教训）
1. **数值等价不能只看"看起来一样"** —— 每个替身都报 `max|Δ|/max|ref|`；
2. **比较器必须能失败** —— 每个擂台配一条**故意写错的负对照**（NG），
   它必须给出**大**差异；若 NG 也"通过"，说明这个比较器没有分辨力，**整台作废**；
3. **只信墙钟，不信推理** —— 用中位数 + 预热，且报告 min/max 抖动。

## 擂台
* B1 `eps0_fields`：`6×nv` 次整场 `+=` vs **BLAS GEMM** vs einsum
* B2 `sigma` 的 einsum 布局：`(M,6,6)` vs `(6,6,M)` vs 手工展开 vs optimize=True
* B3 实数 FFT：`fftn/ifftn`(c2c) vs `rfftn/irfftn`
* B4 `sigma_tensor` 整链：旧 vs 新（rfft + 转置布局）
* B5 `elastic_driving_pair` 的 soft 读出：全体 `(nreg,N³)`+nreg 次 einsum vs gather 两个
* B6 `np.gradient` vs 手工切片中心差分
* B7 `sfft` 的 `workers` 扫（决定 FFT 线程数）
"""
import os
import sys
import time

import numpy as np
from scipy import fft as sfft

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from windowB_pf3d import PF3D, C_iso3, lambda_packed   # noqa: E402

N = int(os.environ.get('R562_N', '64'))
NV = int(os.environ.get('R562_NV', '24'))
REP = int(os.environ.get('R562_REP', '7'))
WORKERS = int(os.environ.get('R562_WORKERS', '4'))

OUT = []


def A(s):
    OUT.append(s)
    print(s, flush=True)


def relerr(a, b):
    a = np.asarray(a)
    b = np.asarray(b)
    d = float(np.max(np.abs(a - b))) if a.size else 0.0
    s = float(np.max(np.abs(b))) if b.size else 0.0
    return d / max(s, 1e-300), d


def bench(fn, rep=REP, warm=2):
    for _ in range(warm):
        fn()
    ts = []
    for _ in range(rep):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return float(np.median(ts)), float(np.min(ts)), float(np.max(ts))


def verdict(tag, ref, cand, ng, tol, ok_ng_ratio=1e3):
    """ref/cand/ng 都是 ndarray。判：cand 相对差 ≤ tol；ng 相对差 ≥ ok_ng_ratio×tol。"""
    e_c, d_c = relerr(cand, ref)
    e_n, d_n = relerr(ng, ref)
    good = (e_c <= tol)
    teeth = (e_n >= ok_ng_ratio * max(tol, 1e-16))
    A('      %-26s max|Δ|/max|ref| = %.3e   %s' % (tag, e_c, '✅' if good else '❌'))
    A('      %-26s max|Δ|/max|ref| = %.3e   %s（负对照，必须大）'
      % ('[NG] ' + tag, e_n, '✅ 比较器有分辨力' if teeth else
         '❌❌ 负对照也"通过" ⇒ 比较器没分辨力，本擂台作废'))
    return good, teeth


def main():
    A('=' * 100)
    A('R562 — 算子替身擂台   N=%d nv=%d rep=%d workers=%d' % (N, NV, REP, WORKERS))
    A('=' * 100)
    L = 1.0
    C = C_iso3(113e9, 0.34)
    rng = np.random.default_rng(11)
    eps0 = np.stack([np.linalg.qr(rng.normal(size=(3, 3)))[0] * 0.01
                     for _ in range(NV)])
    pf = PF3D(N, L, C, eps0, gamma=0.1, w90=0.02, Lmob=1.0,
              workers=WORKERS, k0_mode='free')
    A('  C 是实张量 ⇒ Lam 是实数（_lam_cplx=%s）' % pf._lam_cplx)
    # 造一个"生产像"的 phi：分段常数块 + 界面（软剖面）
    ph = rng.random((NV, N, N, N))
    ph = (ph > 0.6).astype(np.float64)
    pf.phi = ph.copy()
    X = np.arange(N)[None, None, :]
    soft = 0.5 * (1.0 - np.tanh((X - N * 0.5) / 1.5))
    pf.phi = pf.phi * soft[None] + (1 - pf.phi) * 0.0

    # =========================================================== B1
    A('')
    A('  ── B1  eps0_fields：6×nv 次整场乘加  vs  BLAS GEMM ──')
    nv = pf.nv
    e0v = np.ascontiguousarray(pf.e0v)                 # (nv,6)
    phi = np.ascontiguousarray(pf.phi)                 # (nv,N,N,N)

    def b1_loop():
        e = np.zeros((6, N, N, N))
        for p in range(6):
            for v in range(nv):
                e[p] += e0v[v, p] * phi[v]
        return e

    def b1_gemm():
        return (e0v.T @ phi.reshape(nv, -1)).reshape(6, N, N, N)

    def b1_einsum():
        return np.einsum('vp,v...->p...', e0v, phi)

    def b1_loop_out():
        e = np.zeros((6, N, N, N))
        tmp = np.empty((N, N, N))
        for p in range(6):
            np.multiply(e0v[0, p], phi[0], out=e[p])
            for v in range(1, nv):
                np.multiply(e0v[v, p], phi[v], out=tmp)
                np.add(e[p], tmp, out=e[p])
        return e

    def b1_ng():
        e = np.zeros((6, N, N, N))
        for p in range(6):
            for v in range(nv - 1):                # 负对照：漏掉最后一个变体
                e[p] += e0v[v, p] * phi[v]
        return e

    r1 = b1_loop()
    t_loop = bench(b1_loop)
    t_gemm = bench(b1_gemm)
    t_ein = bench(b1_einsum)
    t_lo = bench(b1_loop_out)
    ok_g, teeth = verdict('GEMM e0v.T@phi', r1, b1_gemm(), b1_ng(), 1e-14)
    ok_e, _ = verdict('einsum vp,v...->p...', r1, b1_einsum(), b1_ng(), 1e-14)
    ok_o, _ = verdict('loop+out=', r1, b1_loop_out(), b1_ng(), 0.0)
    A('      墙钟： loop=%.4f  gemm=%.4f (%.2f×)  einsum=%.4f (%.2f×)  loop_out=%.4f (%.2f×)'
      % (t_loop[0], t_gemm[0], t_loop[0] / t_gemm[0],
         t_ein[0], t_loop[0] / t_ein[0], t_lo[0], t_loop[0] / t_lo[0]))

    # =========================================================== B2
    A('')
    A('  ── B2  sigma 的 einsum 布局（M=%d 个 k 点）──' % (N ** 3))
    Eh = (rng.normal(size=(6, N ** 3)) + 1j * rng.normal(size=(6, N ** 3)))
    Eh = np.ascontiguousarray(Eh, dtype=np.complex128)
    Lam = np.ascontiguousarray(pf.Lam)                 # (M,6,6) float64
    A('      Lam 布局 %s  %.1f MB   ；Lam 是否 6×6 对称：%s'
      % (Lam.shape, Lam.nbytes / 2 ** 20,
         np.allclose(Lam, np.swapaxes(Lam, 1, 2), rtol=0, atol=1e-12)))
    LamT = np.ascontiguousarray(np.transpose(Lam, (1, 2, 0)))   # (6,6,M)

    def b2_old():
        return -np.einsum('kpq,qk->pk', Lam, Eh)

    def b2_T():
        return -np.einsum('pqk,qk->pk', LamT, Eh)

    def b2_opt():
        return -np.einsum('kpq,qk->pk', Lam, Eh, optimize=True)

    def b2_unroll():
        sh = [None] * 6
        for p in range(6):
            acc = LamT[p, 0] * Eh[0]
            for q in range(1, 6):
                acc = acc + LamT[p, q] * Eh[q]
            sh[p] = -acc
        return np.stack(sh)

    def b2_np():
        # 手工 36 项、写入预分配 out（避免 stack 分配）
        sh = np.empty((6, Eh.shape[1]), dtype=np.complex128)
        tmp = np.empty(Eh.shape[1], dtype=np.complex128)
        for p in range(6):
            np.multiply(LamT[p, 0], Eh[0], out=sh[p])
            for q in range(1, 6):
                np.multiply(LamT[p, q], Eh[q], out=tmp)
                np.add(sh[p], tmp, out=sh[p])
        np.negative(sh, out=sh)
        return sh

    def b2_ng():
        return -np.einsum('kpq,qk->pk', Lam, Eh[:, ::-1])   # 负对照：打乱 k

    r2 = b2_old()
    t_old = bench(b2_old)
    t_T = bench(b2_T)
    t_opt = bench(b2_opt)
    t_un = bench(b2_unroll)
    t_np = bench(b2_np)
    verdict('einsum pqk (Lam 转置)', r2, b2_T(), b2_ng(), 1e-14)
    verdict('einsum optimize=True', r2, b2_opt(), b2_ng(), 1e-14)
    verdict('手工展开(pqk)', r2, b2_unroll(), b2_ng(), 1e-14)
    verdict('手工 multiply/add', r2, b2_np(), b2_ng(), 1e-14)
    A('      墙钟： old(kpq)=%.4f  T(pqk)=%.4f (%.2f×)  optimize=True=%.4f (%.2f×)'
      % (t_old[0], t_T[0], t_old[0] / t_T[0], t_opt[0], t_old[0] / t_opt[0]))
    A('             手工展开=%.4f (%.2f×)  手工mul/add=%.4f (%.2f×)'
      % (t_un[0], t_old[0] / t_un[0], t_np[0], t_old[0] / t_np[0]))

    # =========================================================== B3
    A('')
    A('  ── B3  实数 FFT：fftn/ifftn(c2c)  vs  rfftn/irfftn ──')
    e6 = rng.normal(size=(6, N, N, N))
    e6 = np.ascontiguousarray(e6)
    half = N // 2 + 1

    def b3_c2c():
        return sfft.fftn(e6, axes=(1, 2, 3), workers=WORKERS)

    def b3_real():
        return sfft.rfftn(e6, axes=(1, 2, 3), workers=WORKERS)

    shf = b3_c2c()

    def b3_i_c2c():
        return np.real(sfft.ifftn(shf, axes=(1, 2, 3), workers=WORKERS))

    def b3_i_real():
        return sfft.irfftn(shf[..., :half], axes=(1, 2, 3), s=(N, N, N),
                           workers=WORKERS)

    def b3_ng():
        # 负对照：把半谱沿"半轴"反向 —— 形状不变、看起来像个真谱，但内容是错的
        return sfft.rfftn(e6, axes=(1, 2, 3), workers=WORKERS)[..., ::-1]

    r3 = b3_c2c()
    A('      fftn 出形 %s ；rfftn 出形 %s  ⇒ **半轴 = 最后一个轴**'
      % (r3.shape, b3_real().shape))
    verdict('rfftn == c2c 半谱', r3[..., :half], b3_real(), b3_ng(), 1e-14)
    r3i = b3_i_c2c()
    verdict('irfftn == real(ifftn)', r3i, b3_i_real(),
            b3_i_real() * (1.0 + 1e-6), 1e-14)
    t_c2c = bench(b3_c2c)
    t_r = bench(b3_real)
    t_ic = bench(b3_i_c2c)
    t_ir = bench(b3_i_real)
    A('      fftn  = %.4f s  (%.1f MB 出)   rfftn  = %.4f s  (%.1f MB 出)  **%.2f×**'
      % (t_c2c[0], r3.nbytes / 2 ** 20, t_r[0], b3_real().nbytes / 2 ** 20,
         t_c2c[0] / t_r[0]))
    A('      ifftn = %.4f s                irfftn = %.4f s                **%.2f×**'
      % (t_ic[0], t_ir[0], t_ic[0] / t_ir[0]))
    A('      合计：(c2c)%.4f vs (real)%.4f  **%.2f×**；谱内存 %.1f→%.1f MB'
      % (t_c2c[0] + t_ic[0], t_r[0] + t_ir[0],
         (t_c2c[0] + t_ic[0]) / (t_r[0] + t_ir[0]),
         r3.nbytes / 2 ** 20, b3_real().nbytes / 2 ** 20))

    # =========================================================== B4
    A('')
    A('  ── B4  sigma_tensor 整链：旧(c2c+Lam(M,6,6)) vs 新(rfft+LamT 半谱) ──')
    phi2 = np.ascontiguousarray(pf.phi)

    def b4_old():
        e = np.zeros((6, N, N, N))
        for p in range(6):
            for v in range(nv):
                e[p] += e0v[v, p] * phi2[v]
        e[3:] *= 2.0
        Eh_ = sfft.fftn(e, axes=(1, 2, 3), workers=WORKERS).reshape(6, -1)
        sh = -np.einsum('kpq,qk->pk', Lam, Eh_)
        return np.real(sfft.ifftn(sh.reshape((6, N, N, N)), axes=(1, 2, 3),
                                  workers=WORKERS))

    # 半谱 k 网格（rfftn 的半轴 = 最后一个轴）
    kv = 2 * np.pi * np.fft.fftfreq(N, d=pf.dx)
    Kh = np.stack(np.meshgrid(kv, kv, kv[:half], indexing='ij'),
                  -1).reshape(-1, 3)
    LamH = np.asarray(lambda_packed(C, Kh, k0_mode='free'))       # (Mh,6,6)
    LamHT = np.ascontiguousarray(np.transpose(LamH, (1, 2, 0)))
    A('      Lam 半谱：(%d,6,6)=%.1f MB → 转置 (6,6,%d)=%.1f MB'
      % (LamH.shape[0], LamH.nbytes / 2 ** 20, LamH.shape[0], LamHT.nbytes / 2 ** 20))

    def b4_new():
        e = (e0v.T @ phi2.reshape(nv, -1)).reshape(6, N, N, N)
        e[3:] *= 2.0
        Eh_ = sfft.rfftn(e, axes=(1, 2, 3), workers=WORKERS).reshape(6, -1)
        sh = -np.einsum('pqk,qk->pk', LamHT, Eh_)
        return sfft.irfftn(sh.reshape((6, N, N, half)), axes=(1, 2, 3),
                           s=(N, N, N), workers=WORKERS)

    def b4_ng():
        e = (e0v.T @ phi2.reshape(nv, -1)).reshape(6, N, N, N)
        e[3:] *= 2.0                       # 负对照：漏掉工程应变因子 2
        Eh_ = sfft.rfftn(e, axes=(1, 2, 3), workers=WORKERS).reshape(6, -1)
        sh = -np.einsum('pqk,qk->pk', LamHT, Eh_)
        return sfft.irfftn(sh.reshape((6, N, N, half)), axes=(1, 2, 3),
                           s=(N, N, N), workers=WORKERS)

    r4 = b4_old()
    ok4, teeth4 = verdict('新旧 sigma 整链', r4, b4_new(), b4_ng(), 1e-12)
    t4o = bench(b4_old, rep=max(3, REP // 2))
    t4n = bench(b4_new, rep=max(3, REP // 2))
    A('      墙钟： 旧=%.4f s   新=%.4f s   **%.2f×**' % (t4o[0], t4n[0], t4o[0] / t4n[0]))

    # =========================================================== B5
    A('')
    A('  ── B5  elastic_driving_pair 的 soft 读出 ──')
    nreg = nv + 1
    karr = rng.integers(0, nreg, size=(N, N, N))
    larr = rng.integers(0, nreg, size=(N, N, N))
    e0p = np.concatenate([np.zeros((1, 6)), np.asarray(pf.e0v_eng, float)], 0)
    sep = np.zeros(nreg)

    def b5_full():                              # 现状：全体 (nreg,N³) + nreg 次 einsum
        out = np.zeros((nreg, N, N, N))
        for v in range(nv):
            out[v + 1] = np.einsum('p,p...->...', pf.e0v_eng[v], r4) + sep[v + 1]
        return (np.take_along_axis(out, karr[None], 0)[0],
                np.take_along_axis(out, larr[None], 0)[0])

    def b5_gather():                            # 新：只 gather 两个索引
        def _ed(idx):
            o = np.zeros((N, N, N))
            for p in range(6):
                o += e0p[idx, p] * r4[p]
            return o + sep[idx]
        return _ed(karr), _ed(larr)

    def b5_ng():
        def _ed(idx):
            o = np.zeros((N, N, N))
            for p in range(6):
                o += e0p[idx, p] * r4[p]
            return o
        return _ed((karr + 1) % nreg), _ed((larr + 1) % nreg)

    ra, rb = b5_full()
    ca, cb = b5_gather()
    verdict('gather ed[karr]', ca, ra, b5_ng()[0], 1e-13)
    verdict('gather ed[larr]', cb, rb, b5_ng()[1], 1e-13)
    t5f = bench(b5_full, rep=max(3, REP // 2))
    t5g = bench(b5_gather, rep=max(3, REP // 2))
    A('      墙钟： 全表=%.4f s   gather=%.4f s   **%.2f×**'
      % (t5f[0], t5g[0], t5f[0] / t5g[0]))

    # =========================================================== B6
    A('')
    A('  ── B6  np.gradient(edge_order=2) vs 手工切片中心差分 ──')
    p1 = np.ascontiguousarray(pf.phi[0] if pf.phi.ndim == 4 else pf.phi)
    p1 = np.ascontiguousarray(rng.normal(size=(N, N, N)))

    def b6_np():
        return np.gradient(p1, pf.dx, edge_order=2)

    def b6_manual():
        g = [None] * 3
        for ax in range(3):
            a = p1
            g[ax] = (np.roll(a, -1, axis=ax) - np.roll(a, 1, axis=ax)) / (2 * pf.dx)
        return g

    def b6_slice():
        # 周期边界 ⇒ 用切片赋值代替 roll（不建整场临时）
        g = []
        for ax in range(3):
            n = p1.shape[ax]
            out = np.empty_like(p1)
            sl_c = [slice(None)] * 3
            sl_m = [slice(None)] * 3
            sl_p = [slice(None)] * 3
            sl_c[ax] = slice(1, n - 1)
            sl_m[ax] = slice(0, n - 2)
            sl_p[ax] = slice(2, n)
            np.subtract(p1[tuple(sl_p)], p1[tuple(sl_m)], out=out[tuple(sl_c)])
            e_first = [slice(None)] * 3
            e_first[ax] = 0
            e_last = [slice(None)] * 3
            e_last[ax] = n - 1
            e_1 = [slice(None)] * 3
            e_1[ax] = 1
            e_nm2 = [slice(None)] * 3
            e_nm2[ax] = n - 2
            np.subtract(p1[tuple(e_1)], p1[tuple(e_last)],
                        out=out[tuple(e_first)])
            np.subtract(p1[tuple(e_first)], p1[tuple(e_nm2)],
                        out=out[tuple(e_last)])
            out /= (2 * pf.dx)
            g.append(out)
        return g

    r6 = b6_np()
    verdict('手工 roll 中心差分', r6, b6_manual(),
            [g * 1.0 + 1e-3 for g in r6], 1e-13)
    verdict('切片中心差分', r6, b6_slice(),
            [g * 1.0 + 1e-3 for g in r6], 1e-13)
    t6n = bench(b6_np, rep=max(3, REP // 2))
    t6m = bench(b6_manual, rep=max(3, REP // 2))
    t6s = bench(b6_slice, rep=max(3, REP // 2))
    A('      墙钟： np.gradient=%.4f s   手工 roll=%.4f s (%.2f×)   切片=%.4f s (%.2f×)'
      % (t6n[0], t6m[0], t6n[0] / t6m[0], t6s[0], t6n[0] / t6s[0]))

    # =========================================================== B7
    A('')
    A('  ── B7  sfft 的 workers 扫（rfftn, N=%d）──' % N)
    row = []
    for w in (1, 2, 4, 8):
        def f(w=w):
            return sfft.rfftn(e6, axes=(1, 2, 3), workers=w)
        tt = bench(f, rep=max(3, REP // 2))
        row.append('w=%d: %.4f' % (w, tt[0]))
    A('      ' + '   '.join(row))

    A('')
    A('=' * 100)
    out = '\n'.join(OUT)
    with open(os.path.join(HERE, '_w2_r562_bench.log'), 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
