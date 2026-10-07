#!/bin/bash
# _r579_vnkchk.sh --- 核对 `k_loop=act` 到底省了多少：看两臂的 `adv.step.vnk` 与 `fe.advance.k_loop`
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for t in BASEr1 KLOOPr1 ALL5r1; do
  F="_w2_r579q_${t}_24x64_w4.log"
  echo "===== $t ====="
  [ -f "$F" ] || { echo "  (缺 $F)"; continue; }
  grep -E '干净单步|adv\.step\.vnk|adv\.step\.advphi|fe\.advance\.k_loop|顶层合计|未归属' "$F" | head -8
done
