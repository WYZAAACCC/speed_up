#!/usr/bin/env bash
# _run_a2regress.sh --- A2 修法验证：T23（零位移 / 区域保真）+ T2（reinit 目标梯度回归）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
{
  echo "########## T23（A2：零位移 + region 保真）##########"
  $PY -u T23_verify_reinit.py --N 64 --dx-nm 50 --steps 200
  echo "RC_T23=$?"
  echo "########## T2 回归（reinit 目标梯度 |∇φ|=1）##########"
  $PY -u T2_verify_reinit.py 2>&1 | tail -20
  echo "RC_T2=$?"
  echo ALL_DONE
} > _a2_regress.log 2>&1
