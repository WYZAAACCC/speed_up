#!/usr/bin/env bash
# _dryrun_t17.sh --- **T17 驱动器的冒烟验证**：用极小规格把三根轴各跑一遍，
#   确认它能产出正确的表 + 判据（`MEASUREMENT_SPEC R0` 用在**驱动器**上：
#   先证工具能跑，再花几小时跑真算例）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
{
  $PY -c "import ast;ast.parse(open('T17_converge.py').read());print('SYNTAX OK')" || exit 2
  for AX in dx L nv; do
    echo "########## T17 轴 = $AX（冒烟：L=1.6 µm Δx=50 nm n=64 f_target=0.015）##########"
    timeout 1800 $PY -u T17_converge.py --axis $AX --L-um 1.6 --dx-nm 50 --n 64 \
            --f-target 0.015 --adv proj2
    echo "RC_$AX=$?"
  done
  echo ALL_DONE
} > _t17_dryrun.log 2>&1
