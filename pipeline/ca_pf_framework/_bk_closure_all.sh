#!/bin/bash
# _bk_closure_all.sh —— ★ **闭环总检**：一条命令跑完全部自动检查，输出一张 PASS/FAIL 表。
#
# 这是给"挑毛病的人"用的入口：把 R29 建立的**全部**守卫一次跑完。
# 分三类：
#   A. 闭式与判据（windowB_closure 的正/负对照）
#   B. 工具自身的正/负对照（量具、报告生成、athermal 核验、引擎恒等性）
#   C. 一致性（文档数字 vs 代码、参数完备性、一条命令 == 长命令行、归档逐位）
#
# 用法： bash _bk_closure_all.sh            （约 6–10 min，`_bk_nuc_identity` 最慢）
#        SKIP_SLOW=1 bash _bk_closure_all.sh   （跳过引擎恒等性，约 1 min）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
LOG=_w2_bk_closure_all.log
: > "$LOG"
SKIP_SLOW="${SKIP_SLOW:-0}"

row () {   # $1=名称 $2=命令 $3=判据正则（取最后一条匹配）
  local name="$1" cmd="$2" pat="$3"
  echo "=== $name ===" >> "$LOG"
  local out
  out=$(eval "$cmd" 2>&1)
  echo "$out" >> "$LOG"
  local line
  line=$(echo "$out" | grep -aE "$pat" | tail -1)
  printf '  %-46s %s\n' "$name" "${line:-（没有匹配到判据行 —— 去看 $LOG）}"
}

{
  echo "############ A. 闭式与判据"
} >> "$LOG"
echo "================ 闭环总检（$(date '+%F %T')） ================"
row "A1 windowB_closure 正/负对照" \
    "$PY -u windowB_closure.py" 'FAIL ='
row "A2 _bk_closure_report 参数表完整性" \
    "$PY -u _bk_closure_report.py --selftest" 'FAIL ='

{
  echo "############ B. 工具自身的正/负对照"
} >> "$LOG"
row "B1 _bk_measure 量具" \
    "$PY _bk_measure.py --selftest" 'FAIL ='
row "B2 _bk_athermal athermal 核验" \
    "$PY -u _bk_athermal.py --selftest" 'FAIL ='
if [ "$SKIP_SLOW" = "1" ]; then
  printf '  %-46s %s\n' "B3 _bk_nuc_identity 引擎恒等性" "（SKIP_SLOW=1 ⇒ 跳过）"
else
  row "B3 _bk_nuc_identity 引擎恒等性" \
      "$PY -u _bk_nuc_identity.py" 'FAIL ='
fi

{
  echo "############ C. 一致性"
} >> "$LOG"
row "C1 文档数字 vs 代码（_bk_docnum）" \
    "$PY -u _bk_docnum.py" '不一致/过时项 ='
row "C2 参数完备性（_bk_param_audit）" \
    "$PY -u _bk_param_audit.py" '没提到的：'
row "C3a 一条命令 == 长命令行（参数逐项）" \
    "$PY -u _bk_closedcheck.py" '不一致项 ='
row "C3b 该配置本身合法（6 条独立判据）" \
    "$PY -u _bk_closedcheck.py" '不合法项 ='
row "C4 归档默认路径逐位（_bk_defcheck def1）" \
    "$PY -u _bk_defcheck.py def1" '共有列'
row "C5 归档默认路径逐位（_bk_defcheck def3）" \
    "$PY -u _bk_defcheck.py def3" '共有列'
row "C6 归档 eng12 判决复现（V-8b 应 PASS）" \
    "$PY _bk_verdict.py --root _exp/_bk_eng --tag eng12 --arms eng --ctrl-tag L200" 'V-8b'

echo "---------------------------------------------------------------"
echo "完整输出：$LOG"
echo "★ 逐条读法见 BLOCK_PARAM_CLOSURE.md §5；任何一条 FAIL 都必须先当**真问题**查。"
