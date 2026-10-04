#!/bin/bash
# _t5_trend291.sh --- 判据 1 的直接量：**实有根数是否跨档上升**（被拒不再作废）
# 用法：bash _t5_trend291.sh <秒数>
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
DUR=${1:-560}
LOG=_w2_t5_trend291.log
: > "$LOG"
t0=$(date +%s)
{
  echo "══ s291 判据 1 趋势：实有根数 vs 目标，每 60 s 采一次（共 ${DUR}s）══"
  printf '%-8s %-11s %-8s %-8s %-8s %s\n' "t(s)" "臂" "成功" "被拒" "目标" "末次事件(step/T/累计)"
} >> "$LOG"
while :; do
  now=$(date +%s); el=$((now - t0))
  [ "$el" -ge "$DUR" ] && break
  for T in t5FIX t5BKMo; do
    L=_w2_t5_short_$T.log
    [ -f "$L" ] || continue
    OKS=$(grep -ac '块内第' "$L")
    REJ=$(grep -ac '被引擎拒' "$L")
    TGT=$(grep -a '被引擎拒' "$L" | tail -1 | grep -oE '目标 [0-9]+ 根')
    [ -z "$TGT" ] && TGT=$(grep -a '块内第' "$L" | tail -1 | grep -oE '共 [0-9]+ 块')
    LAST=$(grep -a '块内第' "$L" | tail -1 | grep -oE 'step [0-9]+：T=[0-9.]+ K.*累计 [0-9]+/[0-9]+' | cut -c1-70)
    printf '%-8s %-11s %-8s %-8s %-8s %s\n' "$el" "$T" "$OKS" "$REJ" "$TGT" "$LAST" >> "$LOG"
  done
  # 步号（从日志的 [ N] 行读）
  ST=$(grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t5FIX.log 2>/dev/null | tail -1 | grep -oE '^ *\[ *[0-9]+\]' | tr -dc '0-9')
  echo "          └ t5FIX 末个日志步 = ${ST:-?}" >> "$LOG"
  sleep 60
done
echo "done $(date '+%H:%M:%S')" >> "$LOG"
