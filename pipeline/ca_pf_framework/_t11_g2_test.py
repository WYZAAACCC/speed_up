#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_g2_test.py —— R623 **G2（放开异变体界面形核）** 的单元测试。

## 为什么要写成单元测试（而不是只跑冒烟）
  那条守卫埋在 `nucleate()` 的
    `if n_stack > 0` → `attach 失败后` → `for _try in range(16)` → `for j in range(4)`
  **四层嵌套**里 ⇒ 小盒冒烟**根本走不到**（实测 `cov=0`、`iface_*` 一个都不出现
  ⇒ **判据没有分辨力**，R581 **P43**）。
  ⇒ 直接把守卫抽成纯函数 `_test_stack_iface_ok(cover, reg, k_new, vmap)`，
    单元测试**确定性地**喂几何进去。

## 要证的命题（可 FAIL）
  P1 **默认（开关关）**：覆盖区含别的场 ⇒ **拒**（`ok=False`）—— 这就是"第 2/3 波
     发生不了"的根因。
  P2 **开关开 + 异变体**：覆盖区 = 母相 ∪ **恰好一个**场，且**变体不同** ⇒ **放行**。
  P3 **开关开 + 同变体**：变体**相同** ⇒ **拒**（同变体贴同变体走原 `stack` 语义）。
  P4 **开关开 + 多个场**：覆盖区含 **≥2** 个场 ⇒ **拒**（不许一次贴多根）。
  P5 **纯母相**：任何设置下都**放行**（原有行为不得被破坏）。
  P6 **字段缺失**（`vmap` 为空 / 场号查不到）⇒ **拒**（不能因为查不到就当异变体）。
"""
import sys

import numpy as np

sys.path.insert(0, ".")
import windowB_surface as WS  # noqa: E402

N = 8
g = WS.LevelSetMulti(N, 1.0, nv=4, gamma=0.0, Mob=1.0)

# ⚠ 2026-10-05 修（我自己的测试数据错误）：第一版写成
#     `reg[:, :, :4] = 1 ; reg[:, :, 4:] = 2` —— **把整个盒子填满了**
#   ⇒ **一个母相胞都没有** ⇒ `cover_par[0,0,0]` 指向的是**场 1**
#      ⇒ "纯母相"那条用例实际测的是"贴着场 1" ⇒ 返回 `why='iface'`。
#   **正解**：必须**留出母相**。下面把场只放在 z ∈ [2,6)，z<2 与 z≥6 是母相。
reg = np.zeros((N, N, N), np.int16)
reg[:, :, 2:4] = 1          # 场 1（z = 2,3）
reg[:, :, 4:6] = 2          # 场 2（z = 4,5）
# 现在 z = 0,1,6,7 是母相(0)
cover_par = np.zeros((N, N, N), bool)
cover_par[0, 0, 0] = True                       # 纯母相（z=0）
cover_one = np.zeros((N, N, N), bool)
cover_one[0, 0, 0] = True                       # 母相
cover_one[0, 0, 2] = True                       # + 场1（恰好一个）
cover_two = np.zeros((N, N, N), bool)
cover_two[0, 0, 0] = True                       # 母相
cover_two[0, 0, 2] = True                       # + 场1
cover_two[0, 0, 5] = True                       # + 场2  ⇒ 两个

VM = {1: 1, 2: 4, 3: 2, 4: 3}   # 场→变体：场1=V1、场2=V4、场3=V2、场4=V3
ON = {'nuc_iface_nucleation': True}     # 模拟开关打开时调用点的行为

# ⚠ 记账：`_test_stack_iface_ok` 是**纯几何谓词**，**不含开关门控**
#   —— 门控在调用点（"要不要调它"）。所以本测试把两件事分开测：
#     (a) 谓词本身的分辨力（P2–P6）；
#     (b) 开关关时调用点是否**不调它**（P1，用开关字典模拟）。
CASES = [
    # 名称,                                      开关, cover,     k_new, vmap, 期望 ok, 期望 why
    ("P1a 开关**关** ⇒ 调用点应走原判据（此处只验语义）", None, cover_one, 3, VM, None, None),
    ("P2 开关开 + 异变体（场1=V1，新场3=V2）⇒ 放行", ON, cover_one, 3, VM, True, 'iface'),
    ("P3 同变体（新场1 = 场1 的变体 V1）⇒ 拒",       ON, cover_one, 1, VM, False, 'samevar'),
    ("P4 覆盖含两个场 ⇒ 拒",                        ON, cover_two, 3, VM, False, 'multi'),
    ("P5 纯母相 ⇒ 放行（原有行为）",                 ON, cover_par, 3, VM, True,  'parent'),
    ("P6a vmap 为空 ⇒ 拒",                          ON, cover_one, 3, {}, False, 'samevar'),
    ("P6b 场号查不到 ⇒ 拒",                          ON, cover_one, 9, VM, False, 'samevar'),
]

print("=" * 96)
print(f"N={N}  场→变体 vmap={VM}  （场1=V1, 场2=V4, 场3=V2, 场4=V3）")
print(f"reg 布局：z∈{{0,1,6,7}} = 母相(0)；z∈{{2,3}} = 场1；z∈{{4,5}} = 场2")
print("=" * 96)
ok_all = True
for name, sw, cov, kn, vm, want_ok, want_why in CASES:
    if sw is None:
        # 开关关：调用点**不调**该谓词，而走 `(reg[cover]==0).all()`
        got_ok = bool((reg[cov] == 0).all())
        got_why = '（调用点走原判据）'
        good = (got_ok is False)
        ok_all &= good
        print(f"  [{'PASS' if good else '**FAIL**'}] {name}")
        print(f"          原判据 (reg[cover]==0).all() = {got_ok}"
              f"   期望 False（这就是「第 2/3 波发生不了」的根因）")
        continue
    got_ok, got_why = g._test_stack_iface_ok(cov, reg, kn, vm)
    good = (got_ok == want_ok) and (got_why == want_why)
    ok_all &= good
    print(f"  [{'PASS' if good else '**FAIL**'}] {name}")
    print(f"          实测 ok={got_ok} why={got_why!r}"
          f"   期望 ok={want_ok} why={want_why!r}")

print("\n" + "=" * 96)
print("★ 分辨力自检（R581 P43）：负对照必须与正对照**不同**")
neg, _ = g._test_stack_iface_ok(cover_one, reg, 3, VM)     # 异变体
pos, _ = g._test_stack_iface_ok(cover_one, reg, 1, VM)     # 同变体
print(f"   异变体（场1=V1 → 新场3=V2） ok={neg}")
print(f"   同变体（场1=V1 → 新场1=V1） ok={pos}")
print(f"   ⇒ {'有分辨力 ✅' if neg != pos else '**没有分辨力（判据恒真/恒假）** ❌'}")
ok_all &= (neg != pos)
print("=" * 96)
print("总判定：" + ("**全部 PASS**" if ok_all else "**有 FAIL，必须继续查**"))
print("=" * 96)
sys.exit(0 if ok_all else 1)
