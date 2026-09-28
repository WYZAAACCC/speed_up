#!/bin/bash
# ★★★ R1 第 2 轮：把**饱和后的推荐值 `norm_smooth=4`** 搬到 R24 标准域（N=192 / Δx=125 nm）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
run () {
  local NAME="$1"; local CASE="$2"; shift 2
  local DIR="_exp/$NAME"; mkdir -p "$DIR"
  setsid nohup $PY -u _r1_exp.py --out "$DIR" --case "$CASE" \
      --N 192 --dx-nm 125.0 --steps 700 --every 4 --snap-every 20 \
      --kv 1 --beta-h 3.5 --beta-w 2.3 --adv proj2 --nthreads 8 \
      --reinit-band 6.0 --max-hours 2.6 --ed-diag "$@" \
      > "${DIR}/run.log" 2>&1 < /dev/null &
  echo "started $NAME (case=$CASE) pid=$!  extra: $*"; sleep 2
}
run mid192_ns4 mid  --norm-smooth 4
run lath192_ns4 lath --norm-smooth 4
sleep 5
ps -eo pid,etimes,rss,args | grep _r1_exp | grep -v grep | cut -c1-130
free -g | head -2
