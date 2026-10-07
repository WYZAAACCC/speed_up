#!/bin/bash
# _t11_oom_table.sh —— 抽 OOM dump 里的**全进程内存表**（找真正的内存消耗者）。
OUT=/mnt/f/speed_up/_w2_oom_table.txt
{
echo "############ 采集: $(date '+%F %T')"
echo
echo "=== OOM dump 的完整块（21:35:44 那次，含进程表）==="
dmesg 2>/dev/null | awk '/invoked oom-killer/{f=1} f{print} /oom_reaper|Out of memory: Killed/{if(f)c++} f&&c>=2{exit}' | head -120
echo
echo "=== 若上面为空：从 kern.log 抽同一段 ==="
grep -a -A80 "21:35:44.*invoked oom-killer" /var/log/kern.log 2>/dev/null | head -100
echo
echo "=== tasks 表（RSS 排序，若 dump 里有）==="
dmesg 2>/dev/null | grep -aE "rss_anon|Out of memory: Killed" | tail -30
} > "$OUT" 2>&1
echo "已写出 $OUT（$(wc -l < "$OUT") 行）"
