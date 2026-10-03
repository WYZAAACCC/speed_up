#!/bin/bash
# _t5_dgchk.sh --- 检查带符号 `Δed` 是否打出来了
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "── 搜 '带符号' 的次数 ──"
grep -c '带符号' _w2_t5_short_t5B4D.log 2>/dev/null || echo 0
echo
echo '── 最后一条 F1 块（含后 3 行）──'
L=$(grep -n 'F1 含母相' _w2_t5_short_t5B4D.log 2>/dev/null | tail -1 | cut -d: -f1)
echo "  （F1 行号 = $L）"
if [ -n "$L" ]; then
  sed -n "${L},$((L + 3))p" _w2_t5_short_t5B4D.log | cut -c1-240 | sed 's/^/  /'
fi
echo
echo '── 代码里是否真的有那句 ──'
grep -c '带符号' _bk_exp.py 2>/dev/null || echo 0
grep -n '带符号' _bk_exp.py 2>/dev/null | head -3 | cut -c1-140 | sed 's/^/  /'
