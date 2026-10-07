#!/bin/bash
# _r429_state.sh —— 轮末状态快照（只读）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== 双臂进程 ==="
ps -eo pid=,etime=,rss=,args= | grep -F -- '--tag ab' | grep -v grep \
  | awk '{printf "  pid=%s etime=%s rss=%.2fGB\n", $1, $2, $3/1048576}'
echo
echo "=== 文档行数 ==="
wc -l R30_AUDIT_LEDGER.md AUDIT_SUMMARY_R76.md
echo
echo "=== 数据落盘 ==="
du -sh _exp/_bk_mb/dry_abA _exp/_bk_mb/dry_abB 2>/dev/null
echo
echo "=== 双臂最新读数 ==="
bash _r427_watch.sh 2>&1 | grep -E '臂 ab|形核事件|CSV 行数|step=|Traceback|进程'
