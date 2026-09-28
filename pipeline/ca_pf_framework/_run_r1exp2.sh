#!/bin/bash
# ★ R1 第 2 轮：判决/筛选矩阵启动器
#   用法：bash _run_r1exp2.sh "名字|额外参数..." ...   （每个参数串是一个算例）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python

for SPEC in "$@"; do
  NAME="${SPEC%%|*}"
  EXTRA="${SPEC#*|}"
  DIR="_exp/$NAME"
  mkdir -p "$DIR"
  setsid nohup $PY -u _r1_exp.py --out "$DIR" $EXTRA \
      > "${DIR}/run.log" 2>&1 < /dev/null &
  echo "started $NAME pid=$!  args: $EXTRA"
  sleep 2
done
sleep 5
echo "=== 已启动 ==="
ps -eo pid,etimes,rss,args | grep _r1_exp | grep -v grep | cut -c1-170
