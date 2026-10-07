#!/usr/bin/env bash
# _regress_sweep.sh --- **全量回归扫描**（`MEASUREMENT_SPEC R8`：改了常数/默认之后
#   必须重跑所有引用它的判据）。本会话改了 5 处：D17（adv_grad 默认）、A1（曲率默认）、
#   A2（reinit 守卫）、D7（T0/Ms/ΔG/DS）、Δf（2e8→3.5e8）。
#   本脚本只跑**便宜**的判据（N≤64、步数少），贵的（T11/T12/T13/T15/T16/T19H）另行。
#   逐条打印 PASS/FAIL，最后汇总。**只读验证，不改任何生产文件。**
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
{
  for T in T1_verify_edsign T2_verify_reinit T4_verify_no_partition \
           T5_verify_signs T6_verify_Tschedule T7_verify_dGsens; do
    echo "########## $T ##########"
    timeout 1200 $PY -u $T.py 2>&1 | grep -v -e RuntimeWarning -e 'self.reinitialize'
    echo "RC_${T}=$?"
    echo
  done
  echo ALL_DONE
} > _regress_sweep.log 2>&1
