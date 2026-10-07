#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for _ in $(seq 1 "${1:-9}"); do
  sleep 55
  grep -q 'SMOKE-CLI DONE' _w2_r580_smoke_cli.log 2>/dev/null && break
done
echo "############ F：CLI 开关全开档（原始读数）"
cat _w2_r580_smoke_cli.log 2>/dev/null | tail -45
echo
echo "############ 逐臂日志"
for F in _w2_r580_base.log _w2_r580_allon.log _w2_r580_neg.log; do
  [ -f "$F" ] || { echo "  (缺 $F)"; continue; }
  printf '  %-22s Traceback=%s 退出末行=%s\n' "$F" "$(grep -c '^Traceback' "$F" || true)" "$(tail -1 "$F" | cut -c1-80)"
done
echo
echo "############ baner 对照"
grep -m1 '算子开关' _w2_r580_base.log  || true
grep -m1 '算子开关' _w2_r580_allon.log || true
