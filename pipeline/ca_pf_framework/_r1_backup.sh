#!/bin/bash
# WSL 崩过之后：先备份被打断算例的部分数据，再重启它们
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for d in e5_equi6 e7_selfac equi192_ns4; do
  if [ -f "_exp/$d/series.csv" ]; then
    n=$(wc -l < "_exp/$d/series.csv")
    cp "_exp/$d/series.csv" "_exp/$d/series_partial_${n}rows.csv"
    echo "backed up $d : ${n} rows"
  fi
done
ls -la _exp/e5_equi6/*.csv _exp/e7_selfac/*.csv _exp/equi192_ns4/*.csv 2>/dev/null | head -12
