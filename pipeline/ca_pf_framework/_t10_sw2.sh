#!/bin/bash
# _t10_sw2.sh --- 稳健版 swap 报警：**先等引擎出现**再开始盯，引擎消失后不退出（继续盯全机 swap）
TAG=${1:-t10FIX}
DUR=${2:-28800}
LOG=_w2_t10_swapfix2.log
: > "$LOG"
echo "══ swap 报警（稳健版）启动 $(date '+%m-%d %H:%M:%S')  tag=$TAG  上限 ${DUR}s ══" >> "$LOG"
echo "  判据：进程 VmSwap > 0 或 全机 Swap used > 0 ⇒ 告警；心跳每 600 s" >> "$LOG"

seen=0; peak=0; t0=$(date +%s); last=0
while :; do
  now=$(date +%s); el=$((now - t0))
  [ "$el" -ge "$DUR" ] && { echo "  到时限，退出（$el s）" >> "$LOG"; break; }
  P=""
  for X in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
    C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
    case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
  done
  SW_ALL=$(free -m | awk '/^Swap:/{print $3}')
  if [ -n "$P" ]; then
    seen=1
    PSW=$(awk '/^VmSwap/{print $2}' /proc/$P/status 2>/dev/null)
    PHW=$(awk '/^VmHWM/{print $2}' /proc/$P/status 2>/dev/null)
    PSW=${PSW:-0}; PHW=${PHW:-0}
    [ "$PHW" -gt "$peak" ] 2>/dev/null && peak=$PHW
    if [ "${PSW:-0}" -gt 0 ] 2>/dev/null || [ "${SW_ALL:-0}" -gt 0 ] 2>/dev/null; then
      echo "⚠️⚠️⚠️ **SWAP 被触发** @$(date '+%H:%M:%S')（历龄 ${el}s）" >> "$LOG"
      echo "    进程 VmSwap = $((PSW/1024)) MB ；全机 swap used = ${SW_ALL} MB" >> "$LOG"
      echo "    进程 VmHWM  = $((PHW/1024)) MB（历史峰值 $((peak/1024)) MB）" >> "$LOG"
      echo "    free: $(free -m | sed -n 3p)" >> "$LOG"
    fi
    if [ $((el - last)) -ge 600 ]; then
      last=$el
      echo "  [${el}s] 活着 RSS=$(awk '/^VmRSS/{print $2}' /proc/$P/status 2>/dev/null | awk '{printf "%d", $1/1024}')MB VmHWM=$((PHW/1024))MB VmSwap=$((PSW/1024))MB 全机swap=${SW_ALL}MB" >> "$LOG"
    fi
  else
    if [ $((el - last)) -ge 600 ]; then
      last=$el
      echo "  [${el}s] 引擎不在（seen=$seen）全机swap=${SW_ALL}MB" >> "$LOG"
    fi
  fi
  sleep 20
done
echo "── 结束，全程进程 VmHWM 峰值 = $((peak/1024)) MB ──" >> "$LOG"
