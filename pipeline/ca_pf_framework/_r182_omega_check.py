#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r182_omega_check.py —— **P1-45 修法（`--omega-mode perstep`）的验证**。

背景见 `R30_AUDIT_LEDGER.md` **§129**：`ladder` 模式把**总张角** `θ_max` 均分给
`M−1` 个间隔 ⇒ 相邻同变体板条的取向差 `Δθ = θ_max/(M−1)` **随 M 变**
⇒ 块内界面能跨 M=2…20 变化 **7.91 倍**，M≤4 时**倒挂**（> γ₀）。

新增的 `perstep` 模式把 `θ_max` 解释成**逐界面步长** `Δθ`（材料性质）
⇒ `ω_i = (i·Δθ)·a` ⇒ **相邻同变体对的 γ 与 M 无关**。

## 判据（**先写死，再跑**）

| # | 判据 | 期望 | 性质 |
|---|---|---|---|
| **P-1** | `perstep(Δθ=θ_max/(M−1))` 与 `ladder(θ_max)` 的 `omega` **逐位相同** | 是 | ★ **正对照**（两种参数化在这一点上必须重合）|
| **P-2** | `perstep(Δθ=0.4545°)` 在 M=2,3,6,12,20 上，**相邻对 γ 完全相同** | 是 | 修法生效 |
| **P-3** | `ladder(5°)` 在同样 M 上，相邻对 γ **不同**（跨度 ≥ 5×） | 是 | **负对照**（否则 P-2 是同义反复）|
| **P-4** | `perstep(Δθ=0.4545°)` 下，**首末对** θ 随 M 线性增长（M=12 时仍 5°） | 是 | 修法**没有**把"块内转动梯度"整个抹掉 |
| **P-5** | 退化输入：M=1 ⇒ 全零；M=0 ⇒ shape (0,3)；`Δθ=0` ⇒ 全零且 `n_f3` 仍为对数 | 不炸 | 硬规则 ⑨ |
| **P-6** | **归档惰性**：默认 `ladder` 路径算出的 `gamma0`/`n_f3`/γ 值与 `§129.3` 实测一致 | 是 | 回归的本地代理 |

⚠ **P-1 为什么是正对照而不是同义反复**：`ladder` 用 `linspace`（末点**含** θ_max），
`perstep` 用 `arange·Δθ`（末点 = `(M−1)·Δθ`）。二者**只在 `Δθ` 取 `θ_max/(M−1)` 时**
重合，且**浮点路径不同**（`linspace` 内部按 `step*(i)` 累加还是 `(1−t)*start+t*stop`
取决于 numpy 版本）⇒ **逐位相同不是显然的**，值得验。
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_lath as WL  # noqa: E402

GAMMA0 = 0.25          # 归档工作点（`--gamma0 0.25`）
AX = np.array([1.0, 0.0, 0.0])


def tab(M, mode, deg, laths=None, gamma0=GAMMA0):
    om = WL.default_omega(M, deg, axis=AX, mode=mode)
    return WL.LathTable(list(laths if laths is not None else [1] * M),
                        omegas=om, gamma0=gamma0)


