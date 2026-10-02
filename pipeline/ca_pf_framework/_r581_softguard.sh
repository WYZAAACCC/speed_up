#!/bin/bash
# _r581_softguard.sh --- ★ 分级内存保卫：先牺牲**最不完整**的那一臂，保住快跑完的。
#
# ## 为什么需要它（而不是只靠 `_r581_memguard.sh`）
# `_r581_memguard.sh` 在 `MemAvailable < 1800 MB` 时**杀掉全部** `_bk_exp.py`
# —— 那会**同时丢掉三臂**，包括已经跑到 step 400+ 的两臂。
# 本脚本在**更早**（默认 2600 MB）只杀**一个**指定的 tag（默认 `p2_b5ps`，
# 它是最晚起的、最不完整的）⇒ 保住已经跑了 2 小时的两臂。
#
# 用法: bash _r581_softguard.sh <先牺牲的tag> [阈值MB] [最长小时]
# ⚠ 任何 kill 都**只是停进程**；已经落盘的 `series.csv` / `snap_*.npz` **不删**。
set -u
cd "$(dirname "$0")" || exit 1
VICTIM="${1:-p2_b5ps}"
LIM="${2:-2600}"
HOURS="${3:-4}"
LOG=_w2_r581_softguard.log
END=$(( $(date +%s) + HOURS * 3600 ))
echo "[$(date '+%F %T')] softguard 启动：阈值 ${LIM} MB，先牺牲 tag=${VICTIM}，最长 ${HOURS} h" | tee -a "$LOG"
KILLED=0
while [ "$(date +%s)" -lt "$END" ]; do
  AV=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
  if [ "$AV" -lt "$LIM" ] && [ "$KILLED" -eq 0 ]; then
    P=$(pgrep -f -- "--tag ${VICTIM}[[:space:]]" | head -1 || true)
    if [ -n "$P" ]; then
      echo "[$(date '+%F %T')] ⚠ MemAvailable=${AV} MB < ${LIM} MB ⇒ 牺牲 tag=${VICTIM} (pid=$P)" | tee -a "$LOG"
      kill -TERM "$P" 2>/dev/null || true
      sleep 15
      kill -KILL "$P" 2>/dev/null || true
      KILLED=1
      echo "[$(date '+%F %T')]    已停。剩余 MemAvailable=$(awk '/MemAvailable/{print $2}' /proc/meminfo) MB" | tee -a "$LOG"
      echo "     ⚠ **已落盘的 series.csv / snap_*.npz 一律不删**；PID 记录在 `_w2_r581_p2_p2_${VICTIM}.log`" | tee -a "$LOG"
    else
      echo "[$(date '+%F %T')] ⚠ MemAvailable=${AV} MB 低，但找不到 ${VICTIM} 的进程" | tee -a "$LOG"
    fi
  fi
  sleep 20
done
echo "[$(date '+%F %T')] softguard 正常退出（杀了 ${KILLED} 次）" | tee -a "$LOG"
