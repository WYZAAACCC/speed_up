#!/bin/bash
# _t5_p0dbg2.sh --- 查**正确文件**里的插桩输出
cd "$(dirname "$0")" || exit 1
echo '════ 各日志里的 P0DBG 行数 ════'
for f in _w2_t5_short_dA.log _w2_t5_short_dB.log _w2_t5_dbg_A2.log _w2_t5_dbg_B.log; do
  [ -f "$f" ] || { printf '  %-28s （不存在）\n' "$f"; continue; }
  printf '  %-28s P0DBG=%-4s  %s 字节\n' "$f" "$(grep -c 'P0DBG' "$f" 2>/dev/null)" "$(stat -c%s "$f")"
done
echo
echo '════ ★ A 臂（一次跑 20 步）的插桩 ════'
grep -h 'P0DBG' _w2_t5_short_dA.log 2>/dev/null | head -12 | sed 's/^/  /'
echo
echo '════ ★ B 臂的插桩 ════'
grep -h 'P0DBG' _w2_t5_short_dB.log 2>/dev/null | head -12 | sed 's/^/  /'
echo
echo '════ 目录里 dA 的日志（续跑那次可能覆盖/改名）════'
ls -1t _w2_t5_short_dA*.log _w2_t5_dbg_A2.log 2>/dev/null | head -6 | sed 's/^/  /'
grep -h 'P0DBG' _w2_t5_short_dA*.log 2>/dev/null | tail -24 | sed 's/^/  /'
