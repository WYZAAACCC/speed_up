#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
for i in $(seq 1 60); do
  n=$(ls _v1_out 2>/dev/null | wc -l)
  w=$(ps -eo args | grep -c '[_]v1_worker')
  if [ "$w" -eq 0 ]; then break; fi
  sleep 20
done
echo "完成 worker 输出数: $(ls _v1_out | wc -l) / 56"
tail -6 _v1_run.log