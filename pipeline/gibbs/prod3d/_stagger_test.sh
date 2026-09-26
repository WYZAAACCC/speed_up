#!/bin/bash
# 交错方案（无 mortar，双向显式）在等温非平衡算例上的验收：
#   判据：① Γ 仍按 McLean 收敛（时标 k_att·t）② 守恒逐项对上 ③ depletion > 0
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
cd /mnt/f/speed_up/pipeline/gibbs/prod3d || exit 1
TISO=${TISO:-1800} GAMIC=${GAMIC:-0} STAGGER=1 AUTOSC=0 PRECOND=mumps \
  NLATOL=${NLATOL:-1e-7} DTMAX=${DTMAX:-1e-7} WGB=${WGB:-8e-6} DX=${DX:-2e-6} \
  python3 make_gibbs3d.py 2>&1 | tail -2
sed 's/\r$//' _run_case.sh > /tmp/rc.sh
SRC=${SRC:-/mnt/f/speed_up/pipeline/gibbs/prod3d/stage1_meltpool_gibbs3d_iso_neq.i}
CASE=${CASE:-g3d_stg}
WALL=${WALL:-900} bash /tmp/rc.sh "$CASE" "$SRC" Executioner/end_time=${ED:-1e-6} > /dev/null 2>&1
R=/root/work/$CASE
echo "Converged = $(grep -c 'Solve Converged' $R/run.log)   DidNOT = $(grep -c 'Did NOT' $R/run.log)"
grep 'GBStagger' $R/run.log | tail -3
