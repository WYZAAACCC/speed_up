#!/bin/bash
# _t5_gate292.sh --- s292 验收：① 节拍 ② 补投轮次数 ③ 实有根数 ④ 对照臂不变
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== NOW $(date '+%H:%M:%S') ==="
echo
echo "=== ① 进程 ==="
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*) echo "  pid=$P etime=$(ps -o etime= -p $P | tr -d ' ') $(echo "$C" | grep -oE '\-\-tag [A-Za-z0-9_]+' )" ;; esac
done
echo
echo "=== ② s292 补投轮（★ 每档应至多一次）==="
for T in t5FIX t5BKMo; do
  echo "  --- $T: $(grep -ac '◆ s292 补投轮' _w2_t5_short_$T.log 2>/dev/null) 次"
  grep -a '◆ s292 补投轮' _w2_t5_short_$T.log 2>/dev/null | tail -4 | sed 's/^/     /'
done
echo
echo "=== ③ burst 记账 ==="
for T in t5FIX t5BKMo t5ETAo; do
  L=_w2_t5_short_$T.log
  [ -f "$L" ] || continue
  echo "  $T: 成功=$(grep -ac '块内第' $L) 被拒=$(grep -ac '被引擎拒' $L)"
  grep -a '块内第' $L | tail -1 | grep -oE 'step [0-9]+：T=[0-9.]+ K.*累计 [0-9]+/[0-9]+' | cut -c1-80 | sed 's/^/     末成功 /'
done
echo
echo "=== ④ 节拍（[ N] 行的 s/步）==="
for T in t5FIX t5BKMo t5ETAo; do
  echo "  --- $T ---"
  grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$T.log 2>/dev/null | grep -oE '^ *\[ *[0-9]+\]|步$|[0-9.]+s/步' | paste - - 2>/dev/null | tail -4 | sed 's/^/     /'
done
echo
echo "=== ⑤ 快照 ==="
for T in t5FIX t5BKMo t5ETAo; do
  D=_exp/_bk_t5/dry_$T
  N=$(ls $D/snap_*.npz 2>/dev/null | wc -l)
  MX=$(ls $D/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)
  echo "  $T: n=$N max=${MX:-0}"
done
echo
echo "=== ⑥ 内存 ==="
free -m | sed -n 2p | sed 's/^/  /'
echo
echo "=== ⑦ 守望器 ==="
tail -3 _w2_t5_wait291.log
