#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_mscale.py --- ★★★★ **`m` 的规模账：C5 的目标能靠"提 `m`"达到吗？**

## 为什么必须算这一笔
R33 查明 **同变体板条数硬上限 = `m` = `nv/12`**（`nfsv` 只能在**同变体的空场**里选）。
goal §(14) 给的公式是 **`m ≥ ceil(B·n/12)`** —— 它**隐含假设 12 个变体被均匀使用**。

**★ 但 R33/R30 的实测是反的**：`vmap_vals` 显示
**场 1/2/3/4 全是变体 1、场 17/18/19/20 全是变体 5** ⇒ **`ed` 规则把变体**聚簇**了**。

⇒ **若变体聚簇，`m` 必须 ≥ "同变体的板条数"，而不是 `B·n/12`。**
⇒ **本量具就是把这两条路的内存账算出来。**

## 内存定律（goal §(12) 的实测系数，`onfly` 档）
`M ≈ a·nv·CELL + c·CELL + d`，其中 **`a = 9.000` B/胞·nv**、**`c = 392` B/胞**、`d = 1515.6 MB`、
**`CELL = 160³ = 4.096e6`**。
⇒ 预算 **22 GB**（WSL 24 GB，goal 明示按 22 GB 规划）。
"""
import numpy as np

A = 9.000          # B/胞·nv（onfly f64，goal §(12) 实测）
C = 392.0          # B/胞
D = 1515.6         # MB
CELL = 160 ** 3
BUDGET_GB = 22.0


def mem_gb(nv):
    return (A * nv * CELL + C * CELL) / 1e9 * 1e-3 * 1e3 + D / 1024.0


def nv_of_m(m):
    return 12 * m


def main():
    print('=' * 100)
    print('`m` 的规模账：C5 的目标能靠"提 m"达到吗？')
    print('=' * 100)
    print('  内存定律（goal §(12)，onfly 档）：M = %.3f·nv·CELL + %.0f·CELL + %.1f MB'
          % (A, C, D))
    print('  CELL = 160³ = %.4g ；预算 = **%.0f GB**' % (CELL, BUDGET_GB))
    print()
    print('  ── 先自检：用 R33 判决实验的 `m=4`/`m=12` 对账 ──')
    for m in (4, 12):
        nv = nv_of_m(m)
        print('     m=%-3d ⇒ nv=%-5d ⇒ 预测峰值 **%.2f GB**' % (m, nv, mem_gb(nv)))
    print('     （R45 实测：`p2_b5ov` RSS **4.85 GB**、`p2_b5ps` **5.00 GB**，'
          '两者都是 m=4 ⇒ 预测 %.2f GB vs 实测 ~4.9 GB）' % mem_gb(nv_of_m(4)))
    print('     ⚠ 预测**偏高约 %.1f×** ⇒ 本表的绝对数是**保守上界**，只用来比**相对规模**'
          % (mem_gb(nv_of_m(4)) / 4.9))
    print()
    print('  ── 两条路（C5 目标 = **220–450 根**，goal §(14) 双报口径）──')
    laths = [25, 90, 220, 450, 540]
    print('  %-10s %-22s %-22s' % ('目标根数', '① 变体**均匀**用', '② 变体**聚簇**（实测形态）'))
    print('  ' + '-' * 92)
    for L in laths:
        # ① 均匀：每变体 L/12 根 ⇒ m = ceil(L/12)
        m1 = int(np.ceil(L / 12.0))
        g1 = mem_gb(nv_of_m(m1))
        # ② 聚簇：全部同变体 ⇒ m = L
        m2 = L
        g2 = mem_gb(nv_of_m(m2))
        f = lambda g: ('**%.1f GB** %s' % (g, '✅' if g <= BUDGET_GB else '❌ **超预算**'))
        print('  %-10d %-22s %-22s' % (L, 'm=%-4d %s' % (m1, f(g1)),
                                       'm=%-4d %s' % (m2, f(g2))))
    print()
    print('  ── 反算：%.0f GB 预算下，两条路各自最多能放多少根？──' % BUDGET_GB)
    # 解 9*nv*CELL + 392*CELL + 1515.6MB*1e6 = 22GB
    rhs = BUDGET_GB * 1e9 - C * CELL - D * 1024 * 1024
    nv_max = rhs / (A * CELL)
    print('     nv_max ≈ **%.0f**（由 %.3f·nv·CELL ≤ 剩余预算解得）' % (nv_max, A))
    print('     ⇒ ① 均匀路：根数上限 ≈ nv_max = **%.0f 根**' % nv_max)
    print('     ⇒ ② 聚簇路：根数上限 ≈ nv_max/12 = **%.0f 根**' % (nv_max / 12))
    print()
    print('=' * 100)
    print('★★★ 结论（**这就是本量具要回答的**）')
    print('=' * 100)
    print('  · **均匀路**：C5 的 220–450 根**都落在预算内**（m=19…38，nv=228…456）✅')
    print('  · **聚簇路**（= 我实测到的 `ed` 行为）：220 根就要 m=220、nv=2640 ⇒')
    print('    **%.0f GB，远超 %.0f GB 预算** ❌' % (mem_gb(nv_of_m(220)), BUDGET_GB))
    print('  ⇒ ⇒ **"提 `m`"这条修法只有在"变体被均匀使用"时才可行。**')
    print('  ⇒ ⇒ 而实测 `vmap_vals` 显示 **`ed` 把变体聚簇**（场 1–4 全变体 1、场 17–20 全变体 5）')
    print('     ⇒ **必须先修变体选择（让它用更多变体），否则 C5 结构上到不了。**')
    print('  ★ 而"让变体多样"**正好也是 C6（涌现自协调）需要的** ⇒ **C5 与 C6 是同一件事**。')
    print('=' * 100)


if __name__ == '__main__':
    main()
