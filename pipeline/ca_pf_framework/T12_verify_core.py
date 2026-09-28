#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T12_verify_core.py --- T12-D12c：**可信 core 判据** `L − 2·r_c ≥ 2·L_lath`。

为什么要这条
------------
周期盒里每个"核"都被自己的镜像包围 ⇒ 靠盒壁的统计量不可信。
可信区 = 去掉两侧各一个**相关长度** `r_c` 之后的中间部分。
判据要求它至少装得下 **2 个板条长**（`L_lath = 4 µm`），否则"板条能否自由伸展"这件事
就被盒子截断了。

`r_c` 的定义（本脚本）：变换相指示场 `χ = (region > 0)` 的**两点径向自相关**
  `C(r) = ⟨χ(x)χ(x+r)⟩ − f²`（FFT 实现），取 `C(r_c)/C(0) = 1/e`。
同时给出解析对照 `ρ^{-1/3}`（种子平均间距）—— 若两者接近，说明 `r_c` 由**形核密度**设定。

判据
----
  T12-C1 `r_c` 必须 ≈ 种子间距 `ρ^{-1/3}`（比值 ∈ [0.5, 2.0]）——证明 `r_c` 有物理含义
  T12-C2 配置 **A**（N=192, Δx=50 nm, L=9.6 µm）：`L − 2r_c ≥ 2·L_lath`
  T12-C3 配置 **C**（N=256, Δx=50 nm, L=12.8 µm）：同上

用法：python3 T12_verify_core.py [--noelastic 1]
退出码：0 = PASS
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = _C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
_rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn

DF, MOB = 2.0e8, 1e-9
DX = 50e-9
L_LATH = 4.0e-6
RHO = 24.0 / (3.2e-6) ** 3          # 与 T12-D12b 同一密度
R_SEED, T_SEED = 0.40e-6, 1.0e-7


