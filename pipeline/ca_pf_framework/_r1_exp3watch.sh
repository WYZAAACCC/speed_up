#!/bin/bash
# _r1_exp3watch.sh --- 实验 3（验收靶 `mid192_ns4b`）跑完后，自动出**完整**判决
#
# 为什么需要
# ----------
# 队列 v4 的 `analyze()` 只对 `mid192_ns4b` 调了 `_r1_aniso.py`（有效窗口的各向异性）。
# 但实验 3 是**验收靶**，它的判决还需要另外三样，v4 都没做：
#   ① `_r1_analyze.py` 的 **C-1…C-6 判据表 + 守卫汇总**（正式判决表）；
#   ② **复现性检查** `_r1_dxcurve.py mid192_ns4 mid192_ns4b`
#      —— 两者配置完全相同，配对曲线重合才说明重做有效（这是重做的**前提**）；
#   ③ `_r1_bkchk.py` 的**记账列正确性**（新列的 P-1…P-5）。
#
# ⚠ 等待逻辑要区分"还没开始"与"已经结束"（`_r1_a3watch.sh` 第一版在此栽过：
#   `pgrep` 在"没启动"时也返回非零 ⇒ 循环立刻退出、在空数据上跑分析）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
set +e
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_r1exp3watch.log
T=mid192_ns4b
: > "$LOG"
log () { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

running () { pgrep -f "_r1_exp.py --out _exp/$T" > /dev/null 2>&1; }

log "等 $T **启动**……"
n=0
while true; do
  if running || [ -f "_exp/$T/series.csv" ]; then break; fi
  n=$((n + 1)); [ $((n % 30)) = 0 ] && log "  …仍在等启动（$((n/2)) 分钟）"
  sleep 120
done
log "$T 已启动，等它结束……"
while running; do sleep 120; done
log "$T 结束 —— 出完整判决"

log "--- ① C-1…C-6 判据表 + 守卫汇总（`_r1_analyze.py`）---"
$PY -u _r1_analyze.py --dx-nm 125 --every 5 "_exp/$T" >> "$LOG" 2>&1

log "--- ② 复现性检查：$T vs mid192_ns4（配置相同，曲线重合 ⇒ 重做有效）---"
$PY -u _r1_dxcurve.py mid192_ns4 "$T" >> "$LOG" 2>&1

log "--- ③ 有效窗口各向异性（`_r1_aniso.py`）---"
$PY -u _r1_aniso.py "$T" >> "$LOG" 2>&1

log "--- ④ 记账列正确性（`_r1_bkchk.py` P-1…P-5）---"
$PY -u _r1_bkchk.py "$T" >> "$LOG" 2>&1

log "==== 实验 3 完整判决完成。口径：比率看 ③、判据看 ①、有效性看 ②、数据可信看 ④ ===="
