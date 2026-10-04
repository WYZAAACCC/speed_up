#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== relaunch log tail ==="
tail -14 _w2_t5_relaunch291.log
echo
echo "=== NOW: $(date '+%H:%M:%S') ==="
echo "--- live arms ---"
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*)
    echo "pid=$P etime=$(ps -o etime= -p $P | tr -d ' ') $(echo "$C" | grep -oE '\-\-tag [A-Za-z0-9_]+|\-\-ed-eta [0-9.]+|\-\-burst-km [0-9]+' | tr '\n' ' ')"
  ;; esac
done
echo
echo "=== burst 记账验收（s291 判据 1 与 2）==="
for T in t5FIX t5BKMo t5ETAo; do
  L=_w2_t5_short_$T.log
  [ -f "$L" ] || { echo "$T: 无日志"; continue; }
  OK=$(grep -ac 'athermal 形核\*\*\|★★ \*\*athermal\|athermal 形核' $L)
  OKS=$(grep -ac '块内第' $L)
  REJ=$(grep -ac '被引擎拒' $L)
  LAST=$(grep -a '块内第' $L | tail -1 | grep -oE '累计 [0-9]+/[0-9]+.*' | cut -c1-60)
  REJT=$(grep -a '被引擎拒' $L | tail -1 | grep -oE '目标 [0-9]+ 根.*' | cut -c1-60)
  echo "$T: 成功=$OKS 被拒=$REJ"
  echo "     末成功: $LAST"
  echo "     末被拒: $REJT"
done
echo
echo "=== 快照 ==="
for T in t5FIX t5BKMo t5ETAo; do
  D=_exp/_bk_t5/dry_$T
  echo "$T: n=$(ls $D/snap_*.npz 2>/dev/null | wc -l) max=$(ls $D/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)"
done
echo
echo "=== 内存 ==="
free -m | sed -n 2p
