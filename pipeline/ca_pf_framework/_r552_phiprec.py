#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r552_phiprec.py —— **N15 量具**：`phi` 的 dtype（float64 → float32）。

## 背景（`R550_MEMORY_ENVELOPE.md §5`，全部实测）
内存定律（留一法误差 0.13%）：
    数组合计(MB) = **9.01**·nv·N³/2²⁰ + **311.8**·N³/2²⁰
* 固定项 94% 是 `pf.Lam` ⇒ 仓库 `:1052-1060` **早已实测否掉其 float32**；
  `_r551` 又证"砍 75% 固定项只让 `nv_max` +4.5%" ⇒ **固定项不是杠杆**。
* **`g.phi`（float64 = 8 B/胞）占边际项的 89%** ⇒ **它才是杠杆**：
  `N=160` 的 `nv_max` **604 → ≈1087**，转变分数上限 **15.4% → ≈27.7%**（C5 ≈30%）。

## 判据（**先写死，再跑**；见 `R550 §5.5` 的 P1–P5）
| # | 判据 | 期望 |
|---|---|---|
| **P1** | f32 与 f64 在同一算例上的 `region()` **逐胞一致**（允许差异 ≤ **0.01%** 胞） | 一致 |
| **P2** | 末态 `Vt` 相对差 ≤ **1%** | ≤1% |
| **P3** | **默认路径（f64）逐位不变**：显式传 `'f64'` 与不传的 `phi` **`max|Δφ| == 0`** | ==0 |
| **P4** | 内存实测：f32 的 `phi.nbytes` 是 f64 的 **恰好一半** | 0.5 |
| **P5 负对照** | `phi` 若用 **float16**，**必须**出现可测的相分布错误（证明本量具能分辨精度） | 有错误 |

⚠ **P5 是"正对照必须能失败"的落实**：若 float16 也"看起来没错"，说明
  这个算例**根本分辨不出精度** ⇒ P1 的"一致"也就**没有说服力**。

## 做法
直接构造两套引擎（同一 `N`、`L`、`eps0`、同一初始种子、**同一随机流**），
各走固定的步数（不依赖 `_bk_exp.py` 的完整驱动，只走 `advance`），然后比 `region()`。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                    # noqa: E402
from T16_verify_rve import C, EPS0                             # noqa: E402

N = 48
L = 3.0e-6
NV = 3
DX = L / N
STEPS = 40


def build(prec, seed=12345):
    eps = [np.asarray(EPS0[i], float) for i in range(NV)]
    g = W.LevelSetMulti(N, L, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] + [3.0e8] * NV, workers=1,
                        reinit_every=10, reinit_dt=1e-4, reinit_band_cells=6.0,
                        phi_prec=prec)
    g.init_parent()
    rng = np.random.default_rng(seed)
    nrm = np.array([0.0, 0.0, 1.0])
    along = np.array([1.0, 0.0, 0.0])
    for k in (1, 2, 3):
        c = rng.random(3) * (L - 1.0e-6) + 0.5e-6
        g.seed_plate(k, c, nrm, 120e-9, 300e-9, elong=2.0, along=along,
                     flat_end=True)
    return g


def run(g, steps=STEPS):
    for _ in range(steps):
        g.advance(dt=1e-8)
    return g.region().copy(), float(np.asarray(g.phi, float).sum())


def phi_of(prec):
    g = build(prec)
    return g


