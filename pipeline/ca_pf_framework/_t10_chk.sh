#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== NOW $(date '+%H:%M:%S') ==="
echo "--- 引擎 RSS ---"
BEST=0; BESTP=""
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*) ;; *) continue ;; esac
  R=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null); R=${R:-0}
  [ "$R" -gt "$BEST" ] && { BEST=$R; BESTP=$P; }
done
if [ -n "$BESTP" ]; then
  echo "  pid=$BESTP RSS=$((BEST/1024)) MB  历龄=$(ps -o etime= -p $BESTP | tr -d ' ')"
  echo "  argv: $(tr '\0' ' ' < /proc/$BESTP/cmdline | grep -oE '\-\-N [0-9]+|\-\-dx-nm [0-9.]+|\-\-nvar [0-9]+|\-\-m [0-9]+|\-\-B [0-9]+|\-\-ed-eta [0-9.]+|\-\-burst-km [0-9]+|\-\-nuc-block-parallel [0-9]+|\-\-mem-limit-gb [0-9.]+' | tr '\n' ' ')"
else
  echo "  ⚠ 引擎不在"
fi
echo "--- free ---"; free -m | sed -n 2p
echo "--- 日志尾 ---"; tail -6 _w2_t5_short_t10N160.log 2>/dev/null | cut -c1-190
echo "--- 快照 ---"; ls _exp/_bk_t5/dry_t10N160/snap_*.npz 2>/dev/null | wc -l
echo "--- 盯守日志尾 ---"; tail -6 _w2_t10_mon.log 2>/dev/null
