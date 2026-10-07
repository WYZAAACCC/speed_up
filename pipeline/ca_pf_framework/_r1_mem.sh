#!/bin/bash
# _r1_mem.sh --- 内存/swap 压力与各算例进程状态（判断是否在 thrashing）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== free -m ==="
free -m
echo
echo "=== swap 活动（si/so 非 0 = 正在换页）==="
vmstat 2 3 2>/dev/null | tail -3
echo
echo "=== 各 _r1_exp 进程 ==="
printf '%-8s %-5s %10s %8s  %s\n' PID STAT RSS_MB ELAPSED OUT
for P in $(pgrep -f '_r1_exp\.py --out' 2>/dev/null); do
  ST=$(ps -o stat= -p "$P" | tr -d ' ')
  RS=$(ps -o rss= -p "$P" | tr -d ' ')
  ET=$(ps -o etimes= -p "$P" | tr -d ' ')
  AR=$(tr '\0' ' ' < "/proc/$P/cmdline" 2>/dev/null)
  OUT=$(echo "$AR" | sed -n 's/.*--out \([^ ]*\).*/\1/p')
  printf '%-8s %-5s %10.0f %8s  %s\n' "$P" "$ST" "$((RS/1024))" "$ET" "$OUT"
done
echo
echo "=== 状态码含义：R=运行 S=可中断睡眠 D=不可中断(多为 I/O/换页) ==="
