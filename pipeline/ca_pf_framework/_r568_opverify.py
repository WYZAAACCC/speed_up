#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r568_opverify.py --- 本轮**全部算子优化开关**的判决量具。

## 被判的对象（全部默认关，见 `windowB_pf3d.PF3D` 类 docstring）
| 开关 | 值 | 声明 |
|---|---|---|
| `eps0_mode` | `loop`(默认) / `einsum` / `gemm` | einsum **逐位**、gemm 1–2 ulp |
| `fft_mode`  | `c2c`(默认) / `rfft` | rfft+Nyquist 修正 ⇒ 与 c2c 等价到舍入 |
| `ed_pair_mode` | `full`(默认) / `gather` | gather **逐位** |

## 判据（全部**先写死**，每条都配**能失败的负对照 NG**）
* **V1** `sigma_tensor`：c2c/loop vs rfft/einsum ⇒ rel ≤ 1e-13；
       NG = **关掉 Nyquist 修正**的 rfft ⇒ 必须 ≥ 1e-3（否则 V1 没分辨力）
* **V2** `eps0_fields`：`einsum` vs `loop` ⇒ **=== 0.0（逐位）**；
       `gemm` vs `loop` ⇒ ≤ 1e-14；NG = 漏掉一个变体 ⇒ 必须 ≥ 1e-3
* **V3** `elastic_driving_pair`：`full` vs `gather` ⇒ **=== 0.0（逐位）**；
       NG = 用 karr+1 读 ⇒ 必须 ≥ 1e-3
* **V4** 端到端短轨迹：同一初值，优化开关 ON vs OFF 各跑 K 步
       ⇒ `region()` 逐位相同的比例、`max|Δφ|`、`ed` 的最大相对差
* **V5** 实测单步墙钟与加速比
* **V6** 默认路径自证：不传任何新开关时，引擎里 `_fft_mode=='c2c'`、
       `_eps0_mode=='loop'`、`_ed_pair_mode=='full'`（**防"改一半"**）
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

N = int(os.environ.get('R568_N', '64'))
NV = int(os.environ.get('R568_NV', '24'))
DX_UM = float(os.environ.get('R568_DX', '0.0625'))
STEPS = int(os.environ.get('R568_STEPS', '12'))
WORKERS = int(os.environ.get('R568_WORKERS', '4'))
LOG = []


def A(s):
    LOG.append(s)
    print(s, flush=True)


def rel(a, b):
    a = np.asarray(a)
    b = np.asarray(b)
    if a.shape != b.shape:
        return float('nan')
    return float(np.max(np.abs(a - b))) / max(float(np.max(np.abs(b))), 1e-300)


