#!/usr/bin/env bash
# _run_t19_all.sh --- 并行跑 T19 的三条独立 stage（C/Cr、E、F），各自落日志。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1

$PY -c "import ast;[ast.parse(open(f).read()) for f in ('windowB_surface.py','T19_verify_proj.py')];print('SYNTAX OK')"
$PY -c "import windowB_surface as W;print('IMPORT OK',hasattr(W,'upwind_flux_vec'))" || exit 2

nohup $PY -u T19_verify_proj.py --stage C,Cr --steps 120 > _t19_C.log 2>&1 &
P1=$!
nohup $PY -u T19_verify_proj.py --stage E > _t19_E.log 2>&1 &
P2=$!
nohup $PY -u T19_verify_proj.py --stage F > _t19_F.log 2>&1 &
P3=$!
echo "launched C/Cr=$P1 E=$P2 F=$P3"
wait $P1; echo "C/Cr rc=$?"
wait $P2; echo "E rc=$?"
wait $P3; echo "F rc=$?"
echo ALL_DONE
