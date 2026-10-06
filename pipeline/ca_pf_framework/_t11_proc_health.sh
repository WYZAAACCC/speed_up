#!/bin/bash
# _t11_proc_health.sh —— 引擎进程健康检查：CPU 时间是否在涨 + cwd 是否 (deleted)。
# 判据：连续两次采样 utime+stime 若**不涨** ⇒ 疑似卡死；cwd 带 (deleted) ⇒ 僵尸。
PIDS=$(pgrep -x python)
[ -z "$PIDS" ] && { echo "**无 python 进程**"; exit 0; }
for p in $PIDS; do
  [ -r "/proc/$p/cmdline" ] || continue
  C=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  case "$C" in *_bk_exp.py*) ;; *) continue ;; esac
  TAG=$(echo "$C" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  read -r U1 S1 < <(awk '{print $14, $15}' "/proc/$p/stat" 2>/dev/null)
  A1=$(awk '/VmRSS/{print $2}' "/proc/$p/status" 2>/dev/null)
  sleep 10
  read -r U2 S2 < <(awk '{print $14, $15}' "/proc/$p/stat" 2>/dev/null)
  A2=$(awk '/VmRSS/{print $2}' "/proc/$p/status" 2>/dev/null)
  DT=$(( (U2 + S2) - (U1 + S1) ))
  echo "PID $p  tag=${TAG:-?}"
  echo "  CPU 时间增量 = $DT jiffies/10s  (>0 = 在算；=0 = **疑似卡死**)"
  echo "  RSS: $((A1/1024)) MB -> $((A2/1024)) MB"
  echo "  cwd = $(readlink /proc/$p/cwd 2>/dev/null)"
done
echo "--- swap ---"; free -m | sed -n 3p
