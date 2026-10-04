#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW $(date '+%m-%d %H:%M:%S')"
L=_w2_t5_short_t10FIX.log
echo "  日志 mtime：$(stat -c '%y' $L 2>/dev/null | cut -c1-19)   大小：$(stat -c '%s' $L 2>/dev/null) B"
echo "  距上次写入：$(( $(date +%s) - $(stat -c '%Y' $L 2>/dev/null) )) s"
echo "--- 日志最后 6 行（去掉 CR）---"
tail -6 "$L" 2>/dev/null | tr -d '\r' | cut -c1-150
echo "--- 是否有 [ N] 步进行 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' "$L" 2>/dev/null | tail -2 | cut -c1-130
echo "--- CPU 时间是否在涨（隔 20 s 两次采样）---"
A=$(awk '{print $14+$15}' /proc/1388/stat 2>/dev/null)
S1=$(awk '/^VmRSS/{print $2}' /proc/1388/status 2>/dev/null)
sleep 20
B=$(awk '{print $14+$15}' /proc/1388/stat 2>/dev/null)
S2=$(awk '/^VmRSS/{print $2}' /proc/1388/status 2>/dev/null)
echo "  utime+stime: $A → $B  （差 $((B-A)) ticks ≈ $(( (B-A)/100 )) s CPU）"
echo "  RSS: $((S1/1024)) → $((S2/1024)) MB"
echo "--- 线程数 / 状态 ---"
awk '/^Threads|^State/{printf "  %s\n", $0}' /proc/1388/status 2>/dev/null
echo "--- 形核分诊 / 补投轮 最近行 ---"
grep -a 's292 补投轮\|s295 形核分诊' "$L" 2>/dev/null | tail -3 | tr -d '\r' | cut -c1-140
