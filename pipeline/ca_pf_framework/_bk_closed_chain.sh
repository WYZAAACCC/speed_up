#!/bin/bash
# _bk_closed_chain.sh —— 闭环算例的**无人值守链**：
#   ① 等 cl1 / cl1g 跑完
#   ② 起**步数配对**的量具正对照 clctrl（gpos：F3 面能强制 100 J/m²）
#      —— 归档的 gpos_L200 只有 200 步、Δx 差 2 倍，拿它判 V-6 会**假 FAIL**
#      （`_bk_verdict.py` 自己就打印了这条警告）
#   ③ 跑完整证据包（A-1..A-8 / V-1..V-8b / 对照读数 / 工具自检）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
LOG=_w2_bk_closed_chain.log
: > "$LOG"

wait_for () {   # $1 = tag
  while pgrep -f "tag $1" > /dev/null 2>&1; do sleep 30; done
}

{
  echo "=== $(date '+%F %T') 等 cl1 / cl1g ==="
} >> "$LOG"
wait_for cl1
wait_for cl1g
echo "=== $(date '+%F %T') cl1/cl1g 结束 ===" >> "$LOG"

{
  echo "=== $(date '+%F %T') 起配对正对照 clctrl（arm=gpos, γ0=0.25, 同 2853 步）==="
} >> "$LOG"
"$PY" -u _bk_closed.py --arm gpos --gamma 0.25 --tag clctrl --run >> "$LOG" 2>&1
echo "=== $(date '+%F %T') clctrl 结束 ===" >> "$LOG"

{
  echo
  echo "################ A. athermal 律核验 A-1..A-8 —— cl1"
  "$PY" -u _bk_athermal.py --root _exp/_bk_closed --tag cl1 2>&1
  echo
  echo "################ A'. 单变量隔离臂 cl1g（γ_F1=0.15，其余逐字相同）"
  "$PY" -u _bk_athermal.py --root _exp/_bk_closed --tag cl1g 2>&1 | tail -14
  echo
  echo "################ B. 标准判决 V-1..V-8b（正对照 = **配对的** clctrl）—— cl1"
  "$PY" _bk_verdict.py --root _exp/_bk_closed --tag cl1 --arms dry \
      --ctrl-root _exp/_bk_closed --ctrl-arm gpos --ctrl-tag clctrl 2>&1
  echo
  echo "################ B'. 同一判决的 V-* 摘要 —— cl1g"
  "$PY" _bk_verdict.py --root _exp/_bk_closed --tag cl1g --arms dry \
      --ctrl-root _exp/_bk_closed --ctrl-arm gpos --ctrl-tag clctrl 2>&1 \
      | grep -E 'V-[0-9]'
  echo
  echo "################ C. 末态读数对照（cl1 / cl1g / 归档 eng12）"
  "$PY" -u _bk_readsum.py _exp/_bk_closed/dry_cl1 _exp/_bk_closed/dry_cl1g \
      _exp/_bk_eng/eng_eng12 2>&1
  echo
  echo "################ D. 工具自检"
  "$PY" _bk_measure.py --selftest 2>&1 | tail -2
  "$PY" windowB_closure.py 2>&1 | tail -2
  "$PY" _bk_athermal.py --selftest 2>&1 | tail -2
  "$PY" _bk_nuc_identity.py 2>&1 | grep -E 'FAIL ='
} >> "$LOG" 2>&1
echo "=== CLOSED CHAIN DONE $(date '+%F %T') ===" >> "$LOG"
