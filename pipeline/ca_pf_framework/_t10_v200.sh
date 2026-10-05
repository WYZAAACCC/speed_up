#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10CL2
echo "════ J1/J2 逐连通分量 PCA @ step 200 ════"
$PY _t10_seven.py $TAG 200 2>&1 | tail -24
echo
echo "════ J1 全部场分量数分布 ════"
$PY _t10_allfields.py $TAG 200 2>&1 | tail -9
echo
echo "════ J3 块表（CSV）════"
$PY _t10_seven.py $TAG 200 2>&1 | tail -9
