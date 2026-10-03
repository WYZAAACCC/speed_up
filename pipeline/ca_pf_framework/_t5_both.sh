#!/bin/bash
# _t5_both.sh --- 两臂健康与进度（只读）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ 进程 ════'
ps -eo pid,etime,rss,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "  pid=%s 已跑=%s RSS=%.2f GB\n", $1, $2, $3/1048576}'
echo
echo '════ 两臂进度 ════'
for t in t5H3 t5V2; do
  printf '  ── %s ──\n' "$t"
  printf '     series 行数/末步: %s / %s\n' \
    "$(($(wc -l < _exp/_bk_t5/dry_$t/series.csv 2>/dev/null || echo 1) - 1))" \
    "$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)"
  printf '     形核公告=%s 被拒=%s   模式: %s\n' \
    "$(grep -c 'athermal 形核' _w2_t5_short_$t.log 2>/dev/null)" \
    "$(grep -c '被引擎拒' _w2_t5_short_$t.log 2>/dev/null)" \
    "$(grep -oE '模式 \*\*[a-z]+\*\*' _w2_t5_short_$t.log 2>/dev/null | sort | uniq -c | tr '\n' ' ')"
  printf '     检查点: %s\n' "$(ls -1t _exp/_bk_t5/dry_$t/ckpt/*.npz 2>/dev/null | head -1 | xargs -r stat -c '%n %s字节 %y' 2>/dev/null | cut -c1-95)"
done
echo
free -m | sed -n 2p | sed 's/^/  内存: /'
