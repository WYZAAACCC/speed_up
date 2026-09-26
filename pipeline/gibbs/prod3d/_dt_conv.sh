#!/bin/bash
# 【A5 判据】显式交错方案的时间收敛性：dt 减半 ⇒ 与"精确解"的差应减半（一阶）
#   用 ConstantDT 固定步长（自适应步长会让三次跑的 dt 不一样，无法比较）。
#   量的对象：末态 gam_int（面上的 Γ 总量）与 c_int_pp（体相库存）。
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
cd /mnt/f/speed_up/pipeline/gibbs/prod3d || exit 1
sed 's/\r$//' _run_case.sh > /tmp/rc.sh
for DT in 1e-7 5e-8 2.5e-8; do
  echo "########## dt = $DT ##########"
  WALL=900 bash /tmp/rc.sh "g3d_dtc_$DT" \
    /mnt/f/speed_up/pipeline/gibbs/prod3d/stage1_meltpool_gibbs3d_iso_neq.i \
    Executioner/end_time=4e-7 Executioner/TimeStepper/type=ConstantDT \
    Executioner/TimeStepper/dt=$DT -w > /dev/null 2>&1
  R=/root/work/g3d_dtc_$DT
  echo "Converged = $(grep -c 'Solve Converged' $R/run.log)  DidNOT = $(grep -c 'Did NOT' $R/run.log)"
  tail -1 $R/case_out.csv | cut -d, -f1,12,18,21
done
