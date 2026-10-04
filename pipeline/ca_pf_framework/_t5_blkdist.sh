#!/bin/bash
# 核实：块内板条数分布是否严重不均（B=3 的名义目标 vs 实际）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_short_t5N276F.log
echo "=== t5N276F 的 blk_laths 轨迹（块内板条数分布）==="
grep -a 'blk_laths=' $L | tail -3 | cut -c1-260
echo
echo "=== 首末对比 ==="
grep -a 'blk_laths=' $L | head -1 | grep -oE 'blk_laths=[0-9/]+' | sed 's/^/  首: /'
grep -a 'blk_laths=' $L | tail -1 | grep -oE 'blk_laths=[0-9/]+' | sed 's/^/  末: /'
echo
echo "=== nblk_sig / n_var_sig 轨迹 ==="
grep -a 'nblk_sig=' $L | tail -3 | grep -oE 'nblk_sig=[0-9]+ n_var_sig=[0-9]+' | sed 's/^/  /'
echo
echo "=== 模式统计（attach 是否占多数）==="
grep -a '模式 \*\*' $L | grep -oE '模式 \*\*[a-z]+\*\*' | sort | uniq -c | sed 's/^/  /'
echo
echo "=== 三臂当前状态 ==="
for T in t5FIX t5BKMo t5ETAo; do
  D=_exp/_bk_t5/dry_$T
  MX=$(ls $D/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)
  echo "  $T max=${MX:-0} 补投轮=$(grep -ac '◆ s292' _w2_t5_short_$T.log 2>/dev/null) 被拒=$(grep -ac '被引擎拒' _w2_t5_short_$T.log 2>/dev/null)"
done
