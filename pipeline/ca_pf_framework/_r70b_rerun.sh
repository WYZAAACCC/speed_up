#!/bin/bash
# R70b: 用**修好的算子**（分位数口径，抗长指）重跑两档，看"棘轮"是否减弱。
#   判据：`d(a)` 应从旧的 3.818（N=10）降向"面推进×2" ≈ 1.7–2.0。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
echo "=== 重跑两档（修好的算子）  $(date '+%F %T')"
for NP in 10 20; do
  TAG="fq${NP}"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  echo "--- $TAG  $(date '+%T')"
  $PY -u _bk_exp.py --arm dry --N 64 --dx-nm 62.5 --laths 1 \
    --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --facet-proj "$NP" \
    --steps 400 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
    --tag "$TAG" --out _exp/_bk_mb > "_w2_r70b_${TAG}.log" 2>&1 &
  while [ "$(jobs -r | wc -l)" -ge 2 ]; do sleep 5; done
done
wait
echo "=== 完成 $(date '+%F %T')"
echo '### 读数对照（旧 min/max 口径 vs 新分位数口径）'
for T in fp10 fq10 fp20 fq20; do
  d="_exp/_bk_mb/dry_$T"
  [ -f "$d/series.csv" ] || continue
  n=$(tail -1 "$d/series.csv" | cut -d, -f1)
  [ "$n" -ge 300 ] || continue
  printf -- '--- %s\n' "$T"
  timeout 600 $PY _r53_v2run.py "$d" 2>&1 | tail -2 | head -1
done
