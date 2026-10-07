#!/usr/bin/env bash
# _r346_covchk.sh -- 抽所有相关臂的 cov_norm 自检行
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
for f in _w2_r322_near200_run.log _w2_r322_mid200_run.log _w2_r322_far200_run.log \
         _w2_r318_edNear_run.log _w2_r318_edFar_run.log _w2_r311_run.log \
         _w2_r240.log _w2_r280_saSet2P0_run.log _w2_r280_saSet2F2P0_run.log; do
  [ -f "$f" ] || { echo "### $f  (不存在)"; continue; }
  echo "### $f"
  grep -E '块内界面自检|cov_norm|t=0 的两块异变体接触面|播种后' "$f" | head -5
  echo
done
