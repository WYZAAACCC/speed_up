#!/bin/bash
# 诊断三个基准进程为何 CPU 只有 3%：是阻塞在等待，还是在算但日志没 flush。
# 关键判据：相隔 20 秒采两次 /proc/PID/stat 的 utime+stime，看是否增长。
echo "=== 第一次采样 ==="
for P in $(pgrep -f phase_field-opt); do
  S=$(awk '{print $14+$15}' /proc/$P/stat 2>/dev/null)
  ST=$(awk '{print $3}' /proc/$P/stat 2>/dev/null)
  WD=$(cat /proc/$P/wchan 2>/dev/null)
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | cut -c1-60)
  echo "  PID=$P state=$ST cpu_jiffies=$S wchan=$WD"
  echo "      cmd=$CMD"
  echo "      线程数=$(ls /proc/$P/task 2>/dev/null | wc -l)"
  NT=$(ls /proc/$P/task 2>/dev/null | wc -l)
  if [ "$NT" -gt 1 ]; then
    for T in $(ls /proc/$P/task 2>/dev/null | head -6); do
      TS=$(awk '{print $3}' /proc/$T/stat 2>/dev/null)
      TW=$(cat /proc/$T/wchan 2>/dev/null)
      echo "        tid=$T state=$TS wchan=$TW"
    done
  fi
done

echo
echo "=== 等 20 秒后再采样 ==="
sleep 20
for P in $(pgrep -f phase_field-opt); do
  S=$(awk '{print $14+$15}' /proc/$P/stat 2>/dev/null)
  echo "  PID=$P cpu_jiffies=$S"
done
echo
echo "（jiffies 通常 100/秒；20 秒内增长 ~2000 表示满核在算，增长 ~60 表示 3% 闲着）"
echo
echo "=== 对照：M2 当年从启动到第一个时间步花了多久 ==="
ls -la --time-style=full-iso /root/work/s1d_mumps/M2/run.log /root/work/s1d_mumps/M2/M2.e 2>/dev/null
echo "=== M2 日志开头 20 行 ==="
sed 's/\x1b\[[0-9;]*m//g' /root/work/s1d_mumps/M2/run.log | head -20
