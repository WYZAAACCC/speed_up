#!/bin/bash
# _t10_auto.sh --- 10 µm 算例的自动守望：步速 + 七项 + swap 摘要
#   用法：bash _t10_auto.sh <MAXWAIT_S=21600>
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10N160
MAXW=${1:-21600}
LOG=_w2_t10_auto.log
: > "$LOG"
echo "══ 自动守望启动 $(date '+%m-%d %H:%M:%S')（上限 ${MAXW}s）══" >> "$LOG"

t0=$(date +%s)
STEP20=0
while :; do
  el=$(( $(date +%s) - t0 ))
  [ "$el" -ge "$MAXW" ] && { echo "⚠ 超时" >> "$LOG"; break; }
  # 进程没了就收尾
  P=""
  for X in $(ls /proc | grep -E '^[0-9]+$'); do
    C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
    case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
  done
  if [ -z "$P" ]; then
    {
      echo "⚠ 引擎不在 @ ${el}s"
      [ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt | sed 's/^/    /'
      grep -a '看门狗\|峰值 RSS' _w2_t5_short_$TAG.log 2>/dev/null | tail -3 | sed 's/^/    /'
    } >> "$LOG"
    break
  fi
  # ① 出现 [ 20] 就记步速（只记一次）
  if [ "$STEP20" -eq 0 ]; then
    L20=$(grep -aE '^ *\[ *20\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -1)
    if [ -n "$L20" ]; then
      STEP20=1
      {
        echo ""; echo "★ **[ 20] 出现 @ ${el}s** ⇒ 步速可读"
        echo "    $L20" | cut -c1-200
        grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log | grep -oE '^ *\[ *[0-9]+\]|[0-9.]+s/步' | paste - - | tail -3 | sed 's/^/    /'
      } >> "$LOG"
    fi
  fi
  # ② swap 摘要（每 5 分钟）
  if [ $((el % 300)) -lt 31 ]; then
    SW=$(awk '/VmSwap/{print int($2/1024)}' /proc/$P/status 2>/dev/null)
    HW=$(awk '/VmHWM/{print int($2/1024)}' /proc/$P/status 2>/dev/null)
    SS=$(free -m | awk '/^Swap:/{print $3}')
    ST=$(grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -1 | grep -oE '\[ *[0-9]+\]' | tr -dc '0-9')
    NE=$(grep -ac 'athermal 形核' _w2_t5_short_$TAG.log 2>/dev/null)
    echo "[${el}s] 步=${ST:-0} 核=${NE} RSS=$(( $(awk '/VmRSS/{print $2}' /proc/$P/status)/1024 )) VmHWM=${HW:-0} VmSwap=${SW:-0} 全机swap=${SS} MB" >> "$LOG"
  fi
  # ③ 快照 ≥100 就出七项（只出一次）
  MX=$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)
  if [ -n "$MX" ] && [ "${MX:-0}" -ge 100 ] 2>/dev/null && [ ! -f _w2_t10_seven.done ]; then
    touch _w2_t10_seven.done
    {
      echo ""; echo "════ 七项监控 @ 快照 step=$MX（快照序列：$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tr '\n' ' ')）════"
    } >> "$LOG"
    $PY _t10_seven.py $TAG "$MX" >> "$LOG" 2>&1
  fi
  sleep 60
done
echo "── 守望结束 $(date '+%H:%M:%S') ──" >> "$LOG"
