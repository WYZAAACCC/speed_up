#!/bin/bash
# ★★ R1 第 2 轮判决/筛选矩阵
#   全部在 **24 µm 盒**（`R24` 盒长守卫通过：24/8.1 = 2.96×），Δx=250 nm（N=96）⇒ 便宜。
#   ⚠ 记账：Δx=250 nm **不是** R24 的标准分辨率 ⇒ 本矩阵是**机理筛选**，
#     形貌的绝对值结论作废，只比**速率比 ΔL:ΔW:ΔT** 与**臂间单因素对比**。
#   种子 ×2（`--seed-scale 2`）：Δx=250 nm 下最薄方向必须 ≥2 胞 ⇒ mid 的 T=320→640 nm。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
COMMON="--case mid --seed-scale 2 --N 96 --dx-nm 250 --steps 600 --every 4 \
        --snap-every 40 --nthreads 3 --max-hours 1.0 --beta-h 3.5 --beta-w 2.3"

run () {   # run <名字> <额外参数...>
  local NAME="$1"; shift
  local DIR="_exp/$NAME"
  mkdir -p "$DIR"
  setsid nohup $PY -u _r1_exp.py --out "$DIR" $COMMON "$@" \
      > "${DIR}/run.log" 2>&1 < /dev/null &
  echo "started $NAME pid=$!  extra: $*"
  sleep 2
}

run mid250_base --ed-diag
run mid250_noel --no-elastic
run mid250_ns2  --norm-smooth 2 --ed-diag

sleep 6
echo "=== 已启动 ==="
ps -eo pid,etimes,rss,args | grep _r1_exp | grep -v grep | cut -c1-160
free -g | head -2
