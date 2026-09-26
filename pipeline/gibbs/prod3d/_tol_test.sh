#!/bin/bash
# 扫 nl_abs_tol：看"给体相的那个汇"（~1e-17/节点）在哪个容差下才被解出来。
# 判据：depletion 由负转正（= 晶界真的从体相抽走了溶质）+ 守恒逐项平衡。
set +u
cd /mnt/f/speed_up/pipeline/gibbs/prod3d || exit 1
sed 's/\r$//' _run_case.sh > /tmp/rc.sh
for T in "$@"; do
  echo "########## nl_abs_tol = $T ##########"
  TISO=1800 GAMIC=0 DISP=1 AUTOSC=0 PRECOND=mumps NLATOL="$T" DTMAX=1e-7 \
    WGB=8e-6 DX=2e-6 python3 make_gibbs3d.py > /dev/null 2>&1
  WALL=900 bash /tmp/rc.sh "g3dtol_$T" \
    /mnt/f/speed_up/pipeline/gibbs/prod3d/stage1_meltpool_gibbs3d_iso_neq.i \
    Executioner/end_time=1e-6 2>&1 | grep -E 'rc=|未收敛|^time|^1e-06'
done