def build(_df_eps=0.0, _df1_eps=0.0, _g_eps=0.0, **kw):
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(NV)]
    _df = [0.0] + [3.0e8 * (1.0 + _df_eps)] * NV
    _df[1] = 3.0e8 * (1.0 + _df1_eps)          # 不对称扰动（`df[k]−df[l]` 不再相消）
    g = W.LevelSetMulti(N, N * DX_UM, C=C, eps0=eps,
                        gamma=0.25 * (1.0 + _g_eps), Mob=1e-9,
                        df=_df, workers=WORKERS,
                        reinit_every=20, reinit_dt=1e-4, reinit_band_cells=6.0,
                        phi_prec='f64', **kw)
    g.init_parent()
    rng = np.random.default_rng(7)
    nrm = np.array([0.0, 0.0, 1.0])
    Lc = N * DX_UM
    for k in range(1, max(2, NV // 4) + 1):
        g.seed_plate(k, rng.random(3) * (Lc * 0.6) + Lc * 0.2, nrm, 120e-9, 300e-9)
    g.advance(dt=1e-8)                      # 预热（也是 soft 剖面的建立步）
    return g


def snap(g):
    return {'region': g.region().copy(),
            'phi': np.array(g.phi, copy=True),
            'karr_larr': (g.region()[0, 0, 0],)}


def run(g, n):
    reg0 = g.region().copy()
    for _ in range(n):
        g.advance(dt=1e-8)
    return reg0


def main():
    A('=' * 100)
    A('R568 — 算子优化开关判决（N=%d nv=%d steps=%d workers=%d）'
      % (N, NV, STEPS, WORKERS))
    A('=' * 100)

    # ================================================= V6 默认路径自证
    A('')
    A('  ── V6 默认路径自证（不传新开关 ⇒ 必须是旧路）──')
    g0 = build()
    v6 = (g0.pf._fft_mode == 'c2c' and g0.pf._eps0_mode == 'loop'
          and g0._ed_pair_mode == 'full')
    A('      pf._fft_mode=%r  pf._eps0_mode=%r  _ed_pair_mode=%r  ⇒ %s'
      % (g0.pf._fft_mode, g0.pf._eps0_mode, g0._ed_pair_mode,
         '✅ PASS' if v6 else '❌ FAIL（默认被改动 = 归档不可复现）'))

    # ================================================= V2 eps0_fields
    A('')
    A('  ── V2 `eps0_fields`：loop / einsum / gemm ──')
    w = 1.5 * g0.dx
    for v in range(NV):
        g0.pf.phi[v] = 0.5 * (1.0 - np.tanh(g0.phi[v + 1] / w))
    r_loop = g0.pf.eps0_fields()
    g0.pf._eps0_mode = 'einsum'
    r_ein = g0.pf.eps0_fields()
    g0.pf._eps0_mode = 'gemm'
    r_gem = g0.pf.eps0_fields()
    g0.pf._eps0_mode = 'loop'
    d_ein, d_gem = rel(r_ein, r_loop), rel(r_gem, r_loop)
    ng = r_loop.copy()
    ng[0] = 0.0                                   # NG：漏掉一个应变分量
    d_ng = rel(ng, r_loop)
    A('      einsum vs loop : max|Δ|/max = %.3e   %s'
      % (d_ein, '✅ **逐位相同**' if d_ein == 0.0 else '⚠ 非逐位'))
    A('      gemm   vs loop : max|Δ|/max = %.3e   %s'
      % (d_gem, '✅ ≤1e-14' if d_gem <= 1e-14 else '❌'))
    A('      [NG] 漏掉第 0 分量 : max|Δ|/max = %.3e   %s'
      % (d_ng, '✅ 有分辨力' if d_ng > 1e-3 else '❌ 判据没分辨力'))
    v2 = (d_ein == 0.0 and d_gem <= 1e-14 and d_ng > 1e-3)

    # ================================================= V1 sigma_tensor
    A('')
    A('  ── V1 `sigma_tensor`：c2c/loop vs rfft/einsum ──')
    g1 = build(fft_mode='rfft', eps0_mode='einsum')
    # 让两边的 pf.phi 完全一致
    for v in range(NV):
        prof = 0.5 * (1.0 - np.tanh(g0.phi[v + 1] / w))
        g0.pf.phi[v] = prof
        g1.pf.phi[v] = prof
    s_old = g0.pf.sigma_tensor(None)
    s_new = g1.pf.sigma_tensor(None)
    d_sig = rel(s_new, s_old)
    # NG：把 Lam 半谱**整体**替换成"未做 Nyquist 平均"的版本
    _Lam_bak = g1.pf.Lam.copy()
    kv = 2 * np.pi * np.fft.fftfreq(N, d=g1.pf.dx)
    half = N // 2 + 1
    _idx = np.stack(np.meshgrid(np.arange(N), np.arange(N), np.arange(half),
                                indexing='ij'), -1).reshape(-1, 3)
    _Kh = np.stack(np.meshgrid(kv, kv, kv[:half], indexing='ij'),
                   -1).reshape(-1, 3)
    g1.pf.Lam = np.asarray(P3.lambda_packed(C, _Kh, k0_mode='free'))
    g1.pf._nyq_n = 0
    s_ng = g1.pf.sigma_tensor(None)
    d_sig_ng = rel(s_ng, s_old)
    g1.pf.Lam = _Lam_bak
    A('      rfft/einsum vs c2c/loop : max|Δ|/max = %.3e   %s'
      % (d_sig, '✅ ≤1e-13' if d_sig <= 1e-13 else '❌'))
    A('      [NG] 关掉 Nyquist 修正    : max|Δ|/max = %.3e   %s'
      % (d_sig_ng, '✅ 有分辨力（必须大）' if d_sig_ng > 1e-3 else '❌ 判据没分辨力'))
    A('      σ 量级 max|σ| = %.4e' % float(np.max(np.abs(s_old))))
    v1 = (d_sig <= 1e-13 and d_sig_ng > 1e-3)

    # ---- V1b ★ R570：`E_el()`（诊断能量）也必须等价 —— 这是**冒烟在真实路径上**
    #      抓到的缺陷：半谱二次型漏了 "k↔−k 配对权重"，`E_el_J` 曾差 37.7%。
    e_old = float(g0.pf.E_el())
    e_new = float(g1.pf.E_el())
    d_E = abs(e_new - e_old) / max(abs(e_old), 1e-300)
    A('      V1b `E_el()` c2c=%.6e  rfft=%.6e  相对差 = %.3e   %s'
      % (e_old, e_new, d_E, '✅ ≤1e-12' if d_E <= 1e-12 else '❌ FAIL'))
    v1 = v1 and (d_E <= 1e-12)

    # ================================================= V3 ed_pair
    A('')
    A('  ── V3 `elastic_driving_pair`：full vs gather ──')
    karr, larr = g0.par.argmin2(g0.phi)
    karr = karr.astype(np.intp)
    larr = larr.astype(np.intp)
    g0._ed_pair_mode = 'full'
    ea_f, eb_f = g0.elastic_driving_pair(karr, larr)
    g0._ed_pair_mode = 'gather'
    ea_g, eb_g = g0.elastic_driving_pair(karr, larr)
    g0._ed_pair_mode = 'full'
    d3a, d3b = rel(ea_g, ea_f), rel(eb_g, eb_f)
    ng3 = g0._ed_pair_gather((karr + 1) % (NV + 1), larr, s_old)[0]
    d3ng = rel(ng3, ea_f)
    A('      ed[karr] : max|Δ|/max = %.3e   %s'
      % (d3a, '✅ **逐位相同**' if d3a == 0.0 else '⚠ 非逐位'))
    A('      ed[larr] : max|Δ|/max = %.3e   %s'
      % (d3b, '✅ **逐位相同**' if d3b == 0.0 else '⚠ 非逐位'))
    A('      [NG] 用 karr+1 读 : max|Δ|/max = %.3e   %s'
      % (d3ng, '✅ 有分辨力' if d3ng > 1e-3 else '❌ 判据没分辨力'))
    v3 = (d3a == 0.0 and d3b == 0.0 and d3ng > 1e-3)

    # ================================================= V4 端到端轨迹
    A('')
    A('  ── V4 端到端短轨迹（同一初值，各 %d 步）──' % STEPS)
    V4POS = [False]
    arms = [('baseline (c2c/loop/full)', dict()),
            ('einsum', dict(eps0_mode='einsum')),
            ('einsum+gather', dict(eps0_mode='einsum', ed_pair_mode='gather')),
            ('rfft+einsum+gather',
             dict(fft_mode='rfft', eps0_mode='einsum', ed_pair_mode='gather')),
            ('rfft+gemm+gather',
             dict(fft_mode='rfft', eps0_mode='gemm', ed_pair_mode='gather')),
            # ★★ **V4 负对照（必须能失败）**。
            #   第一版用 `df×(1+ε)` —— **实测它是坏对照**：本配置里**所有变体的 df 相同**
            #   ⇒ `df[karr] − df[larr] ≡ 0`（只在母相/变体交界处非零）⇒ 扰动被消掉，
            #   1e-12 才勉强给出 4.4e-16。⇒ 换成扰动**真正进入速度**的量：
            #   `γ`（进 `stk`／曲率项，是速度的主导项之一）。
            ('NG: γ×(1+1e-12)', dict(_g_eps=1.0e-12)),
            ('NG: γ×(1+1e-9)', dict(_g_eps=1.0e-9)),
            ('NG: df×(1+1e-12)（**坏对照**，df 相消）', dict(_df_eps=1.0e-12)),
            # ★ 下面两条是**大**扰动：它们必须被看见，否则说明 V4 比较器是死的。
            ('NG(大): γ×1.5', dict(_g_eps=0.5)),
            ('NG(大): df[1]×1.01（不对称）', dict(_df1_eps=0.01))]
    base = None
    A('      %-34s %-10s %-12s %-12s' % ('arm', 'Δregion胞', 'max|Δφ|', 'Vt 相对差'))
    import json
    for name, kw in arms:
        gg = build(**kw)
        _phi_before = np.array(gg.phi, copy=True)      # ★ V4 的**正对照**：轨迹得真的动
        r0 = run(gg, STEPS)
        _moved = float(np.max(np.abs(np.asarray(gg.phi, float) - _phi_before)))
        if base is None:
            base = (r0.copy(), np.array(gg.phi, copy=True),
                    float(gg.totals()[0] + gg.totals()[1]))
            A('      %-34s %-10s %-12s %-12s' % (name, '—（基准）', '—', '—'))
            A('      └ **[正对照] 基准轨迹本身移动了 max|Δφ| = %.4e** ⇒ %s'
              % (_moved, '✅ 轨迹真的在动，下面的 0 才有意义'
                 if _moved > 0 else
                 '❌ **轨迹根本没动** ⇒ 本表的"全 0"什么都说明不了，V4 作废'))
            v4pos = _moved > 0
            V4POS[0] = _moved > 0
            continue
        dreg = int(np.count_nonzero(r0 != base[0]))
        dphi = float(np.max(np.abs(np.asarray(gg.phi, float) - base[1])))
        vt = float(gg.totals()[0] + gg.totals()[1])
        dvt = abs(vt - base[2]) / max(abs(base[2]), 1e-30)
        A('      %-34s %-10d %-12.3e %-12.3e   (本臂自身走了 %.2e)'
          % (name, dreg, dphi, dvt, _moved))

    # ================================================= V5 墙钟
    A('')
    A('  ── V5 墙钟（中位数 / 5 步）──')
    for name, kw in arms:
        gg = build(**kw)
        gg.advance(dt=1e-8)
        ts = []
        for _ in range(5):
            t0 = time.perf_counter()
            gg.advance(dt=1e-8)
            ts.append(time.perf_counter() - t0)
        A('      %-30s %.4f s/步' % (name, float(np.median(ts))))

    A('')
    A('  ══ 总判定 ══')
    A('      V1 sigma 等价 = %s ；V2 eps0 = %s ；V3 ed_pair = %s ；V6 默认关 = %s'
      % ('PASS' if v1 else 'FAIL', 'PASS' if v2 else 'FAIL',
         'PASS' if v3 else 'FAIL', 'PASS' if v6 else 'FAIL'))
    A('      V4 正对照（轨迹真的在动）= %s'
      % ('PASS' if V4POS[0] else '❌ FAIL ⇒ V4 表作废'))
    out = '\n'.join(LOG)
    with open(os.path.join(HERE, '_w2_r568_opverify.log'), 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
    return 0 if (v1 and v2 and v3 and v6) else 1


if __name__ == '__main__':
    sys.exit(main())
