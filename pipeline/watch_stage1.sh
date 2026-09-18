#!/bin/bash
# 观察阶段一算例：进度 + GrainTracker 活跃晶粒数趋势

cd /root/work/s1 || exit 1
LOG=${1:-s1.log}

echo "=== 进度 ==="
if [ -f s1_out.csv ]; then
    n=$(( $(wc -l < s1_out.csv) - 1 ))
    echo "  步数 $n，末行: $(tail -1 s1_out.csv)"
else
    echo "  尚无 CSV"
fi
np=$(pgrep -fc 'phase_field-opt' 2>/dev/null)
echo "  进程数: ${np:-0}"

echo
echo "=== GrainTracker：每次状态块的总晶粒数 ==="
# 日志形如 "Grains active index 0: 5 -> 5"
#   $1=Grains $2=active $3=index $4=0: $5=前 $6=-> $7=后
grep 'Grains active index' "$LOG" | awk '{s += $7; n++} n == 8 {printf "%d\n", s; s = 0; n = 0}' | \
    awk 'NR % 20 == 1 {printf "  状态块 %-4d 总晶粒 %s\n", NR, $1}'

echo
echo "=== 事件 / 错误 ==="
for pat in Remap remap merged disappear ERROR WARNING Cutback DIVERGED; do
    c=$(grep -c "$pat" "$LOG" 2>/dev/null)
    [ "${c:-0}" -gt 0 ] && echo "  $pat: $c"
done

echo
echo "=== 日志尾 ==="
grep -v '^$' "$LOG" | tail -4
