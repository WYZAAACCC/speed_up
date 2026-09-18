#!/bin/bash
# 清掉 MOOSE 进程。写成文件跑 —— 内联命令里嵌套引号/pgrep -f 模式
# 在 Git Bash -> WSL 这条链上反复出问题（今天踩了多次）。
pgrep -f 'phase_field-opt -i' > /tmp/mp.txt 2>/dev/null
N=$(wc -l < /tmp/mp.txt)
echo "待清理 $N 个"
xargs -r kill -9 < /tmp/mp.txt 2>/dev/null
sleep 3
echo "剩余 $(pgrep -cf 'phase_field-opt -i')"
