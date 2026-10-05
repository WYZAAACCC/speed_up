#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10CL2
echo "NOW $(date '+%m-%d %H:%M:%S')"
echo "--- 目录 ---"
ls -la _exp/_bk_t5/dry_$TAG/ | tail -8
echo "--- 快照 ---"
ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | xargs -n1 basename | tr '\n' ' '; echo
MX=$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)
echo "--- 快照最大 = ${MX:-0} ---"
if [ -n "$MX" ] && [ "${MX:-0}" -ge 100 ] 2>/dev/null; then
  echo; echo "════ J1/J2 ════"; $PY _t10_seven.py $TAG "$MX" 2>&1 | tail -22
  echo; echo "════ J1 全部场 ════"; $PY _t10_allfields.py $TAG "$MX" 2>&1 | tail -8
  echo; echo "════ J3 块表 ════"; $PY _t10_seven.py $TAG "$MX" 2>&1 | tail -7
else
  echo "  还没落盘 ⇒ 引擎仍在写，下一轮再判"
fi
echo "--- swap ---"
free -m | sed -n 3p
