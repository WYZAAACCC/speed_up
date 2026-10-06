#!/bin/bash
# _t11_goal_watch.sh —— goal 每轮的**统一监控快照**（进程 + 内存 + 各日志 + CPU 增量）。
# 判活判据（`R625 §13.3`）：**CPU 时间增量 > 0 才算在算**；只看日志 mtime 不得判卡死。
OUT=/mnt/f/speed_up/_w2_goal_watch.txt
{
echo "############ $(date '+%F %T')"
echo
echo "=== ① 内存 / swap（红线：MemAvailable ≥ 2 GB；swap 不持续增长）==="
free -m
echo
echo "=== ② python 进程 + CPU 增量（两次采样，间隔 10 s）==="
declare -A T1 A1
for p in $(pgrep -x python); do
  T1[$p]=$(awk '{print $14+$15}' /proc/$p/stat 2>/dev/null)
  A1[$p]=$(awk '/VmRSS/{print $2}' /proc/$p/status 2>/dev/null)
done
sleep 10
for p in $(pgrep -x python); do
  [ -r "/proc/$p/cmdline" ] || continue
  C=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null)
  T2=$(awk '{print $14+$15}' /proc/$p/stat 2>/dev/null)
  A2=$(awk '/VmRSS/{print $2}' /proc/$p/status 2>/dev/null)
  D=$(( ${T2:-0} - ${T1[$p]:-0} ))
  TAG=$(echo "$C" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  echo "  PID $p  $(echo "$C" | grep -oE '_t11_[a-z0-9_]+\.py|_bk_exp\.py' | head -1)  tag=${TAG:-—}"
  echo "     CPU增量=${D} jiffies/10s  (>0=在算, =0=**疑似卡死**)   RSS ${A1[$p]:-?} → ${A2:-?} kB"
  echo "     cwd=$(readlink /proc/$p/cwd 2>/dev/null)"
done
echo
echo "=== ③ 日志行数 + mtime ==="
for f in /mnt/f/speed_up/_w2_cube2.log /mnt/f/speed_up/_w2_c2Eq0.log \
         /mnt/f/speed_up/_w2_c2B647.log /mnt/f/speed_up/_w2_c2B15.log; do
  if [ -f "$f" ]; then
    echo "  $(basename $f): $(wc -l < $f) 行  $(stat -c %y "$f" | cut -d. -f1)"
  else
    echo "  $(basename $f): (未创建)"
  fi
done
echo
echo "=== ④ 主控日志尾部（含已完成臂的结果表）==="
tail -32 /mnt/f/speed_up/_w2_cube2.log 2>/dev/null
} > "$OUT" 2>&1
echo "已写出 $OUT"
