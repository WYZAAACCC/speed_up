#!/bin/bash
# 判据：`norm_smooth` 必须**收敛**（不是可调魔法参数）。
# 已有 m=0(0.625) / 1(0.300) / 2(0.170) / 4(0.110)；补 m=8 / 16。
# 判据（先写死）：若 m 继续单调下降**穿过**设计值 0.100 ⇒ 平滑过头（是旋钮不是正则）；
#   若在 0.10–0.13 附近**饱和** ⇒ 收敛 ✓。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
COMMON="--case mid --seed-scale 2 --N 96 --dx-nm 250 --steps 600 --every 4 \
        --snap-every 40 --nthreads 2 --max-hours 1.0 --beta-h 3.5 --beta-w 2.3"

run () {
  local NAME="$1"; shift
  local DIR="_exp/$NAME"; mkdir -p "$DIR"
  setsid nohup $PY -u _r1_exp.py --out "$DIR" $COMMON "$@" \
      > "${DIR}/run.log" 2>&1 < /dev/null &
  echo "started $NAME pid=$!  extra: $*"; sleep 2
}
run mid250_ns8  --norm-smooth 8
run mid250_ns16 --norm-smooth 16
sleep 5
ps -eo pid,etimes,rss,args | grep _r1_exp | grep -v grep | cut -c1-110
free -g | head -2
