#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_blockband_check.py —— ③-8：用**现成算术**（③ 的"推导"一档）核生产配置的**块厚**是否落带。

## 为什么这么做（而不是继续找 Galindo-Nava 2015）
  * `W_BLOCK_BAND_UM` 在**生产引擎 `_bk_exp.py` 里零命中** ⇒ 「块尺寸律」**不被消费**；
  * `R507 §5` 的 `每块放得下` 已经给了**几何容量**的算式
    （`α_KM·(T_阈 − T_end)`，`T_阈` 由**核形状的弹性罚**定）
    ⇒ 它本身**就是**一条"块内根数"的物理约束，**比钢的块尺寸律更贴本体系**。

## 判据（可 FAIL）
  1. `W_block = n_块 · t` 是否落在 `W_BLOCK_BAND_UM = (1.0, 6.0) µm`；
  2. **两种口径都要报**：C-2 预言 `n = α·(M_s − T_end)` 与 几何容量 `n_geo`；
  3. **块数上界** `B_max = L²/A_f` 与 `B = L³/(n·V_lath)` 的自洽性。
"""
import sys

ALPHA = 0.041739          # 生产值（`_t5_short.py:274` / `t10B9`/`t10PROD1` 的 exp_args）
MS = 873.0
T_END = 298.0
T = 0.250e-6              # m，单根厚度（引擎 `--eng-t-nm 250`）
L = 10.0e-6               # m，盒
A_F = 1.000e-6 * 0.500e-6  # m²，足迹（plate_L 1000 nm × plate_W 500 nm）
BAND = (1.0, 6.0)         # µm
# `R507 §1` 的两个阈值（引擎同路径实测）
T_THR_DISC = 380.1        # K（带尖边圆盘）
T_THR_ELLIP = 523.8       # K（光滑椭球，**生产用的就是这个**）
SHAPE = sys.argv[1] if len(sys.argv) > 1 else "ellipsoid"

n_c2 = ALPHA * (MS - T_END)
n_geo = ALPHA * ((T_THR_ELLIP if SHAPE == "ellipsoid" else T_THR_DISC) - T_END)
t_um = T * 1e6

print(f"配置：α_KM={ALPHA}  M_s={MS}  T_end={T_END}  t={t_um:.3f} µm  "
      f"L={L*1e6:.1f} µm  A_f={A_F*1e12:.0f} nm²  核形状=**{SHAPE}**")
print(f"文献带 W_BLOCK_BAND_UM = {BAND} µm\n")
print(f"{'口径':>14} {'n（根/块）':>11} {'W_block=n·t (µm)':>17}  判定")
for nm, n in (("C-2 预言", n_c2), ("几何容量", n_geo)):
    w = n * t_um
    ok = BAND[0] <= w <= BAND[1]
    print(f"{nm:>14} {n:>11.2f} {w:>17.2f}  "
          f"{'✅ 落带内' if ok else ('⚠ 低于带下界' if w < BAND[0] else '⚠ 超带上界')}")

B_max = (L ** 2) / A_F
V_box = L ** 3
V_lath = A_F * T
print(f"\n块数上界 B_max = L²/A_f = {B_max:.1f}")
for nm, n in (("C-2 预言", n_c2), ("几何容量", n_geo)):
    B = V_box / (n * V_lath)
    print(f"  若每块 {nm} n={n:.2f} 根 ⇒ 达到「两百多根」需 B ≈ {B:.1f}"
          f"（{'✅ 在界内' if B <= B_max else '❌ **超 B_max ⇒ 几何不可能**'}）")

print(f"\n★ 生产用 `--nuc-block-target 9`（B=9）⇒ 预言总根数 = 9 × n：")
for nm, n in (("C-2 预言", n_c2), ("几何容量", n_geo)):
    print(f"   {nm}: 9 × {n:.2f} = **{9*n:.0f} 根**"
          f"（用户 ⑧ 的目标是「两百多」，nv=220）")
