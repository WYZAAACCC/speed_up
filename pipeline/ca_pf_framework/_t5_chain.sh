#!/bin/bash
# _t5_chain.sh --- 监控链条存活 + t5N276 进度（一条命令，避免 PowerShell 引号问题）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ 监控链条（四条）════'
printf '  %-20s %s\n' '_t5_armon (几何)'  "$(ps -eo args --no-headers 2>/dev/null | grep -c '[p]ython _t5_armon')"
printf '  %-20s %s\n' '_t5_blkmon (块)'   "$(ps -eo args --no-headers 2>/dev/null | grep -c '[p]ython _t5_blkmon')"
printf '  %-20s %s\n' '_t5_mon_keeper(守护)' "$(ps -eo args --no-headers 2>/dev/null | grep -c '[_]t5_mon_keeper')"
printf '  %-20s %s\n' '_t5_finalwatch2(终态)' "$(ps -eo args --no-headers 2>/dev/null | grep -c '[p]ython _t5_finalwatch2')"
echo
echo '════ t5N276 ════'
printf '  末步 = %s   快照 = %s   引擎进程 = %s\n' \
  "$(tail -1 _exp/_bk_t5/dry_t5N276/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(ls -1 _exp/_bk_t5/dry_t5N276/snap_*.npz 2>/dev/null | wc -l)" \
  "$(ps -eo args --no-headers 2>/dev/null | grep -c -- '--tag t5N276')"
printf '  ckpt = %s 个（断点续跑就绪）\n' \
  "$(ls -1 _exp/_bk_t5/dry_t5N276/ckpt/*.npz 2>/dev/null | wc -l)"
echo
echo '════ 全部引擎 ════'
ps -eo args --no-headers 2>/dev/null | grep -c '[_]bk_exp.py' | sed 's/^/  进程数 = /'
free -m | sed -n 2p | sed 's/^/  /'
