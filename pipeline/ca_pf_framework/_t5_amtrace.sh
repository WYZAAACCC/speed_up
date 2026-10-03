#!/bin/bash
# _t5_amtrace.sh --- ★★★★★ 抓 `mob-iform ellipse` 崩溃的**确切 traceback**
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for t in t5AM_ell t5AM_combo; do
  echo "════════ $t ════════"
  L=_w2_t5_short_$t.log
  [ -f "$L" ] || { echo "  （无 $L）"; continue; }
  echo "  ── 日志大小 $(stat -c%s "$L") 字节 ──"
  echo '  ── 含 Error/Traceback/错误 的行 ──'
  grep -nE "Traceback|Error|error|Exception|raise|❌|✗" "$L" 2>/dev/null | head -8 | cut -c1-165 | sed 's/^/     /'
  echo '  ── 末尾 22 行（**不截断**，看调用栈）──'
  tail -22 "$L" | cut -c1-165 | sed 's/^/     /'
  echo
done
