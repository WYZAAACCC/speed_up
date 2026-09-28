#!/bin/bash
# 等两个 R24 确认跑自然停止（到 --max-hours 2.6 或跑完 700 步），然后自动出判定。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python

echo "等待 _exp/mid192_ns4 与 _exp/lath192_ns4 结束 …"
for i in $(seq 1 200); do
  N=$(pgrep -c -f "_r1_exp.py --out _exp/mid192_ns4" 2>/dev/null || echo 0)
  M=$(pgrep -c -f "_r1_exp.py --out _exp/lath192_ns4" 2>/dev/null || echo 0)
  if [ "$N" = "0" ] && [ "$M" = "0" ]; then
    echo "两个都结束了（第 $i 次检查）"
    break
  fi
  sleep 60
done

echo
echo "################ R24 判定 ################"
$PY -u _r1_analyze.py _exp/mid192_ns4 _exp/lath192_ns4 --skip 8 2>&1 | tail -60
echo
echo "################ 对照：Δx=250 nm 的 m=4 与 m=2 ################"
$PY -u _r1_analyze.py _exp/mid250_ns4 _exp/mid250_ns2 --skip 8 2>&1 | grep -E '###|ΔL : ΔW|碎片守卫'
echo
echo "################ 日志尾部 ################"
tail -6 _exp/mid192_ns4/run.log
tail -6 _exp/lath192_ns4/run.log
