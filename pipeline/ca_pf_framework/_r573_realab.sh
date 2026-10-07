#!/bin/bash
# _r573_realab.sh --- **真实路径**（`_bk_exp.py`）的 OFF/BIT/ON 三步/秒 A/B。
# 判据：三臂都必须 exit 0；s/步 取末 4 次打印的中位数（前几次含首次分配/编译）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
bash _r569_smoke.sh > _w2_r573_smoke.log 2>&1
echo "smoke exit=$?"

for T in off bit on; do
  L="_w2_r569_${T}.log"
  echo ""
  echo "--- r569_${T} ---"
  grep -m1 '算子开关' "$L" || true
  echo -n "  末 6 次 s/步： "
  grep -oE '[0-9]+\.[0-9]+s/步' "$L" | tail -6 | tr '\n' ' '
  echo ""
  grep -oE '[0-9]+\.[0-9]+s/步' "$L" | tail -4 | sed 's/s\/步//' | sort -n | \
    awk '{a[NR]=$1} END{if(NR>0) printf "  中位数 = %.4f s/步\n", (a[2]+a[3])/2}'
done
echo ""
echo "=== R573 REAL A/B DONE $(date '+%F %T') ==="