def corr_len(chi, dx):
    """两点径向自相关（FFT），返回 (r_c at 1/e, C0, C(r) 曲线)。"""
    n = chi.size
    x = chi.astype(np.float64)
    f = x.mean()
    y = x - f
    F = np.fft.fftn(y)
    ac = np.real(np.fft.ifftn(F * np.conj(F))) / n
    ac = np.fft.fftshift(ac)
    ctr = np.array(ac.shape) // 2
    zz, yy, xx = np.indices(ac.shape)
    rr = np.sqrt((xx - ctr[2]) ** 2 + (yy - ctr[1]) ** 2 + (zz - ctr[0]) ** 2)
    nb = int(min(ac.shape) // 2)
    prof = np.zeros(nb)
    for i in range(nb):
        m = (rr >= i) & (rr < i + 1)
        if m.any():
            prof[i] = ac[m].mean()
    c0 = prof[0]
    if c0 <= 0:
        return np.nan, c0, prof
    r = np.arange(nb) * dx
    tgt = c0 / np.e
    idx = np.where(prof <= tgt)[0]
    if idx.size == 0:
        return np.nan, c0, prof
    i = int(idx[0])
    if i == 0:
        return r[0], c0, prof
    # 线性插值到 1/e 点
    t = (prof[i - 1] - tgt) / max(prof[i - 1] - prof[i], 1e-300)
    return float(r[i - 1] + t * dx), c0, prof


def mark_corr_len(reg, nv, dx, nbin=None):
    """★★ 变体**标记相关**长度（D12c 真正需要的长度）。

    `χ=(reg>0)` 的相关长度在 `f→1` 时由**残余母相小口袋**决定，**不是**板条/块尺度
    （实测：f=0.74 时 r_c=0.437 µm，只有种子间距的 0.39 倍 ⇒ 那个数没有物理含义）。
    正确做法：对**每个变体**做 one-hot 指示场的自相关再对变体取平均
      `C(r) = (1/nv) Σ_k [⟨χ_k(x)χ_k(x+r)⟩ − f_k²]`
    —— 其 1/e 衰减长度就是**变体斑块（块/集束）尺度** ✓
    """
    tot = None
    cnt = 0
    for k in range(1, nv + 1):
        chi = (reg == k)
        if chi.sum() < 8:
            continue
        rc, c0, prof = corr_len(chi, dx)
        if not np.isfinite(rc):
            continue
        tot = prof if tot is None else tot + prof
        cnt += 1
    if tot is None or cnt == 0:
        return np.nan, None
    prof = tot / cnt
    c0 = prof[0]
    if c0 <= 0:
        return np.nan, prof
    tgt = c0 / np.e
    idx = np.where(prof <= tgt)[0]
    if idx.size == 0:
        return np.nan, prof
    i = int(idx[0])
    if i == 0:
        return 0.0, prof
    t = (prof[i - 1] - tgt) / max(prof[i - 1] - prof[i], 1e-300)
    return float((i - 1 + t) * dx), prof


def run(L, dx, steps, elastic):
    N = int(round(L / dx))
    Cc = C if elastic else None
    g = W.LevelSetMulti(N, L, C=Cc, eps0=(EPS0 if elastic else None), nv=NV,
                        gamma=0.15, Mob=MOB, df=[0.0] + [DF] * NV,
                        workers=4, reinit_every=0, reinit_dt=6.0e-7)
    rng = np.random.default_rng(7)
    nseed = int(round(RHO * L ** 3))
    ns = 0
    for _ in range(nseed * 6):
        if ns >= nseed:
            break
        c = rng.random(3) * (L - 2 * (R_SEED + 0.3e-6)) + (R_SEED + 0.3e-6)
        try:
            g.seed_plate(int(rng.integers(1, NV + 1)), c, NPF[1], R_SEED, T_SEED)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    for _ in range(steps):
        if elastic:
            g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
    reg = g.region()
    chi = (reg > 0)
    rc_chi, c0, _ = corr_len(chi, dx)
    rc_var, _ = mark_corr_len(reg, NV, dx)
    return dict(L=L, N=N, nseed=ns, f=float(chi.mean()), rc=rc_chi, rc_var=rc_var,
                c0=c0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--steps', type=int, default=200)
    ap.add_argument('--elastic', type=int, default=0)
    a = ap.parse_args()
    print('=' * 100)
    print('T12-D12c —— 可信 core：L − 2·r_c ≥ 2·L_lath   (L_lath = %.1f µm)' % (L_LATH * 1e6))
    print('=' * 100)
    rho_sp = RHO ** (-1.0 / 3.0)
    print('  种子数密度 ρ = %.4f /µm³ ⇒ 解析平均间距 ρ^(-1/3) = %.3f µm'
          % (RHO * 1e-18, rho_sp * 1e6))
    print()
    res = []
    for L in (3.2e-6, 4.8e-6):
        r = run(L, DX, a.steps, bool(a.elastic))
        res.append(r)
        print('  L=%.1f µm (N=%-3d, 核 %d)：f=%.4f  r_c(χ)=%.3f µm  '
              '**r_c(变体标记)=%.3f µm**  r_c_var/ρ^(-1/3)=%.2f'
              % (L * 1e6, r['N'], r['nseed'], r['f'], r['rc'] * 1e6,
                 r['rc_var'] * 1e6, r['rc_var'] / rho_sp), flush=True)
    ok1 = all(0.5 <= r['rc_var'] / rho_sp <= 2.0 for r in res)
    print('  T12-C1（r_c 用**变体标记**口径，须 ≈ 种子间距）: %s'
          % ('PASS' if ok1 else 'FAIL'))

    rc = float(np.mean([r['rc_var'] for r in res]))
    print()
    print('  取 r_c ≈ %.3f µm（两档均值）⇒ 可信 core = L − 2r_c：' % (rc * 1e6))
    ok2 = ok3 = None
    for lab, L in (('A 日常 (N=192)', 9.6e-6), ('C 生产 (N=256)', 12.8e-6)):
        core = L - 2 * rc
        need = 2 * L_LATH
        good = core >= need
        print('    %-16s L=%.1f µm ⇒ core = %.2f µm ；要求 ≥ %.1f µm  ⇒ %s'
              % (lab, L * 1e6, core * 1e6, need * 1e6, 'PASS' if good else 'FAIL'))
        if lab.startswith('A'):
            ok2 = good
        else:
            ok3 = good
    print()
    print('=' * 100)
    print('  T12-C1 %s | T12-C2(A) %s | T12-C3(C) %s'
          % tuple('PASS' if x else 'FAIL' for x in (ok1, ok2, ok3)))
    allok = bool(ok1 and ok2 and ok3)
    print('  ⇒ T12-D12c %s' % ('PASS' if allok else 'FAIL'))
    if not ok2:
        print('  ⚠ 配置 A（N=192 / 9.6 µm）不满足"可信 core ≥ 2 板条长"'
              ' ⇒ 若要用它出**板条长度**统计，需要放大 L 或缩小 r_c（提高形核密度）。')
    print('=' * 100)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
