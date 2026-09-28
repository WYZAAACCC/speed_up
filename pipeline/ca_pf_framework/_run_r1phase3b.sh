#!/bin/bash
# 补齐的两只：**实验 2（单个等轴晶核）** 与 **实验 7（自协调，随机初值）**
#   全部 R24 标准域 + 已验收的 `norm_smooth=4`
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python

run () {
  local NAME="$1"; shift
  local DIR="_exp/$NAME"; mkdir -p "$DIR"
  setsid nohup $PY -u _r1_exp.py --out "$DIR" --N 192 --dx-nm 125.0 \
      --steps 700 --every 5 --snap-every 25 --beta-h 3.5 --beta-w 2.3 \
      --adv proj2 --nthreads 4 --reinit-band 6.0 --max-hours 2.6 \
      --norm-smooth 4 "$@" > "${DIR}/run.log" 2>&1 < /dev/null &
  echo "started $NAME pid=$!  args: $*"; sleep 3
}

case "$1" in
  # 实验 2：单个**等轴**晶核（用户允许不通过，但必须**做**）
  equi1) run equi192_ns4 --case equi --kv 1 ;;
  # 实验 7：6 个核，packet-1 的 {V1,V2} **随机**分配（seed=1 ⇒ 各 3 个）
  e7)    run e7_selfac   --case mid --nseed 6 --layout line_w --line-gap-nm 1500 \
             --variants "1,2" --shuffle-variants 1 ;;
  # 实验 7b：6 个核，**全部 12 变体**随机分配（seed=7 ⇒ 6 个唯一变体）
  e7b)   run e7b_selfac12 --case mid --nseed 6 --layout line_w --line-gap-nm 1500 \
             --variants "1,2,3,4,5,6,7,8,9,10,11,12" --shuffle-variants 7 ;;
  *) echo "用法: bash _run_r1phase3b.sh {equi1|e7|e7b}" ;;
esac
sleep 5
ps -eo pid,etimes,rss,args | grep _r1_exp | grep -v grep | cut -c1-100
free -g | head -2
