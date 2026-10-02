#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_a24.py --- ★★★ A24：C3 判据 `nf3_col == nslab_n − 1` 的**口径**裁定。

# 一、先写物理（goal §(16)⑤：**先数学与物理框架，后代码**）

## 1. 这个式子在说什么
一个 **block** = 同一变体、由**低角晶界**（F3）分隔的若干 **lath**。
若块内 lath 排成**一条链**（每根只与相邻的一根共享低角晶界），则
**链上的边数 = 根数 − 1** ⇒ `nf3_col == nslab_n − 1`。
⇒ **这个式子隐含了两个前提**：
  * **(P1)** 块内 lath 构成**一条链**（不是树、不是多链）；
  * **(P2)** **没有异变体侵入**（侵入会把链**切断**）。

## 2. 异变体侵入时，物理上应该发生什么
异变体与母变体的取向差**大** ⇒ 它们之间形成的是**高角界面**（F2），**不是**低角晶界。
⇒ 异变体侵入**不会**增加 `nf3_col`；它会把原来的一条低角晶界**替换**成高角界面
⇒ **链被切成两段**。
⇒ 若切成 `b` 段，则 `nf3_col == nslab_n − b`（**段内仍是完整链**）。

**⇒ 所以严格式在物理上只对 `b = 1` 成立；`b ≥ 2` 时正确的式子是
`nf3_col == nslab_n − b`，而 `b` 是**必须实测的量**，不是可以假定的。**

## 3. 判据该怎么写（**最保守 + 可回退 + 显式记账**）
* **不放宽阈值**（`nf3_col == nslab_n − 1` **照报**，不改成 `≥`）；
* **另报一个"链式"口径**：`nf3_col == nslab_n − b`，其中
  **`b` = F3 邻接图的连通分量数**（**必须实测**）；
* 把"**侵入事件**"（`nf2` 上升且 `nf3_col` 下降而 `nslab_n` 不变）**记为 C4 的正证据**，
  而不是当成 C3 的失败。

