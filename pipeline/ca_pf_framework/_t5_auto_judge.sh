#!/bin/bash
# _t5_auto_judge.sh --- ★★★ 自动判定作业：到点判定 + **把结果写进 F 盘的文件**（不怕会话结束）
#
# ## 为什么必须写文件
# `pwsh-2561`/`pwsh-2562` 的判定结果只出现在**会话内的作业输出**里 ⇒
# **若会话结束，结果就丢了**（而判定要 1–13 小时才出来）。
# **⇒ 本作业把每一步都**追加到 F 盘的 `_w2_t5_auto_judge.log`**，任何人/任何会话都能读到。**
#
# ## 覆盖的里程碑（各自判据**预先写死**在既有工具里，本作业不改它们）
#   M1  `t5V2` 形核事件 >= 23 或 fresh >= 1  ⇒ 跑 `_t5_v2judge.sh`（判 ④⑥）
#   M2  `t5H3` 末步 >= 1400 / snap_01400    ⇒ 跑充填率序列（验"紧凑场 <6"的预测）
#   M3  `t5H3`/`t5V2` 的 `nf2 > 0`           ⇒ 判据④ 的直接签名（**一出现就报**）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_auto_judge.log
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; echo "[$(date '+%F %T')] $*"; }

say '════════ 自动判定作业启动 ════════'
say "覆盖：M1 t5V2 事件#23 ⇒ 判决器 | M2 snap_01400 ⇒ 充填率序列 | M3 nf2>0 ⇒ 判据④签名"
say "本作业的全部输出**同时写入 $LOG**（F 盘）⇒ 会话结束也不丢"

DONE1=0; DONE2=0; DONE3=0
DEADLINE=$(( $(date +%s) + 21600 ))      # 最多 6 小时
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  # ── M1 ──
  if [ "$DONE1" = 0 ]; then
    N=$(grep -c 'athermal 形核' _w2_t5_short_t5V2.log 2>/dev/null); [ -z "$N" ] && N=0
    F=$(grep -c '模式 \*\*fresh\*\*' _w2_t5_short_t5V2.log 2>/dev/null); [ -z "$F" ] && F=0
    if [ "$N" -ge 23 ] || [ "$F" -ge 1 ]; then
      say "════ M1 到点：t5V2 事件 = $N，fresh = $F ════"
      bash _t5_v2judge.sh >> "$LOG" 2>&1
      DONE1=1
    fi
  fi
  # ── M2 ──
  if [ "$DONE2" = 0 ] && [ -f _exp/_bk_t5/dry_t5H3/snap_01400.npz ]; then
    say '════ M2 到点：snap_01400 ════'
    $PY _t5_fillts.py >> "$LOG" 2>&1
    $PY _t5_fill.py _exp/_bk_t5/dry_t5H3/snap_01400.npz 62.5 >> "$LOG" 2>&1
    DONE2=1
  fi
  # ── M3：nf2 一出现就报（判据④ 的直接签名）──
  if [ "$DONE3" = 0 ]; then
    for t in t5H3 t5V2; do
      V=$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | awk -F, '{for(i=1;i<=NF;i++) if($i!="" && $i!="nan") v=$i; print v}')
      # 用 python 稳妥取 nf2 列
      V=$($PY - "$t" <<'PYEOF' 2>/dev/null
import csv,sys
t=sys.argv[1]
try:
    rows=list(csv.DictReader(open('_exp/_bk_t5/dry_%s/series.csv'%t,newline='')))
except Exception: print(''); raise SystemExit
for r in reversed(rows):
    v=(r.get('nf2') or '').strip()
    if v not in ('','nan'):
        print(v); raise SystemExit
print('')
PYEOF
)
      if [ -n "$V" ] && [ "$V" != "0.0" ] && [ "$V" != "0" ]; then
        say "════ M3 到点：**$t 的 nf2 = $V > 0** ⇒ 判据④ 的直接签名出现！ ════"
        $PY _t5_v2judge.sh >> "$LOG" 2>&1
        bash _t5_both.sh >> "$LOG" 2>&1
        DONE3=1
        break
      fi
    done
  fi
  if [ "$DONE1" = 1 ] && [ "$DONE2" = 1 ] && [ "$DONE3" = 1 ]; then
    say '════ 三个里程碑都已完成 ⇒ 作业结束 ════'; break
  fi
  sleep 60
done
say "════ 作业结束（DONE1=$DONE1 DONE2=$DONE2 DONE3=$DONE3）════"
say "⇒ 结果已全部写入 $_exp 之外的 $LOG（F 盘）"
