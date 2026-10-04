#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== NOW $(date '+%H:%M:%S') ==="
for T in t5FIX t5BKMo t5ETAo; do
  D=_exp/_bk_t5/dry_$T
  echo "  $T max=$(ls $D/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1) 成功=$(grep -ac '块内第' _w2_t5_short_$T.log 2>/dev/null) fresh拒=$(grep -ac 'fresh` 被拒' _w2_t5_short_$T.log 2>/dev/null)"
done
echo
echo "=== g._nuc / dbg 的存放位置 ==="
grep -n "self\._nuc\b\|self\._nuc\[" windowB_surface.py | head -12 | cut -c1-150
echo
echo "=== _bk_exp.py 里 nuc_cfg / _nuc 的构造与传递 ==="
grep -n "nuc_cfg\|_nuc=\|sites_refill=" _bk_exp.py | head -12 | cut -c1-170
echo
echo "=== 块统计（blk_laths 等）是在哪里打印的？==="
grep -n "blk_laths\|nblk_sig" _bk_exp.py | head -8 | cut -c1-170
echo
echo "=== 是否已有 dbg 打印 ==="
grep -n "dbg" _bk_exp.py | head -12 | cut -c1-170
