#!/bin/bash
# _t5_prog.sh --- 大实验（t5N276）现在跑到多少步 / 是否已结束
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ t5N276（大实验）════'
D=_exp/_bk_t5/dry_t5N276
printf '  series.csv 末行 step = **%s**   最后写入 = %s\n' \
  "$(tail -1 $D/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(stat -c%y $D/series.csv 2>/dev/null | cut -d. -f1)"
printf '  快照 = %s 张（最大 step = %s）   ckpt = %s 个\n' \
  "$(ls -1 $D/snap_*.npz 2>/dev/null | wc -l)" \
  "$(ls -1 $D/snap_*.npz 2>/dev/null | sed 's/.*snap_//;s/\.npz//' | sort -n | tail -1)" \
  "$(ls -1 $D/ckpt/*.npz 2>/dev/null | wc -l)"
printf '  进程 = %s 个\n' "$(ps -eo args --no-headers 2>/dev/null | awk '/--tag t5N276/{n++} END{print n+0}')"
echo
echo '  ── 结束原因（从引擎日志）──'
grep -E '准静态钟|提前结束|走到 step|exit=' _w2_t5_short_t5N276.log 2>/dev/null | tail -4 | cut -c1-150 | sed 's/^/     /'
echo
echo '════ 对照：其它臂 ════'
for t in t5NR t5V2 t5AB_A t5AD_700 t5AD_1000 t5AM_ell t5AM_combo t5H3; do
  D=_exp/_bk_t5/dry_$t
  [ -d "$D" ] || continue
  P=$(ps -eo args --no-headers 2>/dev/null | awk -v q="--tag $t" 'index($0,q){n++} END{print n+0}')
  printf '  %-11s 末步=%-6s 最后写=%-20s 进程=%s\n' "$t" \
    "$(tail -1 $D/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(stat -c%y $D/series.csv 2>/dev/null | cut -d. -f1)" "$P"
done
echo
echo '════ 监控（还在跑）════'
ps -eo args --no-headers 2>/dev/null | grep -cE '[p]ython _t5_(armon|blkmon|milewatch|arwatch|ardist_ts|freshwatch)' | sed 's/^/  监控进程数 = /'
free -m | sed -n 2p | sed 's/^/  /'
