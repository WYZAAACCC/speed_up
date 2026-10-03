#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_nvarbound.py --- ★★★ 变体数 `nvar` 的**结构性上限**（回答用户：块的数量是不是太少了？）

## 问题的物理
**马氏体的**自协调（self-accommodation）**本质是**多个变体**之间**互相 accommodation（形状应变抵消）****
⇒ **变体数不够 ⇒ 根本谈不上自协调。**
**⇒ 用户问得对：块的数量**是**关键，而我一直把它当成"判据④/⑥ 各自独立"。**

## 本脚本算的结构性约束（**纯算术，可复核**）
模型的场预算：`nv = nvar × m`
* 约束 1（总场数）：`nv ≥ B · n(T_end) = B × 23`
* 约束 2（每组容量）：`m ≥ 该组板条数`（**单变体结构时该组要装下全部 23 根**）
⇒ **`nvar ≤ nv / 23`**
"""
N_TEND = 23          # n(T_end) = floor(α_KM·(M_s − T_end))，引擎横幅逐字
BOX_GB_PER_FIELD = 0.16   # N=160 下约 0.16 GB/场（P23 实测）
MEM_LIMIT = 22.0          # 本机可用（P23）
TI64_VARIANTS = 12        # Ti-6Al-4V α′ 的 Burgers 变体数（文献；12 个)

print('=' * 88)
print('★ 变体数 `nvar` 的结构性上限（回答"块的数量是不是太少了"）')
print('=' * 88)
print('  约束：nv = nvar × m；nv ≥ B·n(T_end)；m ≥ n(T_end) = %d（单变体时该组要装下全部）' % N_TEND)
print('  ⇒ **nvar ≤ nv / %d**' % N_TEND)
print()
print('  %-10s %-8s %-10s %-14s %s' % ('nv', '内存(GB)', 'nvar 上限', '可表示变体数', '能否容纳 Ti64 的 12 变体？'))
print('  ' + '-' * 78)
for nv in (24, 48, 72, 96, 144, 276, 300, 600):
    gb = nv * BOX_GB_PER_FIELD
    nvmax = nv // N_TEND
    ok = '✅' if nvmax >= TI64_VARIANTS else '❌'
    mem = '✅' if gb <= MEM_LIMIT else '❌ **超内存**'
    print('  %-10d %-8.1f %-10d %-14d %s  (%s)' % (nv, gb, nvmax, nvmax, ok, mem))

print()
print('  ── 结论（**关键**）──')
print('  ① **本机内存内（nv ≤ ~137）⇒ nvar 上限 = %d**（72/23 = 3）' % (72 // N_TEND))
print('     ⇒ **最多只能表示 2–3 个变体**；')
print('  ② **要容纳 Ti-6Al-4V 的 **%d 个 Burgers 变体**，需 nv ≥ %d × %d = **%d**'
      % (TI64_VARIANTS, TI64_VARIANTS, N_TEND, TI64_VARIANTS * N_TEND))
print('     ⇒ 内存 ≈ **%.0f GB** ⇒ **远超本机 %.0f GB**（P23）。' % (TI64_VARIANTS * N_TEND * BOX_GB_PER_FIELD, MEM_LIMIT))
print()
print('  ⇒ ⇒ **所以：在「盒 ≥10 µm」+「本机 22 GB」下，**
        **变体数只能到 2–3，而真正的自协调需要 12 个变体的**合理子集**（至少 3–4 个特定变体成簇）。**')
print('  ⚠ **这解释了用户的问题**：**`n_var_sig = 2` **不等于**自协调** ——')
print('     它只是"有 2 个变体"，而**自协调要求这些变体的**形状应变互相抵消****（需要**特定的变体组合**）。')
