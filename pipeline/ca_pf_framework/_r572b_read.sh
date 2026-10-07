#!/bin/bash
# _r572b_read.sh --- 把 A/B 两份剖面日志的关键行并排打出来（同样的正则，避免手抄）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PAT='干净单步|记账跑单步|region\(\)|argmin2\(\)|elastic_driving_pair|elastic_driving\(\)|el\.sigma_tensor|el\.eps0_fields|el\.fft_|fe\.ed\.soft_phi|fe\.ed\.einsum|finish\(\)|for_each|par\.gradient|par\.upwind_flux_vec|op\._minmod|op\._bbox_pad|覆盖率|= \*\*[0-9]'
for T in BEFORE AFTER; do
  echo "################ $T ################"
  grep -E "$PAT" "_w2_r572_acct_${T}.log" || echo "  (日志不存在)"
  echo ""
done
