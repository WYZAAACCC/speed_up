#!/bin/bash
# _t10_wait.sh --- 等 10 µm 算例写出快照，自动出**七项读数**（三维视觉由 _t10_view.py 另跑）
#   用法：bash _t10_wait.sh <NEED_STEP=100> <MAXWAIT_S=14400>
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10N160
NEED=${1:-100}
MAXW=${2:-14400}
LOG=_w2_t10_wait.log
: > "$LOG"
echo "══ 等 $TAG 的快照 step >= $NEED（上限 ${MAXW}s）  $(date '+%m-%d %H:%M:%S') ══" >> "$LOG"

t0=$(date +%s)
while :; do
  MX=$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)
  [ -z "$MX" ] && MX=0
  el=$(( $(date +%s) - t0 ))
  if [ "$MX" -ge "$NEED" ] 2>/dev/null; then
    echo "★ 到达 step=$MX（用时 ${el}s）" >> "$LOG"; break
  fi
  if [ "$el" -ge "$MAXW" ]; then echo "⚠ 超时（max=$MX）" >> "$LOG"; break; fi
  P=""
  for X in $(ls /proc | grep -E '^[0-9]+$'); do
    C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
    case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
  done
  if [ -z "$P" ]; then echo "⚠ $TAG 进程已不在（max=$MX）" >> "$LOG"; break; fi
  if [ $((el % 600)) -lt 65 ]; then
    RSS=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null)
    ST=$(grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -1 | grep -oE '\[ *[0-9]+\]' | tr -dc '0-9')
    echo "  [${el}s] 快照=$MX 日志步=${ST:-?} RSS=$(( ${RSS:-0} / 1024 )) MB" >> "$LOG"
  fi
  sleep 60
done

MX=$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)
if [ -n "$MX" ] && [ "${MX:-0}" -gt 0 ] 2>/dev/null; then
  {
    echo ""; echo "════ 七项监控（快照步序：$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tr '\n' ' ') ════"
    $PY _t10_seven.py $TAG "$MX"
    echo ""; echo "════ 日志尾（形核/事件/节拍）════"
    grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -4 | cut -c1-205
    grep -a '◆ s292\|athermal\|◆ s295' _w2_t5_short_$TAG.log 2>/dev/null | tail -8 | cut -c1-205
  } >> "$LOG" 2>&1
fi
echo "done $(date '+%H:%M:%S')" >> "$LOG"