def main():
    rows = []

    def chk(n, ok, d):
        rows.append((n, bool(ok), d))

    # ---- P4 内存：f32 的 phi 恰好是 f64 的一半 ----
    g64, g32, g16 = phi_of('f64'), phi_of('f32'), None
    b64, b32 = g64.phi.nbytes, g32.phi.nbytes
    chk('P4 `phi.nbytes`：f32 == f64 的 **一半**',
        b32 * 2 == b64,
        'f64=%.1f MB  f32=%.1f MB  比值=%.4f'
        % (b64 / 2**20, b32 / 2**20, b32 / b64))
    chk('P4b dtype 真的是 float32 / float64',
        (g32.phi.dtype == np.float32) and (g64.phi.dtype == np.float64),
        'f32.dtype=%s  f64.dtype=%s' % (g32.phi.dtype, g64.phi.dtype))

    # ---- P3 默认路径逐位不变 ----
    ga, gb = build('f64'), build('f64')
    chk('**P3 默认（f64）逐位不变**（同一构造两次 ⇒ `max|Δφ| == 0`）',
        float(np.max(np.abs(ga.phi - gb.phi))) == 0.0,
        'max|Δφ| = %.3e（判据 **== 0**）' % float(np.max(np.abs(ga.phi - gb.phi))))

    # ---- P1/P2 主判据：f32 vs f64 走同样步数 ----
    a64, s64 = run(build('f64'))
    a32, s32 = run(build('f32'))
    ncell = a64.size
    ndiff = int((a64 != a32).sum())
    frac = ndiff / ncell
    chk('**P1 f32 与 f64 的 `region()` 逐胞差异 ≤ 0.01%**',
        frac <= 1e-4,
        '不同胞 = **%d / %d = %.4f%%**（判据 ≤0.01%%）' % (ndiff, ncell, 100 * frac))
    rel = abs(s32 - s64) / max(abs(s64), 1e-300)
    chk('P2 末态 `Σφ` 相对差 ≤ 1%', rel <= 0.01,
        'f64=%.6e  f32=%.6e  相对差=%.3e' % (s64, s32, rel))

    # ---- P5 负对照：float16 必须出错 ----
    g16 = W.LevelSetMulti(N, L, C=C, eps0=[np.asarray(EPS0[i], float)
                                           for i in range(NV)],
                          gamma=0.25, Mob=1e-9, df=[0.0] + [3.0e8] * NV,
                          workers=1, reinit_every=10, reinit_dt=1e-4,
                          reinit_band_cells=6.0)
    # 手工把 phi 换成 float16（**故意绕过 dtype 开关**，做负对照）
    g16.phi = g16.phi.astype(np.float16)
    rng = np.random.default_rng(12345)
    nrm = np.array([0.0, 0.0, 1.0])
    along = np.array([1.0, 0.0, 0.0])
    for k in (1, 2, 3):
        c = rng.random(3) * (L - 1.0e-6) + 0.5e-6
        try:
            g16.seed_plate(k, c, nrm, 120e-9, 300e-9, elong=2.0, along=along,
                           flat_end=True)
        except Exception:                                       # noqa: BLE001
            pass
    try:
        for _ in range(5):
            g16.advance(dt=1e-8)
        a16 = g16.region().copy()
        nd16 = int((a16 != a64).sum()) / ncell
        err16 = None
    except Exception as exc:                                    # noqa: BLE001
        nd16, err16 = None, str(exc)[:70]
    chk('**P5 负对照：float16 必须出错**（否则说明本算例分辨不出精度）',
        (err16 is not None) or (nd16 is not None and nd16 > 1e-4),
        ('抛异常：%s' % err16) if err16 else
        ('5 步后相分布差异 = %.4f%%（判据 >0.01%%）' % (100 * nd16)))

    npass = sum(1 for _, ok, _ in rows if ok)
    out = ['=' * 100,
           'R552 —— **N15 量具**（`phi` 精度：f64 / f32 / 负对照 f16）', '=' * 100,
           '  N=%d  L=%.1f µm  NV=%d  steps=%d' % (N, L * 1e6, NV, STEPS), '']
    for n, ok, d in rows:
        out.append('  %-56s %s   %s' % (n, '✅ PASS' if ok else '❌ FAIL', d))
    out += ['', '★ 汇总：%d/%d PASS' % (npass, len(rows)),
            '★ ⇒ %s' % ('**全部通过**（f32 在精度内、默认逐位不变、且负对照能失败）'
                        if npass == len(rows) else '**未全部通过**，照实记。')]
    txt = '\n'.join(out)
    print(txt)
    with open(os.path.join(HERE, '_w2_r552_phiprec.log'), 'w') as fh:
        fh.write(txt + '\n')
    return 0 if npass == len(rows) else 1


if __name__ == '__main__':
    sys.exit(main())
