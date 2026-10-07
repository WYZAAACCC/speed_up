#!/usr/bin/env bash
# _run_a1regress.sh --- A1 改成默认后的三条回归（T22 全量 / T9-D / T19-C）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
{
  echo "########## T22（A1 全量判据，pair_curvature 默认已改 True）##########"
  $PY -u T22_verify_paircurv.py --N 64 --dx-nm 25
  echo "RC_T22=$?"
  echo "########## T9 回归（面片身份 + 端到端最薄角）##########"
  $PY -u T9_verify_facetid.py 2>&1 | tail -12
  echo "RC_T9=$?"
  echo "########## T19-C（球：粗糙度 + 半径，已知答案）##########"
  $PY -u T19_verify_proj.py --stage C --steps 120 2>&1 | tail -18
  echo "RC_T19=$?"
  echo ALL_DONE
} > _a1_regress.log 2>&1
