#!/bin/bash
# 熔池算例：单侧低维块（TWOSIDE=0）+ 交错扣账，看能不能过第 1 步
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
cd /mnt/f/speed_up/pipeline/gibbs/prod3d || exit 1
TWOSIDE=${TWOSIDE:-0} SINK=${SINK:-1} PRECOND=mumps NLATOL=1e-7 DTMAX=1e-7 \
  WGB=8e-6 DX=2e-6 python3 make_gibbs3d.py 2>&1 | tail -2
sed 's/\r$//' _run_case.sh > /tmp/rc.sh
ED=${ED:-3e-7}
WALL=800 bash /tmp/rc.sh "g3d_m_ts${TWOSIDE}_sk${SINK}" \
  /mnt/f/speed_up/pipeline/gibbs/prod3d/stage1_meltpool_gibbs3d.i \
  Executioner/end_time=$ED > /dev/null 2>&1
R=/root/work/g3d_m_ts${TWOSIDE}_sk${SINK}
echo "Converged = $(grep -c 'Solve Converged' $R/run.log)   DidNOT = $(grep -c 'Did NOT' $R/run.log)"
grep -m1 '0 Nonlinear' $R/run.log
grep -m2 'dM =' $R/run.log
echo "末行 [c_int_pp, depletion]:"; tail -1 $R/case_out.csv | cut -d, -f12,16
