#!/bin/bash
# _t11_oom_dmesg.sh —— 抽取**内核原始 OOM 记录**（dmesg 可读，无需 root）。
OUT=/mnt/f/speed_up/_w2_oom_dmesg.txt
{
echo "############ 采集: $(date '+%F %T')"
echo
echo "=== [1] dmesg | grep oom/killed（含上下文）==="
dmesg 2>/dev/null | grep -aiE "oom|killed process|out of memory|invoked oom" | tail -40
echo
echo "=== [2] kern.log 里的 OOM 段 ==="
grep -aiE "oom|killed process|out of memory" /var/log/kern.log 2>/dev/null | tail -40
echo
echo "=== [3] syslog 里的 OOM 段 ==="
grep -aiE "oom|killed process|out of memory" /var/log/syslog 2>/dev/null | tail -30
echo
echo "=== [4] 21:30-21:35 时段的 syslog（死亡窗口）==="
grep -aE "Oct  6 21:3[0-5]" /var/log/syslog 2>/dev/null | tail -40
echo
echo "=== [5] dmesg 时间轴（末 25 行，任何内容）==="
dmesg -T 2>/dev/null | tail -25 || dmesg 2>/dev/null | tail -25
} > "$OUT" 2>&1
echo "已写出 $OUT（$(wc -l < "$OUT") 行）"
