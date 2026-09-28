#!/usr/bin/env bash
# _run_dxfine.sh --- Δx 收敛扫描的**细网格延伸**（把 `ΔL/ΔW` 从 4.38 往靶 9 推）
#
# 为什么可以加密而**不**变贵
# --------------------------
# 单板条诊断**不需要 10.67 µm 的大盒子**：本轮实测该构型下板条在 3750 nm 标称位移内
# 只长到 **≈2.4 µm**（`_w2_dx2soft.log` step 300：L=2374.2 nm）。
# ⇒ 换 **4.0 µm 盒**即可，于是 `N` 随 Δx 缩小而**不必暴涨**：
#       Δx=83.35 → N=48 ; Δx=50 → N=80 ; Δx=33.34 → N=120
#   代价 ∝ N³·steps ∝ (L_box/Δx)³·(1/Δx) = Δx⁻⁴，但 L_box 从 10.67 降到 4.0 已经
#   省掉 (4/10.67)³ ≈ 19 倍 ⇒ **细网格第一次变得可负担**。
#
# ★ 盒子无关性的既有证据（不是假设）
# ---------------------------------
# `_w2_dx1.log`（N=64 / 10.67 µm）与更早的 N=96 / 16 µm 跑在**同一 Δx=166.7** 上给出
# **逐位相同**的 L/W/T。本轮再加一个**重叠点** A（Δx=83.35 / N=48 / 4.0 µm）与
# `_w2_dx2soft.log`（Δx=83.35 / N=128 / 10.67 µm）对照 ⇒ 若不吻合，本脚本的结论作废。
#
# 全部带 `--elastic-soft`（引擎 b9565f69，F-2 两处都修完）—— 因为它已证明**可叠加**
set -u
cd "$(dirname "$0")"

echo "########## Δx 细网格延伸（soft=True）  start=$(date -Is) ##########"

# A：重叠点（与 _w2_dx2soft.log 同 Δx，但盒 4.0 µm）⇒ 盒子无关性检查
bash _run_arm.sh _w2_dxf1.log W2-DXF1 _probe_shape.py \
    --N 48 --dx-nm 83.35 --steps 300 --every 50 --arms aniso --elastic-soft
echo "### DXF1 rc=$? @ $(date -Is)"

# B：Δx=50 nm（t/Δx=14、R/Δx=10，R13 宽裕）
bash _run_arm.sh _w2_dxf2.log W2-DXF2 _probe_shape.py \
    --N 80 --dx-nm 50.0 --steps 500 --every 84 --arms aniso --elastic-soft
echo "### DXF2 rc=$? @ $(date -Is)"

# C：Δx=33.34 nm（t/Δx=21、R/Δx=15）
bash _run_arm.sh _w2_dxf3.log W2-DXF3 _probe_shape.py \
    --N 120 --dx-nm 33.34 --steps 750 --every 125 --arms aniso --elastic-soft
echo "### DXF3 rc=$? @ $(date -Is)"

echo "########## 结束 end=$(date -Is) ##########"
