#!/bin/bash
# ★ R1 任务③：单个晶核实验的批量启动器
#   用法：bash _run_r1exp.sh "lath:lath mid:mid"   （每项 case:outname）
#   每个算例：标准域 24 µm / Δx=125 nm（R24）、nthreads=6、全程留痕、2 h 上限
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
STEPS=${STEPS:-400}
MAXH=${MAXH:-2.0}
TH=${TH:-6}
EVERY=${EVERY:-4}
SNAP=${SNAP:-20}

for ITEM in $1; do
  CASE="${ITEM%%:*}"
  OUT="${ITEM##*:}"
  DIR="_exp/$OUT"
  mkdir -p "$DIR"
  setsid nohup $PY -u _r1_exp.py \
      --case "$CASE" --out "$DIR" \
      --N 192 --dx-nm 125.0 \
      --steps "$STEPS" --every "$EVERY" --snap-every "$SNAP" \
      --kv 1 --beta-h 3.5 --beta-w 2.3 --norm-smooth 0 \
      --adv proj2 --nthreads "$TH" --reinit-band 6.0 \
      --max-hours "$MAXH" \
      > "${DIR}/run.log" 2>&1 < /dev/null &
  echo "started case=$CASE out=$DIR pid=$!"
  sleep 2
done
sleep 5
echo "=== 已启动 ==="
ps -eo pid,etimes,rss,args | grep _r1_exp | grep -v grep
