#!/bin/bash
# _t5_start_keeper_all.sh --- 正确启动三监控守护（**setsid**，不经 PowerShell 内联引号）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
LOG=_w2_t5_keeper_all.log
echo "[$(date '+%F %T')] ── 启动器被调用（setsid 方式）──" >> "$LOG"

if ! bash -n _t5_keeper_all.sh; then echo "  ❌ 语法错误" >> "$LOG"; exit 1; fi
echo "[$(date '+%F %T')]   语法 OK" >> "$LOG"

setsid bash _t5_keeper_all.sh < /dev/null >> "$LOG" 2>&1 &
sleep 12

SNAP=$(ps -eo pid,args --no-headers 2>/dev/null)
N=$(printf '%s\n' "$SNAP" | grep -c 'bash _t5_keeper_all.sh')
echo "[$(date '+%F %T')]   启动后 _t5_keeper_all 进程数 = $N" >> "$LOG"
echo
echo '── 核对（六个监控/守护，**排除自匹配**）──'
for p in _t5_armon.py _t5_blkmon.py _t5_milewatch.py _t5_finalwatch2.py; do
  printf '  %-22s %s\n' "$p" "$(printf '%s\n' "$SNAP" | grep -c "python .*$p")"
done
for p in _t5_keeper_all.sh _t5_mon_keeper.sh; do
  printf '  %-22s %s\n' "$p" "$(printf '%s\n' "$SNAP" | grep -c "bash $p")"
done
echo
echo '── 守护日志尾 ──'
tail -4 "$LOG" | sed 's/^/  /'
