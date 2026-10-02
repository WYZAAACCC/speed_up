#!/bin/bash
# _r581_wdprot.sh --- 起**带 PROTECT 名单**的看门狗（R162 的改进），并核对队列/P42 风险
cd "$(dirname "$0")" || exit 1
LOG=_w2_r581_wdprot.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

say "=== R581-R162：起带 PROTECT 的看门狗 ==="

# ① 停掉不带 PROTECT 的那条
for p in $(pgrep -f '_r581_memguard.sh' 2>/dev/null); do
  kill -TERM "$p" 2>/dev/null && say "  TERM 旧看门狗 pid=$p"
done
sleep 2
for p in $(pgrep -f '_r581_memguard.sh' 2>/dev/null); do
  kill -9 "$p" 2>/dev/null && say "  KILL 旧看门狗 pid=$p"
done
sleep 2

# ② 确认没有臂被杀
say "换之前的臂："
bash _r581_arms.sh 2>/dev/null | sed -n '4,9p' | tee -a "$LOG"

# ③ 起带 PROTECT 的（把 N=160 的臂名都放进去 —— 它们是 Part 2 主线）
PROT='p2_m12ov p2_m20 p2_m12 p2_m12b p2_b5 p2_m20b'
say "起：阈值 1500 MB、8 h、KILL=1、PROTECT='${PROT}'"
nohup setsid bash _r581_memguard.sh 1500 8 1 "$PROT" > _w2_r581_memguard_outer.log 2>&1 < /dev/null &
sleep 4
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '_r581_memguard.sh 1500' | grep -v grep | cut -c1-100 | tee -a "$LOG"
tail -1 _w2_r581_memguard.log | tee -a "$LOG"

# ④ ★ P42 风险核对：在跑的臂，**它的启动器还在吗**
say ""
say "④ P42 风险核对（臂 vs 它的启动器）"
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  ppid=$(awk '{print $4}' "/proc/$p/stat" 2>/dev/null)
  pc=$(tr '\0' ' ' < "/proc/$ppid/cmdline" 2>/dev/null | cut -c1-58)
  printf '  臂 %-10s pid=%-7s 父 pid=%-7s 父=「%s」\n' "$tag" "$p" "$ppid" "$pc"
done
say ""
say "在跑的队列/启动脚本："
ps -eo pid,ppid,etime,args --no-headers 2>/dev/null \
  | grep -E '_r581_(mqueue|mn64|p2q|mqueue[0-9])' | grep -v grep | cut -c1-88 | sed 's/^/  /' | tee -a "$LOG"
say "  （若某条臂的父进程已不存在、且没有队列在跑 ⇒ 它随时可能被回收，见 P42）"
say "=== R581-R162 WDPROT DONE ==="
