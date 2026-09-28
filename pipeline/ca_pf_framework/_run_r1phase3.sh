#!/bin/bash
# ★★★ R1 阶段③：多个晶核 → 块（实验 4/5/6/7）
#   全部：R24 标准域（N=192 / Δx=125 nm / 24 µm 盒）+ 已验收的 `norm_smooth=4`
#   分组判据见 `_r1_variant_groups.py`：block = **同一变体**；packet = V1+V2 等
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python

run () {   # run <名字> <case> <nseed> <variants> <gap_nm> [额外参数]
  local NAME="$1" CASE="$2" NS="$3" VAR="$4" GAP="$5"; shift 5
  local DIR="_exp/$NAME"; mkdir -p "$DIR"
  setsid nohup $PY -u _r1_exp.py --out "$DIR" --case "$CASE" \
      --N 192 --dx-nm 125.0 --steps 700 --every 5 --snap-every 25 \
      --nseed "$NS" --layout line_w --line-gap-nm "$GAP" --variants "$VAR" \
      --beta-h 3.5 --beta-w 2.3 --adv proj2 --nthreads 6 \
      --reinit-band 6.0 --max-hours 2.6 --norm-smooth 4 "$@" \
      > "${DIR}/run.log" 2>&1 < /dev/null &
  echo "started $NAME (case=$CASE nseed=$NS variants=$VAR gap=${GAP}nm) pid=$!  extra: $*"
  sleep 3
}

case "$1" in
  e4) run e4_lath6   lath 6 1 1500 ;;          # 6 根平行板条核（同变体）⇒ 应成一个 block
  e5) run e5_equi6   equi 6 1 1500 ;;          # 6 个等轴核（同变体）
  e6) run e6_mid6    mid  6 1 1500 ;;          # 6 个中间形核（同变体）
  e7) run e7_selfac  mid  6 "1,2" 1500 ;;      # 同一 packet 内**两个变体**交替 ⇒ 自协调
  *)  echo "用法: bash _run_r1phase3.sh {e4|e5|e6|e7}" ;;
esac
sleep 5
echo "=== 已启动 ==="
ps -eo pid,etimes,rss,args | grep _r1_exp | grep -v grep | cut -c1-120
free -g | head -2
