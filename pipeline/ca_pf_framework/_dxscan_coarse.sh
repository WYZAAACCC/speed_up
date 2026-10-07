#!/usr/bin/env bash
# Round 83：**放大盒子 / 缩小分辨率的 Δx 收敛验证**（`MEASUREMENT_SPEC R5`）
#
# 问题：D12d 只约束了"数密度"（L ≥ 4ρ^{-1/3}），而"装下一条完整板条"还需要
#       `L ≳ 2 × 板条长度`。文献 LPBF α′ 板条长 8.1 µm ⇒ 需 L ≈ 16 µm。
# 关键想法：本模型是 **Gibbs 零厚度面**（界面表示精度**不依赖分辨率**），
#       唯一硬约束是 **`t/Δx ≥ 3`**，而 t 是物理量 ⇒ `N ≥ 3L/t`。
#       t_nuc = 700 nm、L = 16 µm ⇒ **N ≥ 69** ⇒ 粗网格就能装下！
#       且 `dt ∝ Δx` ⇒ 每步物理时间更长 ⇒ 长出 8 µm 只需 ~320 步。
#
# 本脚本验证它：**固定物理构型**（单板条 R=900 nm / t=700 nm / L=10 µm），
#   只扫 Δx；步数按 `∝ 1/Δx` 取，保证**同一物理时间**（`R5` 的要求）。
#   附一档 `m=1`：检验"`norm_smooth` 按胞固定会不会在粗网格上过长"（2胞×167nm=334nm）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python

run () {  # $1=dx nm  $2=steps  $3=m
  echo "############ Δx=$1 nm  steps=$2  norm_smooth=$3  N=$((10000/$1)) ############"
  # ⛔ Round 85 修：上一版的 grep **末尾多了 `-v`**，把整个匹配**反转** ⇒ 日志恰好丢掉
  #   P-1 正对照 / 厚度偏差 / 实测长宽 / 厚向标称 / **P-4 健康度**（`R5` 要求的诊断），
  #   只留下判决句 ⇒ 那份日志**不能作为 `R5` 证据**。现在**不过滤，全量入库**。
  $PY -u _probe_LT.py --L-um 10 --dx-nm "$1" --r-nm 900 --t-nm 700 \
      --steps "$2" --norm-smooth "$3" 2>&1 | grep -v -e WindowB -e RuntimeWarning -e reinitialize
}

run 167 150 2
run 125 200 2
run  83 300 2
run 167 150 1
