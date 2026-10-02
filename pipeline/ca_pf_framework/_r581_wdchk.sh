#!/bin/bash
# _r581_wdchk.sh --- ★★★★★ 看门狗**为什么没触发**？（阈值 1800，而 available 低到 54 MB）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── ① 看门狗进程（含它的状态与它跑的子 shell）──'
ps -eo pid,ppid,stat,etime,args --no-headers 2>/dev/null | grep -E 'memguard|softguard' | grep -v grep | cut -c1-110
echo
echo '── ② 看门狗的日志（有没有报警行）──'
tail -6 _w2_r581_memguard.log 2>/dev/null || echo '  （无）'
echo
echo '── ③ 关键：看门狗**算 END 用的 bc 在不在**（不在 ⇒ 它的 while 循环可能根本没跑）──'
command -v bc || echo '  ❌ bc 不在！'
echo "  试算：HOURS=6 ⇒ \$(echo "6 * 3600" | bc -l) = [$(echo "6 * 3600" | bc -l 2>&1)]"
echo
echo '── ④ 它的主循环是否还活着（看 END 与 now 的比较）──'
# 复现它的逻辑
HOURS=6
END=$(( $(date +%s) + $(printf '%.0f' "$(echo "$HOURS * 3600" | bc -l 2>/dev/null || echo 0)") ))
NOW=$(date +%s)
echo "  END=$END  NOW=$NOW  差=$(( END - NOW )) s"
[ "$NOW" -lt "$END" ] && echo '  ⇒ 逻辑上**仍在窗口内**' || echo '  ⇒ **已过窗口**'
echo
echo '── ⑤ 它启动的时刻（13:43:01）到现在的时长 ──'
echo "  $(( ($(date +%s) - $(date -d '13:43:01' +%s)) / 60 )) min"
echo
echo '── ⑥ 当前 available（与 1800 对比）──'
awk '/MemAvailable/{printf "  available=%.0f MB\n", $2/1024}' /proc/meminfo
