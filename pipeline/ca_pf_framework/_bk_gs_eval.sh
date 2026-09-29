#!/usr/bin/env bash
# _bk_gs_eval.sh —— 对 gs2（长出来的块）跑：逐板条 + 判决
# 用法: bash _bk_gs_eval.sh
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
echo "######## 逐板条（gs2 = 长出来的块）"
"$PY" _bk_perlath.py _exp/_bk_gs/dry_gs2
echo
echo "######## 判决 V-1..V-5 + V-1g（gs2）"
"$PY" _bk_verdict.py --root _exp/_bk_gs --tag gs2 --arms dry
echo
echo "######## 预装臂对照（dry_p2, N=192）"
"$PY" _bk_verdict.py --root _exp/_bk_block --tag p2 --arms dry
