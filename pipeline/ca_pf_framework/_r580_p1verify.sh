#!/bin/bash
# _r580_p1verify.sh --- P1 修完后的**端到端复核**：① 真实路径 9 臂二分  ② 全量逐位回归 + 冒烟
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
LOG=_w2_r580_p1verify.log
: > "$LOG"
say() { echo "$@" | tee -a "$LOG"; }

say "======== ① 真实路径 9 臂二分（P1 修后）$(date '+%F %T') ========"
bash _r580_bisect.sh > _w2_r580_bisect2.log 2>&1
say "  bisect rc=$?"
/root/miniconda3/envs/ml/bin/python _r580_bisect_cmp.py 2>&1 | tee -a "$LOG"

say ""
say "======== ② `E_el_J` 绝对值复核 $(date '+%F %T') ========"
/root/miniconda3/envs/ml/bin/python _r580_elj.py 2>&1 | tee -a "$LOG"

say ""
say "======== ③ 全量逐位回归 + 真实路径冒烟（含快照）$(date '+%F %T') ========"
bash _r580_snapshot.sh afterP1 "P1 修完后的代码（onfly 诊断口径已对齐）" >/dev/null 2>&1
say "  快照：$(ls -dt _r580_backup/afterP1_* 2>/dev/null | head -1)"
bash _r576_regress.sh > _w2_r580_regress2.log 2>&1
say "  regress rc=$?"
grep -E '共有列|逐位一致|FAIL *=|总判定|自检' _w2_r580_regress2.log | tail -6 | sed 's/^/    /' | tee -a "$LOG"

say ""
say "======== ④ 真实路径冒烟（默认档 + CLI 全开）$(date '+%F %T') ========"
bash _r580_smoke_cli.sh > _w2_r580_smoke_cli2.log 2>&1
say "  smoke rc=$?"
grep -E 'C-1a|C-1b|exit=|算子开关|C-2|C-3|C-4|共有列|✅|❌' _w2_r580_smoke_cli2.log \
  | sed 's/^/    /' | tee -a "$LOG"

say ""
say "======== DONE $(date '+%F %T') ========"
