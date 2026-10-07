#!/bin/bash
# _r580_wait.sh --- 等 _r580_verify.sh 出总判定，然后打印 D/E/F 段
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
N="${1:-10}"
for _ in $(seq 1 "$N"); do
  sleep 55
  grep -q '总判定' _w2_r580_verify.log 2>/dev/null && break
done
sed -n '/── D\./,$p' _w2_r580_verify.log
echo
echo "############ 附：CLI 冒烟的原始读数 ############"
grep -E 'exit=|traceback|算子开关|✅|❌|⚠' _w2_r580_smoke_cli.log 2>/dev/null | head -24
