#!/bin/bash
# _r1_compileall.sh --- 本轮碰过的脚本全部做一次语法检查
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
FAIL=0
for f in _r1_exp.py _r1_analyze.py _r1_aniso.py _r1_dxconsist.py \
         _r1_driftchk.py _r1_armhealth.py _r1_sigprove.py _r1_axisswap.py \
         _r1_c5scale.py _r1_c5chk.py _r1_g2mode.py _r1_csvfixchk.py \
         _r1_stepaxis.py _r1_smokechk.py _r1_paircorr.py _r1_pairgeo2.py \
         _r1_tracechk.py _r1_alignchk.py _r1_cfgcmp.py; do
  if $PY -m py_compile "$f" 2>/dev/null; then
    echo "OK   $f"
  else
    echo "FAIL $f"; FAIL=$((FAIL+1))
  fi
done
echo "---- 失败 $FAIL 个 ----"
echo
echo "=== 队列存活情况 ==="
pgrep -af '_r1_drive4|_r1_waitdx' | head -3
echo
echo "=== 在跑的算例数 ==="
pgrep -c -f '_r1_exp\.py'
