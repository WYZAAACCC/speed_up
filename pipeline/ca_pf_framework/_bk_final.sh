#!/usr/bin/env bash
# _bk_final.sh —— 目标收官的**证据包**（一条命令跑完）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
echo "################ A. 默认路径 == 已验配置（逐位）"
"$PY" _bk_defcheck.py 2>&1 | tail -3
echo
echo "################ B. 推荐配置的完整判决（10/12）"
"$PY" _bk_verdict.py --root _exp/_bk_eng --tag eng12 --arms eng --ctrl-tag L200 2>&1 \
  | grep -E 'V-[0-9]|目录=|mtime|正对照|V-6 '
echo
echo "################ C. 三随机种子的稳健性"
"$PY" _bk_rscores.py eng12 eng13 eng14 2>&1 | grep -E '臂 |R-1|R-2|R-3|R-4'
echo
echo "################ D. 量具自检（对照条数）"
"$PY" _bk_measure.py --selftest 2>&1 | tail -3
echo
echo "################ E. 引擎恒等性（默认路径逐位不变）"
"$PY" -u _bk_nuc_identity.py 2>&1 | grep -E '^  U-1|FAIL ='