def main():
    print('=' * 104)
    print('_r182 —— `--omega-mode perstep`（P1-45 修法）验证')
    print('=' * 104)
    res = {}

    # ---------------- P-1 正对照 ----------------
    print()
    print('  ## **P-1 正对照**：`perstep(θ_max/(M−1))` 必须与 `ladder(θ_max)` 逐位相同')
    p1 = True
    for M in (2, 3, 6, 12, 20):
        a = WL.default_omega(M, 5.0, axis=AX, mode='ladder')
        b = WL.default_omega(M, 5.0 / (M - 1), axis=AX, mode='perstep')
        same = np.array_equal(a, b)
        md = float(np.max(np.abs(a - b)))
        p1 &= same
        print('     M=%-3d 逐位相同=%-6s  最大差=%.3e' % (M, same, md))
    print('     ⇒ **P-1 %s**' % ('✅ 通过' if p1 else '❌ 失败'))
    res['P-1'] = p1

    # ---------------- P-2 / P-3 ----------------
    print()
    print('  ## **P-2/P-3**：`perstep` 下相邻对 γ 应与 M 无关；`ladder` 下应显著变')
    print('     %-6s %-14s %-14s %-12s %s'
          % ('M', 'perstep γ(相邻)', '/γ₀', 'ladder γ(相邻)', '/γ₀'))
    per, lad = [], []
    for M in (2, 3, 6, 12, 20):
        tp = tab(M, 'perstep', 0.4545)
        tl = tab(M, 'ladder', 5.0)
        gp = float(tp.gtab[1, 2]) if M > 1 else float('nan')
        gl = float(tl.gtab[1, 2]) if M > 1 else float('nan')
        per.append(gp); lad.append(gl)
        print('     %-6d %-14.6f %-14.4f %-12.6f %.4f'
              % (M, gp, gp / GAMMA0, gl, gl / GAMMA0))
    span_p = max(per) / min(per)
    span_l = max(lad) / min(lad)
    # ★ 修（**本轮第 4 个自查假阳性**）：第一版写 `p2 = span_p < 1e-12` ——
    #   但 `span` 是**比值**，"与 M 无关"对应的是 **span == 1**，不是 span == 0。
    #   实测 span_p = 1.000e+00（各 M 完全一致）却判 ❌。⇒ 判据应为 |span−1| < 1e-12。
    p2 = abs(span_p - 1.0) < 1e-12
    p3 = span_l > 5.0
    print('     ⇒ **P-2** `perstep` 的跨度比 = **%.12f**（要求 |比−1| < 1e-12）⇒ %s'
          % (span_p, '✅ 通过（与 M 完全无关）' if p2 else '❌ 失败'))
    print('     ⇒ **P-3** `ladder` 的跨度 = **%.3f 倍**（要求 > 5）⇒ %s'
          % (span_l, '✅ 通过（确实随 M 变）' if p3 else '❌ 失败（P-2 成同义反复）'))
    res['P-2'], res['P-3'] = p2, p3

    # ---------------- P-4 ----------------
    print()
    print('  ## **P-4**：`perstep` 仍保留"块内转动梯度"（首末对随 M 增长）')
    p4 = True
    for M in (2, 6, 12, 20):
        tp = tab(M, 'perstep', 0.4545)
        th_far = float(np.rad2deg(tp.theta[1, M]))
        exp = 0.4545 * (M - 1)
        ok = abs(th_far - exp) < 1e-9
        p4 &= ok
        print('     M=%-3d 首末对 θ = %7.4f°（期望 %.4f°）⇒ %s'
              % (M, th_far, exp, '✅' if ok else '❌'))
    print('     ⇒ **P-4 %s**（总张角仍随 M 增长 ⇒ 没把梯度抹平）'
          % ('✅ 通过' if p4 else '❌ 失败'))
    res['P-4'] = p4

    # ---------------- P-5 退化 ----------------
    print()
    print('  ## **P-5** 退化输入（硬规则 ⑨）')
    p5 = True
    z1 = WL.default_omega(1, 5.0, axis=AX, mode='perstep')
    c1 = (z1.shape == (1, 3) and not z1.any())
    print('     M=1 ⇒ shape %s，全零=%s ⇒ %s' % (z1.shape, not z1.any(),
                                                '✅' if c1 else '❌'))
    z0 = WL.default_omega(0, 5.0, axis=AX, mode='perstep')
    c0 = (z0.shape == (0, 3))
    print('     M=0 ⇒ shape %s ⇒ %s' % (z0.shape, '✅' if c0 else '❌'))
    tz = tab(4, 'perstep', 0.0)
    cz = (tz.n_f3 == 6 and np.allclose(tz.gtab[1:5, 1:5][np.isfinite(
        tz.gtab[1:5, 1:5])], 0.0))
    print('     M=4, Δθ=0 ⇒ n_f3=%d（应为 6），F3 的 γ 全 0=%s ⇒ %s'
          % (tz.n_f3, cz, '✅' if cz else '❌'))
    p5 = c1 and c0 and cz
    print('     ⇒ **P-5 %s**' % ('✅ 通过' if p5 else '❌ 失败'))
    res['P-5'] = p5

    # ---------------- P-6 归档惰性 ----------------
    print()
    print('  ## **P-6** 归档惰性：默认 `ladder` 路径的值必须与 `§129.3` 实测一致')
    # `§129`/`_r172` 实测值（`_w2_r172.log`）：
    #   1,1,1,3,3,3 (M=6, ladder 5°) ⇒ F3 γ ∈ {0.0979, 0.1592}
    #   1,1,2,2,...,8,8 (M=12, ladder 5°) ⇒ F3 γ = 0.053972
    t6 = tab(6, 'ladder', 5.0, laths=[1, 1, 1, 3, 3, 3])
    g6 = sorted({round(float(t6.gtab[i + 1, j + 1]), 6)
                 for i in range(6) for j in range(i + 1, 6)
                 if t6.vmap[i] == t6.vmap[j]})
    t12 = tab(12, 'ladder', 5.0,
              laths=[1, 1, 2, 2, 3, 3, 4, 4, 7, 7, 8, 8])
    g12 = round(float(t12.gtab[1, 2]), 6)
    # ★ 修（**本轮第 5 个自查假阳性**）：第一版把期望值写成 `[0.0979, 0.1592]`，
    #   但那是 `_w2_r172.log` 里**只印了 4 位小数**的显示值，而这里 `round(...,6)`
    #   得到 `0.097918` / `0.159228` ⇒ 拿 6 位去比 4 位，**必然 ❌**。
    #   ⇒ 教训（硬规则 ⑪ 的数值版）：**判据里的期望值必须与被比较量同精度**，
    #     不能照抄别处日志的**显示**位数。
    c6 = (len(g6) == 2 and abs(g6[0] - 0.097918) < 1e-5
          and abs(g6[1] - 0.159228) < 1e-5)
    c12 = (abs(g12 - 0.053972) < 1e-6)
    print('     `1,1,1,3,3,3` 的 F3 γ 取值 = %s（期望 [0.097918, 0.159228]）⇒ %s'
          % (g6, '✅' if c6 else '❌'))
    print('     `saSet2` 的 F3 γ(相邻) = %.6f（期望 0.053972）⇒ %s'
          % (g12, '✅' if c12 else '❌'))
    print('     ⇒ **P-6 %s**' % ('✅ 通过（默认路径未变）' if (c6 and c12) else '❌ 失败'))
    res['P-6'] = c6 and c12

    # ---------------- 结论 ----------------
    print()
    print('=' * 104)
    print('  ## 结论')
    print('=' * 104)
    for k in ('P-1', 'P-2', 'P-3', 'P-4', 'P-5', 'P-6'):
        print('     %-6s %s' % (k, '✅' if res.get(k) else '❌'))
    allok = all(res.get(k) for k in ('P-1', 'P-2', 'P-3', 'P-4', 'P-5', 'P-6'))
    print()
    print('     ⇒ %s' % ('✅ **全部通过**：`perstep` 已接线，'
                         '且默认 `ladder` 路径逐位未变' if allok
                         else '❌ **有判据不过** ⇒ 见上'))
    print()
    print('  ⚠ 记账：**是否启用 `perstep` 仍需受控对照**（沿用 `§102` 的 C 方案）。')
    print('     本脚本只证"开关接线正确、且默认关时惰性"。')
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
