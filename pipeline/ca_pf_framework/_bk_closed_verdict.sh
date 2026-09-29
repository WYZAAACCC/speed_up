#!/bin/bash
# _bk_closed_verdict.sh —— 闭环算例的**完整证据包**，一条命令跑完。
#   A.  athermal 律核验 A-1..A-8（形核温度、有序比、块完整性、体积尺度）
#   B.  标准判决 V-1..V-8b（与归档同一套判据；V-8b 窗口随 **plate.T_physical** 缩放）
#   C.  配对量具正对照 V-6（`clctrlb`，同几何同步数，只差 F3 面能 = 100 J/m²）
#   D.  末态读数对照（闭环 / 归档 / **未补偿的旧跑**）
#   E.  工具自检
# 用法：bash _bk_closed_verdict.sh [tag] [ctrl-tag]
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
TAG="${1:-cl1b}"
CTRL="${2:-clctrlb}"
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
LOG=_w2_bk_closed_verdict.log
: > "$LOG"
{
  echo "################ A. athermal 律核验 A-1..A-8 —— $TAG"
  "$PY" -u _bk_athermal.py --root _exp/_bk_closed --tag "$TAG" 2>&1
  echo
  echo "################ A'. 单变量隔离臂 cl1gb（γ_F1 = 0.15，其余逐字相同）"
  "$PY" -u _bk_athermal.py --root _exp/_bk_closed --tag cl1gb 2>&1 | tail -14
  echo
  echo "################ A''. α_KM 敏感度臂 cln2（α=5e-3 ⇒ 导出 n=2）"
  "$PY" -u _bk_athermal.py --root _exp/_bk_closed --tag cln2 2>&1 | tail -14
  echo
  echo "################ B. 标准判决 V-1..V-8b（配对正对照 = $CTRL）—— $TAG"
  "$PY" _bk_verdict.py --root _exp/_bk_closed --tag "$TAG" --arms dry \
      --ctrl-root _exp/_bk_closed --ctrl-arm gpos --ctrl-tag "$CTRL" 2>&1
  echo
  echo "################ B'. 同一判决的 V-* 摘要 —— cl1gb / cln2"
  for T in cl1gb cln2; do
    echo "--- $T"
    "$PY" _bk_verdict.py --root _exp/_bk_closed --tag "$T" --arms dry \
        --ctrl-root _exp/_bk_closed --ctrl-arm gpos --ctrl-tag "$CTRL" 2>&1 \
        | grep -E 'V-[0-9]'
  done
  echo
  echo "################ C. CFL 实际用量（R29 新列）"
  "$PY" -u _bk_cfl.py _exp/_bk_closed/gpos_$CTRL _exp/_bk_closed/dry_$TAG \
      _exp/_bk_closed/dry_cl1 2>&1
  echo
  echo "################ D. 末态稳健厚度（剔孤儿；判据靶 = plate.T_physical）"
  "$PY" -u _bk_thick.py _exp/_bk_closed/dry_$TAG _exp/_bk_closed/dry_cl1 \
      _exp/_bk_eng/eng_eng12 2>&1
  echo
  echo "################ D'. 末态读数对照"
  "$PY" -u _bk_readsum.py _exp/_bk_closed/dry_$TAG _exp/_bk_closed/dry_cl1gb \
      _exp/_bk_closed/dry_cln2 _exp/_bk_closed/dry_cl1 _exp/_bk_eng/eng_eng12 2>&1
  echo
  echo "################ E. 工具自检"
  "$PY" _bk_measure.py --selftest 2>&1 | tail -2
  "$PY" windowB_closure.py 2>&1 | tail -2
  "$PY" _bk_athermal.py --selftest 2>&1 | tail -2
  "$PY" _bk_nuc_identity.py 2>&1 | grep -E 'FAIL ='
} >> "$LOG" 2>&1
echo "=== CLOSED VERDICT DONE $(date '+%F %T') ===" >> "$LOG"
