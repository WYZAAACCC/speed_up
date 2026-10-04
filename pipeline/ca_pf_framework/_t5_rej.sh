#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== [1] t5BKMo / t5FIX / t5ETAo: accepted vs rejected ==="
for T in t5BKMo t5FIX t5ETAo; do
  L=_w2_t5_short_$T.log
  [ -f "$L" ] || continue
  OK=$(grep -ac '★★ \*\*athermal 形核\*\*' $L)
  OK2=$(grep -ac 'athermal 形核' $L)
  REJ=$(grep -ac '被引擎拒' $L)
  TGT=$(grep -ao '累计 [0-9]*/[0-9]*' $L | tail -1)
  echo "$T: 成功=$OK2 被拒=$REJ 末次目标=$TGT"
done
echo
echo "=== [2] t5BKMo: 每档 T 与事件号（成功事件） ==="
grep -a 'athermal 形核' _w2_t5_short_t5BKMo.log | grep -ao 'step [0-9]*：T=[0-9.]* K.*累计 [0-9]*/[0-9]*' | cut -c1-90
echo
echo "=== [3] nucleate() 的返回 None 条件 ==="
grep -n 'def nucleate' windowB_surface.py
echo "--- 关键拒绝分支 ---"
awk 'NR>=1440 && NR<=1560 && (/return \[\]/ || /return None/ || /continue/ || /if /)' windowB_surface.py | cut -c1-150 | head -40
