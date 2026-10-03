#!/bin/bash
# _t5_n276read.sh --- 读 t5N276 的三路监控（去重）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ ① 生存与进度 ════'
printf '  引擎进程 = %s   末步 = %s   快照 = %s\n' \
  "$(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- '--tag t5N276')" \
  "$(tail -1 _exp/_bk_t5/dry_t5N276/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(ls -1 _exp/_bk_t5/dry_t5N276/snap_*.npz 2>/dev/null | wc -l)"
echo
echo '════ ② 几何量（长宽比/长厚比 —— 目标②）════'
grep -E '  t5N276 +step ' _w2_t5_ar_monitor.log 2>/dev/null | sort -u | tail -4 | sed 's/^/  /'
echo '  （若空 ⇒ 监控还没测到它，或尚无快照）'
echo
echo '════ ③④⑤ 块 / 块间影响 / 自协调（块监控 —— 目标③④⑤）════'
grep -E '① 生长|③ 成块|④ 块间|⑤ 自协调|块表行|块表列尚无' _w2_t5_n276_monitor.log 2>/dev/null \
  | sort -u | tail -8 | sed 's/^/  /'
echo
echo '════ 块监控进程 ════'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[p]ython _t5_blkmon' | cut -c1-58 | sed 's/^/  /'
free -m | sed -n 2p | sed 's/^/  内存: /'
