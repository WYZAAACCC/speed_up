#!/bin/bash
# ★★ 阶段③的**自走**驱动：等 e4/e6 结束 → 出判定 → 启动 e7 与实验2(单个等轴)
#    → 等它们结束 → 出判定 → 启动 e7b（若有槽位）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python

waitfor () {   # waitfor <名字...>  —— 全部退出才返回
  while true; do
    n=0
    for d in "$@"; do
      c=$(pgrep -c -f "_r1_exp.py --out _exp/$d" 2>/dev/null || true)
      [ -z "$c" ] && c=0
      n=$((n + c))
    done
    [ "$n" = "0" ] && return 0
    sleep 60
  done
}

echo "### 1) 等 e4_lath6 / e6_mid6"
waitfor e4_lath6 e6_mid6
echo "### 1) 完成 @ $(date +%H:%M:%S)"
$PY -u _r1_snapinfo.py --series _exp/e4_lath6 --kv 1 --shape lath 2>&1 | tail -22
$PY -u _r1_snapinfo.py --series _exp/e6_mid6  --kv 1 --shape mid  2>&1 | tail -22
$PY -u _r1_analyze.py _exp/e4_lath6 _exp/e6_mid6 --skip 3 --block 2>&1 | tail -60

echo
echo "### 2) 启动 e7（自协调，随机初值 seed=1）与实验2（单个等轴）"
bash _run_r1phase3b.sh e7
sleep 10
bash _run_r1phase3b.sh equi1

echo "### 2) 等 e7_selfac / equi192_ns4"
waitfor e7_selfac equi192_ns4
echo "### 2) 完成 @ $(date +%H:%M:%S)"
$PY -u _r1_snapinfo.py --series _exp/e7_selfac --kv 1 --shape mid 2>&1 | tail -22
$PY -u _r1_analyze.py _exp/e7_selfac _exp/equi192_ns4 --skip 3 --block 2>&1 | tail -60
echo "### S-1 自协调判定（e7 末态）"
$PY -u _r1_selfac.py --snap "$(ls -1 _exp/e7_selfac/snap_*.npz | tail -1)" --nrand 24 2>&1 | tail -25

echo
echo "### 3) 启动 e7b（全 12 变体随机）"
bash _run_r1phase3b.sh e7b
waitfor e7b_selfac12
echo "### 3) 完成 @ $(date +%H:%M:%S)"
$PY -u _r1_selfac.py --snap "$(ls -1 _exp/e7b_selfac12/snap_*.npz | tail -1)" --nrand 24 2>&1 | tail -25
echo "### 全部完成"
