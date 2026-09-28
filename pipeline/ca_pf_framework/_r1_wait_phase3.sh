#!/bin/bash
# 等 e4/e6/e5/e7 全部结束，然后自动出**阶段③判定**
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TARGETS="$*"
echo "等待：$TARGETS"
while true; do
  n=0
  for d in $TARGETS; do
    c=$(pgrep -c -f "_r1_exp.py --out _exp/$d" 2>/dev/null || true)
    [ -z "$c" ] && c=0
    n=$((n + c))
  done
  [ "$n" = "0" ] && break
  sleep 60
done
echo "全部结束"
echo
echo "################ 阶段③ 块判定 ################"
$PY -u _r1_analyze.py $(for d in $TARGETS; do echo -n "_exp/$d "; done) --skip 3 --block 2>&1 | tail -120
