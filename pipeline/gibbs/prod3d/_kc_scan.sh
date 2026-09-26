#!/bin/bash
# S9 诊断：扫 κ_c（溶质界面宽度 ξ_c = sqrt(κ_c/f̃_cc)），看
#   ① c_min 是否还 < 0   ② 2Δx 棋盘振荡幅度   ③ 收敛性
#   ⚠ 关键论点：Gibbs 表示把"Γ 挂在面上"之后，κ_c **不再受 wGB 约束**
#     （弥散表示下必须 ξ_c ≪ wGB），所以可以纯粹按"网格能不能解析"来选 κ_c。
set +u
cd /mnt/f/speed_up/pipeline/gibbs/prod3d || exit 1
sed 's/\r$//' _run_case.sh > /tmp/rc.sh
for KC in "$@"; do
  echo "########## kappa_c = $KC ##########"
  WALL=800 bash /tmp/rc.sh "g3d_kc_$KC" \
    /mnt/f/speed_up/pipeline/gibbs/prod3d/stage1_meltpool_gibbs3d.i \
    Executioner/end_time=3e-7 Materials/ch_kappa/prop_values=$KC > /dev/null 2>&1
  R=/root/work/g3d_kc_$KC
  echo "Converged = $(grep -c 'Solve Converged' $R/run.log)   DidNOT = $(grep -c 'Did NOT' $R/run.log)"
  tail -1 $R/case_out.csv | cut -d, -f7,9,15,16
  cp -f $R/case_out.csv /mnt/f/speed_up/pipeline/gibbs/prod3d/results_kc_$KC/ 2>/dev/null || {
    mkdir -p /mnt/f/speed_up/pipeline/gibbs/prod3d/results_kc_$KC
    cp -f $R/case_out.csv /mnt/f/speed_up/pipeline/gibbs/prod3d/results_kc_$KC/
  }
  cp -f $R/case_out_profile_*.csv /mnt/f/speed_up/pipeline/gibbs/prod3d/results_kc_$KC/ 2>/dev/null
done
