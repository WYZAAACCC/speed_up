#!/bin/bash
# _t10_swapalert.sh --- 长时盯守：**swap 一旦 > 0 立刻记一条醒目告警**
#   用法：bash _t10_swapalert.sh <总秒数> [间隔秒]
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
TAG=t10N160
DUR=${1:-28800}     # 默认 8 h
IV=${2:-20}
LOG=_w2_t10_swapalert.log
: > "$LOG"
echo "══ swap 报警盯守启动 $(date '+%m-%d %H:%M:%S')（每 ${IV}s，共 ${DUR}s）══" >> "$LOG"
echo "  判据：进程 VmSwap > 0  **或** 全机 Swap used > 0 ⇒ 写 ⚠️ 告警（只写首次 + 状态变化）" >> "$LOG"
PEAKHWM=0; ALERTED=0; LASTSW=-1
t0=$(date +%s)
while :; do
  el=$(( $(date +%s) - t0 ))
  [ "$el" -ge "$DUR" ] && break
  P=""
  for X in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
    C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
    case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
  done
  if [ -z "$P" ]; then
    echo "[$el s] ⚠ 引擎不在" >> "$LOG"
    [ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt | sed 's/^/          /' >> "$LOG"
    grep -a '看门狗\|峰值 RSS' _w2_t5_short_$TAG.log 2>/dev/null | tail -3 | sed 's/^/          /' >> "$LOG"
    break
  fi
  SYS=$(free -m | awk '/^Swap:/{print $3}')
  PSW=$(awk '/VmSwap/{print int($2/1024)}' /proc/$P/status 2>/dev/null)
  HWM=$(awk '/VmHWM/{print int($2/1024)}' /proc/$P/status 2>/dev/null)
  RSS=$(awk '/VmRSS/{print int($2/1024)}' /proc/$P/status 2>/dev/null)
  PSW=${PSW:-0}; HWM=${HWM:-0}; SYS=${SYS:-0}
  [ "$HWM" -gt "$PEAKHWM" ] && PEAKHWM=$HWM
  CUR=$(( PSW + SYS ))
  if [ "$CUR" -gt 0 ] && [ "$ALERTED" -eq 0 ]; then
    {
      echo ""
      echo "  ⚠️⚠️⚠️ **SWAP 被触发** @ $(date '+%m-%d %H:%M:%S')（历龄 ${el}s）"
      echo "      进程 VmSwap = ${PSW} MB ；全机 Swap used = ${SYS} MB"
      echo "      此刻 RSS=${RSS} MB  VmHWM=${HWM} MB"
      free -m | sed -n '2,3p' | sed 's/^/      /'
    } >> "$LOG"
    ALERTED=1
    LASTSW=$CUR
  elif [ "$ALERTED" -eq 1 ] && [ "$CUR" -eq 0 ]; then
    echo "  ✅ swap 已完全收回 @ $(date '+%H:%M:%S')（峰值 VmHWM=${PEAKHWM} MB）" >> "$LOG"
    ALERTED=0; LASTSW=-1
  elif [ "$ALERTED" -eq 1 ] && [ "$CUR" -gt $(( LASTSW * 6 / 5 + 50 )) ]; then
    echo "  ⚠️ swap 继续增长 @ $(date '+%H:%M:%S')：进程 ${PSW} MB + 全机 ${SYS} MB（RSS=${RSS} HWM=${HWM}）" >> "$LOG"
    LASTSW=$CUR
  fi
  # 每 10 分钟记一条常态心跳（含 VmHWM 与 swap）
  if [ $(( el % 600 )) -lt "$IV" ]; then
    ST=$(grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -1 | grep -oE '\[ *[0-9]+\]' | tr -dc '0-9')
    echo "[$el s] 步=${ST:-0} RSS=${RSS} VmHWM=${HWM} VmSwap=${PSW} 全机swap=${SYS} MB" >> "$LOG"
  fi
  sleep "$IV"
done
echo "── 盯守结束 $(date '+%H:%M:%S')，全程 VmHWM 峰值 = ${PEAKHWM} MB ──" >> "$LOG"
