#!/bin/bash
# 2D ????????????????????????
set +u
cd /mnt/f/speed_up/pipeline/gibbs/prod3d || exit 1
COMMON="DIM2=1 WGB=8e-6 DX=2e-6 DTMAX=1e-8 NLATOL=1e-7 PRECOND=mumps"
gen () {  # gen <suffix> <extra env>
  name="$1"; shift
  echo "=== ?? $name : $* ==="
  env $COMMON "$@" OUTSUF="_$name" python3 make_gibbs3d.py > /tmp/gen_$name.log 2>&1
  echo "  rc=$?  ??=$(wc -l < stage1_meltpool_gibbs3d_$name.i 2>/dev/null)"
}
gen k1ng   NO_GIBBS=1
gen k2t5f  T5=0
gen k3noip INPLANE=0
gen k4base X=1
gen k5dt9  DTMAX=1e-9
gen k6fine WGB=4e-6 DX=1e-6
echo "=== ????? ==="
ls -l stage1_meltpool_gibbs3d_k*.i
