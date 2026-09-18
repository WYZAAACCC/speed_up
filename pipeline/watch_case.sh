#!/bin/bash
# 通用算例观察器
# 用法: bash watch_case.sh <运行目录> [end_time]
#
# 注意：run_case.sh 把输入复制成 in.i，所以 MOOSE 的 CSV 叫 in_out.csv
# （csv 名跟输入文件名走），Exodus 才用 file_base。

RUN="${1:-/root/work/s1v2}"
END="${2:-}"

cd "$RUN" || { echo "目录不存在: $RUN"; exit 1; }

np=$(pgrep -fc 'phase_field-opt' 2>/dev/null)
echo "进程数: ${np:-0}"

csv=in_out.csv
[ -f "$csv" ] || csv=$(ls *_out.csv 2>/dev/null | head -1)

if [ -n "${csv:-}" ] && [ -f "$csv" ]; then
    n=$(( $(wc -l < "$csv") - 1 ))
    echo "输出点: $n  $([ -n "$END" ] && echo "/ 约 $(echo "$END" | awk '{printf "%d", $1/2e-6}') 步")"
    head -1 "$csv"
    tail -3 "$csv"
else
    echo "尚无 CSV"
fi

echo
echo "DIVERGED: $(grep -c DIVERGED run.log 2>/dev/null)"

echo
echo "--- 日志尾 ---"
if [ -f run.log ]; then
    grep -v '^$' run.log | tail -6
fi
