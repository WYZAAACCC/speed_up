#!/usr/bin/env bash
# _run_branch_xiang.sh --- 用 Xiang 2022 Table 1 的全部 12 个惯习面法向对一遍我们的候选轴
#
# 出处（子代理全文取证，β 母相立方系，逐字核对）：
#   Xiang H, Van Paepegem W, Kestens LAI, Materials 15 (2022) 5325, PMC9369925, Table 1
#   表题逐字："Predicted habit plane normal and shear vector from Equation (4)
#              in the parent phase reference system."
#   结构：Variant 单元格 rowspan=2 ⇒ 6 个 correspondence variants × 2 个解 = 12 组
#   ★ 论文 §5.1 的 Table 8 是**微弹性判据**的极小点，且论文说它与 PTMT **第 2 个解**
#     只差 0.213°（与第 1 个解差 88.967°）⇒ **Table 8 的 n ≈ 每变体的第二个解**。
#
# 因此本对照要回答两件事：
#   (a) Xiang 的 12 个 m 是否都能在我们的 24 个候选（12 变体 × {n1,n2,a1,a2}）里找到 <2° 的匹配；
#   (b) 匹配是否**一致地落在同一支**（我们预期是 n2/a1 那支）——
#       若一致 ⇒ **选支定案**；若一半落 A 支一半落 B 支 ⇒ 变体编号对应关系还需对齐。
set -u
cd "$(dirname "$0")"
M=""
M="$M;-0.7147,-0.4946,0.4946"      # v1 解1（= Table 8 的第 1 解，离微弹性极小 88.97°）
M="$M;-0.7147,0.4946,-0.4946"      # v1 解2（≈ Table 8 微弹性极小点）
M="$M;-0.7147,0.4946,0.4946"       # v2 解1
M="$M;-0.7147,-0.4946,-0.4946"     # v2 解2
M="$M;-0.4946,-0.7147,0.4946"      # v3 解1
M="$M;0.4946,-0.7147,-0.4946"      # v3 解2
M="$M;0.4946,0.7147,0.4946"        # v4 解1
M="$M;-0.4946,0.7147,-0.4946"      # v4 解2
M="$M;-0.4946,0.4946,-0.7147"      # v5 解1
M="$M;0.4946,-0.4946,-0.7147"      # v5 解2
M="$M;0.4946,0.4946,-0.7147"       # v6 解1
M="$M;-0.4946,-0.4946,-0.7147"     # v6 解2
M="${M#;}"
exec /root/miniconda3/envs/ml/bin/python -u _chk_branch.py "--xiang-m=$M"
