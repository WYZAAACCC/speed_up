#!/bin/bash
# _t5_wait291.sh --- s291 后的守望：等 t5FIX 到 step >= NEED，然后出**步对齐**对比。
#   用法：bash _t5_wait291.sh [NEED=560] [MAXWAIT_S=14400]
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5FIX
NEED=${1:-560}
MAXW=${2:-14400}
LOG=_w2_t5_wait291.log
: > "$LOG"
echo "══ s291 守望：等 $TAG 最大快照 >= $NEED（上限 ${MAXW}s）  $(date '+%m-%d %H:%M:%S') ══" >> "$LOG"

t0=$(date +%s)
while :; do
  MX=$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)
  [ -z "$MX" ] && MX=0
  now=$(date +%s); el=$((now - t0))
  # 每 5 分钟记一次心跳
  if [ $((el % 300)) -lt 62 ]; then
    echo "  [$el s] $TAG max=$MX" >> "$LOG"
  fi
  if [ "$MX" -ge "$NEED" ] 2>/dev/null; then
    echo "★ 到达：$TAG max=$MX（用时 ${el}s）" >> "$LOG"; break
  fi
  if [ "$el" -ge "$MAXW" ]; then
    echo "⚠ 超时：$TAG max=$MX（未到 $NEED）" >> "$LOG"; break
  fi
  # 进程没了也要退出
  P=$(ls /proc | grep -E '^[0-9]+$' | while read -r X; do
        tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null | grep -q -- "--tag $TAG " && echo "$X"; done | head -1)
  if [ -z "$P" ]; then echo "⚠ $TAG 进程已不在（max=$MX）" >> "$LOG"; break; fi
  sleep 58
done

echo "" >> "$LOG"
echo "════ ① burst 记账验收（s291 判据 1、2）════" >> "$LOG"
for T in t5FIX t5BKMo t5ETAo; do
  L=_w2_t5_short_$T.log
  [ -f "$L" ] || continue
  echo "--- $T：成功=$(grep -ac '块内第' $L) 被拒=$(grep -ac '被引擎拒' $L)" >> "$LOG"
  grep -a '块内第' $L | tail -3 | grep -oE 'step [0-9]+：T=[0-9.]+ K.*累计 [0-9]+/[0-9]+' | cut -c1-110 | sed 's/^/     /' >> "$LOG"
  grep -a '被引擎拒' $L | tail -2 | grep -oE '@ step [0-9]+.*' | cut -c1-110 | sed 's/^/     拒 /' >> "$LOG"
done

echo "" >> "$LOG"
echo "════ ② 逐档核数（burst 是否真爆发）════" >> "$LOG"
for T in t5FIX t5BKMo; do
  echo "--- $T ---" >> "$LOG"
  grep -a '块内第' _w2_t5_short_$T.log 2>/dev/null \
    | grep -oE 'step [0-9]+：T=[0-9.]+ K' | sort | uniq -c | sed 's/^/     /' >> "$LOG"
done

echo "" >> "$LOG"
echo "════ ③ 步对齐七项（t5FIX vs t5N276F 对照）════" >> "$LOG"
$PY _t5_aralign.py 200,320,400,480,560,640 >> "$LOG" 2>&1

echo "" >> "$LOG"
echo "════ ④ 七项监控（t5FIX）════" >> "$LOG"
$PY _t5_seven.py t5FIX >> "$LOG" 2>&1

echo "" >> "$LOG"
echo "════ ⑤ 碎片/单块场（步对齐）════" >> "$LOG"
$PY _t5_fragalign.py 200,320,400,480,560,640 >> "$LOG" 2>&1

echo "done $(date '+%m-%d %H:%M:%S')" >> "$LOG"
