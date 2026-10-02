#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_tscale.py --- ★★★ **时间账**：把 `m` 提上去要跑多久？（goal §(15) 的"先算账再开跑"）

## 为什么必须算
R48 的更正说 **C5 可行：`m ≈ 38`（`nv=456`，19.9 GB）** —— 那是**内存**账。
但 goal §(15) 明写：**"时间账：必须先实测 s/步，再外推，与可接受用时对比后才决定步数。
不许不问就开跑。"** ⇒ **本量具算这一笔。**

## 方法（**用现有两臂的实测 `wall_s`，不猜**）
`series.csv` 有 `wall_s`（累计墙钟）与 `step` ⇒ 逐行算 **s/步**：
* **稳态 s/步** 取**后半段的中位**（避开构造期与启动）；旁证：`build` 期单列。
* **外推律**：本仓实测的构造期 `_pair_normals` 是 **O(nv²)**（P9），
  而**每步**的开销主要是 **O(nv·N³)** 的逐场算子 ⇒ **本量具同时给两个外推**：
  ① **保守（线性 in nv）**：`s/步 ∝ nv`；
  ② **悲观（含 O(nv²) 项）**：`s/步 = a·nv + b·nv²`（用两点定 a、b 时退化为线性 ⇒ 只用 ①，
     但把 `build` 期单独按 `nv²` 放大）。
* **判据（预先写死）**：给出 `m ∈ {4, 12, 20, 38, 45}` 的 **预计全程墙钟**（按 600 步，
  因为**准静态钟在 step 600 自停** —— 见各臂日志）。
"""
import os
import sys

import numpy as np

ROOT = '_exp/_bk_p2'
STEPS_SELFSTOP = 600      # 准静态钟自停步（实测：第 6 档 327.5 K < T_end=350 K）
BUDGET_H = 24.0           # "可接受用时"的自选上限（**待用户拍板，这里只给参考线**）


def load(tag):
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    dd = np.genfromtxt(p, delimiter=',', names=True)
    return dd


def main():
    tags = sys.argv[1:] or ['p2_b5', 'p2_b5ov', 'p2_b5ps']
    print('=' * 100)
    print('时间账：`m` 提上去要跑多久？（用现有臂的实测 `wall_s`）')
    print('=' * 100)
    meas = {}
    for t in tags:
        dd = load(t)
        if dd is None or 'wall_s' not in dd.dtype.names:
            print('  %-9s ❌ 无 `wall_s`' % t); continue
        st = np.atleast_1d(dd['step']).astype(float)
        wl = np.atleast_1d(dd['wall_s']).astype(float)
        # 逐行 s/步
        dstep = np.diff(st); dwall = np.diff(wl)
        ok = dstep > 0
        sp = dwall[ok] / dstep[ok]
        stm = st[1:][ok]
        # 稳态 = 后半段中位
        half = stm >= (stm.max() * 0.5)
        med = float(np.median(sp[half])) if half.any() else float(np.median(sp))
        meas[t] = dict(nv=48, steps=int(st.max()), wall=float(wl[-1]),
                       s_per_step_med=med, s_per_step_last=float(sp[-1]))
        print('  %-9s nv=48  到 step %-4d 累计墙钟 **%.0f s = %.2f h**'
              % (t, st.max(), wl[-1], wl[-1] / 3600))
        print('             s/步：后半段**中位 %.3f**  末值 %.3f  首值 %.3f'
              % (med, sp[-1], sp[0]))
    if not meas:
        return
    base = np.median([m['s_per_step_med'] for m in meas.values()])
    print()
    print('  ⇒ **基准 s/步（nv=48）取两臂中位 = %.3f s/步**' % base)
    print()
    print('  ── 外推（**线性 in nv**：每步做 O(nv) 次逐场运算）──')
    print('  %-6s %-7s %-12s %-14s %-14s %s'
          % ('m', 'nv', '相对 nv×', 's/步', '600 步全程', '过 %.0f h 线？' % BUDGET_H))
    print('  ' + '-' * 88)
    for m in (4, 12, 20, 38, 45):
        nv = 12 * m
        k = nv / 48.0
        sps = base * k
        tot_h = sps * STEPS_SELFSTOP / 3600.0
        print('  %-6d %-7d %-12.2f %-14.2f **%-11.2f h** %s'
              % (m, nv, k, sps, tot_h,
                 '✅' if tot_h <= BUDGET_H else '❌ **超 %.0f h**' % BUDGET_H))
    print()
    print('  ── 内存账（goal §(12)：onfly `a=9.000`）对照 ──')
    CELL = 160 ** 3
    for m in (4, 12, 20, 38, 45):
        nv = 12 * m
        gb = (9.000 * nv * CELL + 392.0 * CELL) / 1e9 + 1515.6 / 1024.0
        print('  m=%-4d nv=%-5d ⇒ 预测峰值 **%6.2f GB** %s'
              % (m, nv, gb, '✅' if gb <= 22 else '❌ 超 22 GB'))
    print()
    print('=' * 100)
    print('★ 判读（**预先写死**）')
    print('  · `m=12`（已排队）：时间 %s、内存 %s'
          % ('在 %.0f h 内 ✅' % BUDGET_H if base * 4 * STEPS_SELFSTOP / 3600 <= BUDGET_H else '超线 ❌',
             '在 22 GB 内 ✅'))
    print('  · `m=38`（C5 的 450 根）：时间 %s'
          % ('在 %.0f h 内 ✅' % BUDGET_H if base * (456 / 48.0) * STEPS_SELFSTOP / 3600 <= BUDGET_H
             else '**超 %.0f h ❌ ⇒ C5 即使内存可行，时间也是瓶颈**' % BUDGET_H))
    print('  ⚠ 线性外推**可能偏乐观**：`build` 期的 `_pair_normals` 是 **O(nv²)**（P9）')
    print('     ⇒ nv=456 时构造期 = (456/48)² = **%.0f×** 于 nv=48 的构造期' % (456 / 48.0) ** 2)
    print('  ⚠ "可接受用时"是**我自选的 %.0f h 参考线**，**待用户拍板**。' % BUDGET_H)
    print('=' * 100)


if __name__ == '__main__':
    main()
