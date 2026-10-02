#!/bin/bash
# _r581_launch160.sh --- 起 N=160 的 A4 判决实验（**带 P42 防护：setsid nohup + disown**）
cd "$(dirname "$0")" || exit 1
LOG=_w2_r581_alloc160.log
echo "[$(date '+%F %T')] 启动器：起 N=160 A/B" | tee -a "$LOG"
# ★ 若已在跑就别重复起（防两条 A/B 抢内存）
if pgrep -f '_r581_alloc160.sh' >/dev/null 2>&1; then
  echo "  ⚠ 已有 _r581_alloc160.sh 在跑 ⇒ 不重复起" | tee -a "$LOG"
  exit 0
fi
setsid nohup bash _r581_alloc160.sh > _w2_r581_alloc160_outer.log 2>&1 < /dev/null &
disown 2>/dev/null || true
sleep 25
echo "  ── 它的进程 ──" | tee -a "$LOG"
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E '_r581_alloc160.sh|_bk_exp.py.*dry_alloc' | grep -v grep | cut -c1-104 | tee -a "$LOG"
for p in $(pgrep -f '_bk_exp.py.*_bk_alloc160' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  rss=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  echo "  臂 ${tag:-?} pid=$p RSS=${rss}MB ✓" | tee -a "$LOG"
done
echo "  ── 日志尾 ──" | tee -a "$LOG"
tail -4 "$LOG" | sed 's/^/    /'