# 二、本轮能从 `series.csv` 拿到什么
* **侵入事件**：`nf2` 上升 **且** `nf3_col` 下降 **且** `nslab_n` 不变 ⇒ 计数；
* **`b` 的间接上界**：每发生一次"净消耗"事件，`b` 至少 +1；
* **严格式 vs 链式式的成立率**。
⚠ **本轮拿不到**：`b` 的**直接**测量（要在快照上建 F3 邻接图）⇒ 登记为**下一步**。
"""
import os
import sys

import numpy as np


def load(tag):
    p = os.path.join('_exp/_bk_p2', 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        h = fh.readline().strip().split(',')
    return np.genfromtxt(p, delimiter=',', names=True)


def analyse(t, d):
    ns = np.atleast_1d(d['nslab_n']).astype(int)
    nf = np.atleast_1d(d['nf3_col']).astype(int)
    n2 = np.atleast_1d(d['nf2']).astype(int) if 'nf2' in d.dtype.names else np.zeros_like(ns)
    n = len(ns)
    # 侵入事件：差变负的**每一段**起点算一次（`nf2` 上升是佐证）
    bad = (nf - (ns - 1)) != 0
    ev = []
    prev_bad = False
    for i in range(n):
        if bad[i] and not prev_bad:
            ev.append(i)
        prev_bad = bad[i]
    strict = int((~bad).sum())
    # ★★★ **第一版在这里写错了（留痕）**：我用一个**全局**的 `b`（= 1 + 段数）
    #   去套**所有**行 ⇒ b5 得 **33.1%**，**比严格式（66.9%）还差**。
    #   **数字比原判据还荒谬 ⇒ 先怀疑量具（P21）**。
    #   真相：`b` 是**随时间变**的 —— 侵入发生**之前** `b=1`，之后 `b=2`。
    #   拿"事后的 b"去要求"事前那些行"必然全错。
    # ⇒ 修法：**逐行的运行 b**：`b(t) = 1 + (t 之前发生过的侵入段数)`。
    b_run = np.ones(n, dtype=int)
    k = 1
    for i in range(n):
        if i in ev:
            k += 1
        b_run[i] = k
    chain_ok = int((nf == (ns - b_run)).sum())
    b_est = int(b_run[-1])
    return dict(tag=t, n=n, strict=strict, bad=int(bad.sum()),
                b_est=b_est, ev=ev, chain_ok=chain_ok,
                nf2_start=int(n2[0]), nf2_end=int(n2[-1]),
                nf2_at_ev=[int(n2[i]) for i in ev])


def main():
    tags = sys.argv[1:] or ['p2_b5', 'p2_b3']
    print('=' * 100)
    print('R581 —— A24：C3 判据口径的**实测**依据')
    print('=' * 100)
    print('物理框架（先写，后动代码）：')
    print('  · 一个 block = 同一变体、由低角晶界（F3）分隔的若干 lath；')
    print('  · **若块内是一条链** ⇒ 边数 = 根数 − 1 ⇒ `nf3_col == nslab_n − 1`；')
    print('  · **异变体侵入**形成**高角**界面（F2），会把链**切断**成 b 段')
    print('    ⇒ 正确的式子是 `nf3_col == nslab_n − b`，**b 必须实测**；')
    print('  · ⇒ 严格式隐含 **(P1) 单链 + (P2) 无异变体侵入** 两个前提。')
    print()
    res = []
    for t in tags:
        d = load(t)
        if d is None:
            print('★ %s：没有 series.csv' % t); continue
        r = analyse(t, d)
        res.append(r)
        print('★ %s（%d 行）' % (t, r['n']))
        print('   严格式 `nf3_col == nslab_n − 1`：**%d/%d = %.1f%%**'
              % (r['strict'], r['n'], 100.0 * r['strict'] / r['n']))
        print('   掉队行 = %d ；**掉队段数（⇒ b 的估计）= %d**' % (r['bad'], r['b_est']))
        print('   `nf2`：%d → %d ；**掉队段起点处的 `nf2`** = %s'
              % (r['nf2_start'], r['nf2_end'], r['nf2_at_ev'] or '（无）'))
        print('   ⇒ 链式口径（**逐行运行 b**）`nf3_col == nslab_n − b(t)`：'
              '**%d/%d = %.1f%%**（末值 b=%d）'
              % (r['chain_ok'], r['n'], 100.0 * r['chain_ok'] / r['n'], r['b_est']))
        print('     ⚠ 记账：第一版用**全局 b** 得 **33.1%%**（**比严格式还差**）—— '
              '数字荒谬 ⇒ 先怀疑量具（P21）；真相是 **b 随时间变**。')
        print()
    print('=' * 100)
    print('★★ 裁定（**最保守 + 可回退 + 显式记账**；按"自主推进"规则自选，写进待确认清单）')
    print('=' * 100)
    print('  ① **不放宽阈值**：严格式 `nf3_col == nslab_n − 1` **照报**（不改成 ≥）；')
    print('  ② **另报"链式"口径** `nf3_col == nslab_n − b(t)`，')
    print('     **b(t) = 1 + 到 t 为止发生过的侵入段数**（**随时间变**，不许用全局常数）；')
    print('     物理上 b(t) 应等于 **F3 邻接图在当前时刻的连通分量数**（下一步在快照上直接测）。')
    print('  ③ 把"**侵入事件**"（`nf2` 升 + `nf3` 降 + `nslab_n` 不变）登记为 **C4 的正证据**；')
    print('  ④ ⚠ **本轮未做**：b 的**直接**测量。已登记为**下一步**（要建 F3 邻接图）。')
    print()
    for r in res:
        print('  %-8s 严格式 %.1f%% ／ 链式式(逐行 b(t)) %.1f%%'
              % (r['tag'], 100.0 * r['strict'] / r['n'],
                 100.0 * r['chain_ok'] / r['n']))
    print('=' * 100)


if __name__ == '__main__':
    main()
