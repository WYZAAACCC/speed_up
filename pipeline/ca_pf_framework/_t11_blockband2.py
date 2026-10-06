#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_blockband2.py —— ③-8 第二轮：**统一用引擎自己的几何**重算（我第一版混了口径）。

## 我第一版犯的错（留档）
  同一段里混了**两套体积**：
    * `V_lath = A_f · t`（**物理足迹** `plate_L×plate_W×eng_t`）
    * `V_box/V_lath`（**引擎椭球几何**：`R=320 nm`、`elong=7.0`）
  两者差 **3.76 倍** ⇒ 块数算出 333 vs 89，**自相矛盾**。
  ⇒ 必须**只用一套**，并**两套都报**（`AGENTS.md` P30：同名异量先对单位）。

## 引擎几何（从 `t10B9`/`t10PROD1` 的 `exp_args` 回读）
  `eng_r_nm=320`、`eng_elong=7.0`、`eng_t_nm=250`、`plate_L=1000`、`plate_W=500`
  ⇒ `seed_plate` 里的核：半轴 `R·elong`（长）× `R`（宽）× `t/2`（厚）
"""
ENG_R = 320e-9
ENG_ELONG = 7.0
ENG_T = 250e-9
PLATE_L = 1000e-9
PLATE_W = 500e-9
L = 10.0e-6
BAND = (1.0, 6.0)

# ① 引擎椭球（`seed_plate` 的实际几何）
V_ell = (4.0 / 3.0) * 3.141592653589793 * (ENG_R * ENG_ELONG) * ENG_R * (ENG_T / 2.0)
# ② 物理足迹盒（plate_L × plate_W × t）
V_box_phys = PLATE_L * PLATE_W * ENG_T
V_box = L ** 3

print("=== 两套体积（**必须分开报**）===")
print(f"  ① 引擎椭球 4/3·π·(R·elong)·R·(t/2) = {V_ell*1e18:.4f} µm³")
print(f"  ② 物理足迹 {PLATE_L*1e9:.0f}×{PLATE_W*1e9:.0f}×{ENG_T*1e9:.0f} nm = "
      f"{V_box_phys*1e18:.4f} µm³")
print(f"  比值 ①/② = {V_ell/V_box_phys:.2f}×  ← **3.76 倍差异**（我第一版混用了这两者）")
print(f"  盒体积 L³ = {V_box*1e18:.1f} µm³")

print("\n=== 块厚（判据 1）===")
t_um = ENG_T * 1e6
for nm, n in (("C-2 预言 24", 24.0), ("几何容量 9.42", 9.42)):
    w = n * t_um
    print(f"  {nm:>16} 根/块 ⇒ W_block = {w:.2f} µm  "
          f"{'✅ 落带内' if BAND[0] <= w <= BAND[1] else '⚠ 出带'}")

print("\n=== 块数（判据 2，**两套体积各算一遍**）===")
for lbl, V in (("① 引擎椭球", V_ell), ("② 物理足迹", V_box_phys)):
    print(f"\n  用 {lbl} V_lath = {V*1e18:.4f} µm³：")
    for nm, n in (("C-2 预言", 24.0), ("几何容量", 9.42)):
        # 每块 n 根堆叠 ⇒ 块体积 = n·V_lath
        B_sat = V_box / (n * V)
        print(f"    {nm:>10} n={n:>5.2f} ⇒ 要填满盒需 B = {B_sat:>7.1f} 块"
              f"（B_max=L²/A_f=200 ⇒ {'✅ 界内' if B_sat<=200 else '❌ 超界'}）")
    print(f"    ⇒ 生产 B=9 时的**总根数** = 9 × n：", end="")
    print("  ".join(f"{nm}={9*n:.0f}" for nm, n in (("C-2", 24.0), ("geo", 9.42))))

print("\n=== ⚠ 一处必须登记的口径冲突 ===")
print(f"  引擎椭球的**长半轴** R·elong = {ENG_R*ENG_ELONG*1e6:.3f} µm")
print(f"  而 `plate_L` 声明的是 {PLATE_L*1e6:.3f} µm")
print(f"  ⇒ 引擎核的**全长** {2*ENG_R*ENG_ELONG*1e6:.2f} µm 是声明长度的 "
      f"{2*ENG_R*ENG_ELONG/PLATE_L:.2f} 倍")
print("  ⇒ 『一根板条 = plate_L×plate_W×t』这条口径在**引擎几何下不成立**。")
