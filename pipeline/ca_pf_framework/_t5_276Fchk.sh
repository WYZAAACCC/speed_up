#!/bin/bash
# _t5_276Fchk.sh --- t5N276F 进度 + 形核事件（含模式）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
D=_exp/_bk_t5/dry_t5N276F/series.csv
echo "NOW = $(date '+%F %T')"
printf '  t5N276F 末步 = %s   nslab_n = %s\n' \
  "$(tail -1 $D 2>/dev/null | cut -d, -f1)" "$(tail -1 $D 2>/dev/null | cut -d, -f9)"
printf '  引擎进程 = %s\n' "$(ps -eo args --no-headers 2>/dev/null | grep -c 'bk_exp.py.*--tag t5N276F')"
echo
echo '════ 已出现的形核事件（step / 场 / 模式）════'
awk '/@ step/ && /模式/ {
  match($0, /@ step [0-9]+/); s=substr($0, RSTART+7, RLENGTH-7);
  match($0, /场 [0-9]+/); f=substr($0, RSTART+2, RLENGTH-2);
  match($0, /模式 \*\*[a-z]+\*\*/); m=substr($0, RSTART+8, RLENGTH-10);
  printf "  step %-6s 场 %-4s 模式 %s\n", s, f, m
}' _w2_t5_short_t5N276F.log 2>/dev/null | tail -12
echo
echo '════ 是否已有 stack ════'
awk '/模式 \*\*stack\*\*/{n++} END{print "  stack 事件数 = " n+0}' _w2_t5_short_t5N276F.log 2>/dev/null
echo
echo '════ 对照：t5N276（修复前）在 step 100/200/300 的 nslab_n ════'
awk -F, 'NR>1 && ($1==100||$1==200||$1==300){printf "  step %s  nslab_n %s\n", $1, $9}' \
  _exp/_bk_t5/dry_t5N276/series.csv 2>/dev/null
