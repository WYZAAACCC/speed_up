#!/bin/bash
cd /root/work/probeB 2>/dev/null || { echo "无目录"; exit 0; }
ls
for f in df0 df1e3 df1e4; do
  echo "--- $f ---"
  if [ -d "$f" ]; then
    [ -f "$f/run.log" ] && echo "  DIV=$(grep -c DIVERGED $f/run.log)  CONV=$(grep -c 'Solve Converged' $f/run.log)"
    [ -f "$f/gb_out.csv" ] && { echo "  rows=$(wc -l < $f/gb_out.csv)"; head -1 $f/gb_out.csv; tail -2 $f/gb_out.csv; }
  else
    echo "  (未开始)"
  fi
done
echo "--- 正在跑的 ---"
pgrep -ax gibbs-opt | head -2