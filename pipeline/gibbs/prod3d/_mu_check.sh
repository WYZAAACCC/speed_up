#!/bin/bash
# 把两处 mu 提供者的原文打出来（不看计数，看文字）
set +u
cd /mnt/f/speed_up/pipeline/gibbs/prod3d || exit 1
for f in stage1_meltpool_gibbs3d_mpA.i stage1_meltpool_gibbs3d_mpB.i; do
  echo "=========== $f"
  grep -n 'mu_barrier_const' "$f"
  grep -n 'mu_barrier_gibbs' "$f"
  echo "--- [Materials] 段内真正的 mu 提供者 ---"
  awk '/^\[Materials\]/,/^\[\]/' "$f" | grep -n 'property_name' | grep -E 'mu|M|L|f_loc|kappa|DGB|kex|F_at' | head -12
done
