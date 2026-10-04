#!/bin/bash
# 快速核对：形核事件的 field 是否重复（H1 vs H2 的判据）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
L=_w2_t5_short_t5N276F.log
echo "=== t5N276F 形核事件的 field 列表 ==="
grep -a 'athermal 形核' $L | grep -oE '，场 [0-9]+（' | grep -oE '[0-9]+' | tr '\n' ' '
echo
echo -n "事件数 = "
grep -ac 'athermal 形核' $L
echo -n "互不相同的 field 数 = "
grep -a 'athermal 形核' $L | grep -oE '，场 [0-9]+（' | grep -oE '[0-9]+' | sort -n | uniq | wc -l
echo
echo "=== 模式分布 ==="
grep -a '模式 \*\*' $L | grep -oE '模式 \*\*[a-z]+\*\*' | sort | uniq -c
echo
echo "=== t5N276F 末态 T_hist / meta 里的 n_target ==="
grep -a 'n_target' $L | tail -2 | cut -c1-200
echo
echo "=== wait291 心跳 ==="
tail -6 _w2_t5_wait291.log 2>/dev/null
echo
echo "=== 三个臂的快照 ==="
for T in t5FIX t5BKMo t5ETAo; do
  D=_exp/_bk_t5/dry_$T
  echo "$T: n=$(ls $D/snap_*.npz 2>/dev/null | wc -l) max=$(ls $D/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)"
done
