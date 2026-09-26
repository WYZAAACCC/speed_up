#!/bin/bash
# 精确按进程名杀 MOOSE（不能用 pkill -f：会匹配到自己的命令行 => 自杀）
for P in $(pgrep -x gibbs-opt); do kill -9 "$P"; done
sleep 1
echo "剩余 gibbs-opt 进程数: $(pgrep -x gibbs-opt | wc -l)"
