#!/bin/bash
# _t11_oom_evidence.sh —— 收集 OOM 的**直接证据**（不需 root 的路径全试一遍）。
OUT=/mnt/f/speed_up/_w2_oom_evidence.txt
{
echo "############ 采集时间: $(date '+%F %T')"
echo
echo "=== [1] dmesg 是否可读 ==="
dmesg >/dev/null 2>&1 && echo "  可读" || echo "  **不可读**（需 root 或 kernel.dmesg_restrict）"
echo "  kernel.dmesg_restrict = $(cat /proc/sys/kernel/dmesg_restrict 2>/dev/null)"
echo
echo "=== [2] 内核日志文件 ==="
for f in /var/log/kern.log /var/log/syslog /var/log/messages; do
  if [ -f "$f" ]; then echo "  $f 存在（$(wc -l < "$f") 行）"; else echo "  $f 不存在"; fi
done
echo
echo "=== [3] OOM 相关 sysctl ==="
for k in vm.panic_on_oom vm.overcommit_memory vm.overcommit_ratio vm.min_free_kbytes; do
  printf "  %-26s = %s\n" "$k" "$(cat /proc/sys/$(echo $k | tr . /) 2>/dev/null)"
done
echo
echo "=== [4] cgroup v2 内存限制 ==="
for f in /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.high \
         /sys/fs/cgroup/memory.events /sys/fs/cgroup/memory.peak \
         /sys/fs/cgroup/memory.current; do
  if [ -r "$f" ]; then printf "  %-34s = %s\n" "$f" "$(cat "$f")"; fi
done
echo
echo "=== [5] 进程统计里的 OOM 计数 ==="
grep -aE "oom_kill|oom_" /proc/vmstat 2>/dev/null || echo "  /proc/vmstat 无 oom 字段"
echo
echo "=== [6] 是否曾发生 coredump ==="
echo "  core_pattern = $(cat /proc/sys/kernel/core_pattern 2>/dev/null)"
ls -la /var/lib/systemd/coredump/ 2>&1 | head -4
echo
echo "=== [7] 当前内存/swap ==="
free -m
echo
echo "=== [8] swap 现在被谁占着 ==="
for p in $(ls /proc | grep -E '^[0-9]+$'); do
  s=$(awk '/VmSwap/{print $2}' /proc/$p/status 2>/dev/null)
  [ -n "$s" ] && [ "$s" -gt 1000 ] && echo "  PID $p VmSwap=${s} kB  cmd=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | head -c 80)"
done
echo "  （空 = 无进程在 swap 里，说明死亡进程的 swap 已回收）"
} > "$OUT" 2>&1
echo "已写出 $OUT"
