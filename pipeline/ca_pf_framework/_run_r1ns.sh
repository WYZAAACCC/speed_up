#!/bin/bash
# 判据前置：`norm_smooth` **不得是需要精调的魔法参数**（本项目对 `band_cells` 用过同一条标准）。
# 同 Δx、同种子，只改 norm_smooth ∈ {1, 2, 4}；已有 0（base）与 2（ns2）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
COMMON="--case mid --seed-scale 2 --N 96 --dx-nm 250 --steps 600 --every 4 \
        --snap-every 40 --nthreads 3 --max-hours 1.0 --beta-h 3.5 --beta-w 2.3 --ed-diag"

run () {
  local NAME="$1"; shift
  local DIR="_exp/$NAME"; mkdir -p "$DIR"
  setsid nohup $PY -u _r1_exp.py --out "$DIR" $COMMON "$@" \
      > "${DIR}/run.log" 2>&1 < /dev/null &
  echo "started $NAME pid=$!  extra: $*"
  sleep 2
}
run mid250_ns1 --norm-smooth 1
run mid250_ns4 --norm-smooth 4
sleep 5
ps -eo pid,etimes,rss,args | grep _r1_exp | grep -v grep | cut -c1-120
free -g | head -2
