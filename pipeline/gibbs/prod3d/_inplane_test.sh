#!/bin/bash
# 【S10 验证】沿晶界方向的 Γ 阶跃初值 + k_att=0（隔离体相交换）：
#   开面内扩散 ⇒ gam_max 降、gam_min 升（沿晶界铺平）
#   关面内扩散 ⇒ 两者都不动
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
cd /mnt/f/speed_up/pipeline/gibbs/prod3d || exit 1
sed 's/\r$//' _run_case.sh > /tmp/rc.sh
for IP in 0 1; do
  echo "########## INPLANE = $IP ##########"
  TISO=1800 GAMIC=0 GAMSTEP=1 INPLANE=$IP STAGGER=1 AUTOSC=0 PRECOND=mumps \
    NLATOL=1e-7 DTMAX=1e-7 WGB=8e-6 DX=2e-6 python3 make_gibbs3d.py > /dev/null 2>&1
  WALL=900 bash /tmp/rc.sh "g3d_ip$IP" \
    /mnt/f/speed_up/pipeline/gibbs/prod3d/stage1_meltpool_gibbs3d_iso_neq.i \
    Executioner/end_time=1e-6 UserObjects/gb_stagger/k_att=0 > /dev/null 2>&1
  R=/root/work/g3d_ip$IP
  echo "Converged = $(grep -c 'Solve Converged' $R/run.log)  DidNOT = $(grep -c 'Did NOT' $R/run.log)"
  head -1 $R/case_out.csv | tr ',' '\n' | grep -n 'gam0_max\|gam0_min\|gam0_int' | tr '\n' ' '; echo
  sed -n 2p $R/case_out.csv | cut -d, -f11,12,13
  tail -1 $R/case_out.csv | cut -d, -f11,12,13
done
