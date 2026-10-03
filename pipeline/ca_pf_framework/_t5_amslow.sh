#!/bin/bash
# _t5_amslow.sh --- ★★★ 两臂是"还在早期"还是"病态慢/卡住"
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
for t in t5AM_ell t5AM_combo; do
  echo "════ $t ════"
  L=_w2_t5_short_$t.log
  echo -n '  日志最后修改: '; stat -c '%y' "$L" 2>/dev/null
  echo -n '  日志大小: '; stat -c '%s' "$L" 2>/dev/null
  echo '  ── 日志里**最后一行的 step 号**（引擎每步或每 N 步打一行）──'
  grep -oE '\[ *[0-9]+\]' "$L" 2>/dev/null | tail -3 | sed 's/^/     /'
  echo '  ── 末尾 2 行原文 ──'
  tail -2 "$L" 2>/dev/null | cut -c1-140 | sed 's/^/     /'
  echo -n '  进程 CPU 时间/占用: '
  P=$(ps -eo pid,args --no-headers | grep "dry_$t" | awk '{print $1}' | head -1)
  [ -n "$P" ] && ps -o pid,etime,time,pcpu,rss --no-headers -p "$P" | sed 's/^/     /' || echo '（无进程）'
  echo
done
echo '════ 对照：一个正常臂（t5AD_700）的日志增长速率 ════'
stat -c '  %n 大小=%s 最后写=%y' _w2_t5_short_t5AD_700.log 2>/dev/null || \
stat -c '  %n 大小=%s 最后写=%y' _w2_t5_ad_t5AD_700.log 2>/dev/null
