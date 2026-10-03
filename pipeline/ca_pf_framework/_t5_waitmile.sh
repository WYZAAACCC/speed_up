#!/bin/bash
# _t5_waitmile.sh --- 阻塞等到**任一里程碑触发**（或超时），然后打印现场
# 用法：bash _t5_waitmile.sh <最多等秒数>
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
LIM=${1:-1800}
L=_w2_t5_n276_milestones.log
# ★ s241 修（**本项目 P48 纪律**）：`grep -c` 可能返回**多行**（如 "0\n0"）⇒ `[ -gt ]` 会报
#   `integer expected` 并**静默失效**。⇒ 一律用 `awk … | wc -l` 取计数。
cnt() { awk '/★M[0-9]/{n++} END{print n+0}' "$L" 2>/dev/null; }
BASE=$(cnt)
echo "  起等：已有 ★M 事件 = $BASE 条；最多等 ${LIM} s"
T=0
while [ "$T" -lt "$LIM" ]; do
  NOW=$(cnt)
  if [ "$NOW" -gt "$BASE" ]; then
    echo "  ★ 有新里程碑！（$BASE → $NOW）"
    break
  fi
  # 算例若已死，也要退出
  ALIVE=$(ps -eo args --no-headers 2>/dev/null | awk '/--tag t5N276/{n++} END{print n+0}')
  if [ "$ALIVE" -eq 0 ]; then
    echo "  ⚠ 算例进程消失 ⇒ 退出等待（查日志）"
    break
  fi
  sleep 30; T=$((T + 30))
done
echo "NOW = $(date '+%F %T')   等待了 ${T} s"
echo '════ ★ 里程碑（全部）════'
grep -E '★M[0-9]' "$L" 2>/dev/null | tail -6 | sed 's/^/  /' || echo '  （尚无）'
echo '════ 心跳 / 最新状态 ════'
grep -E '心跳' "$L" 2>/dev/null | tail -1 | sed 's/^/  /'
echo '════ 几何量最新 ════'
grep -E '  t5N276 +step ' _w2_t5_ar_monitor.log 2>/dev/null | sort -u | tail -2 | sed 's/^/  /'
echo '════ 进度 ════'
printf '  末步 = %s   块表最新 step = %s\n' \
  "$(tail -1 _exp/_bk_t5/dry_t5N276/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(awk -F, 'NR==1{for(i=1;i<=NF;i++) if($i=="nblk_sig") c=i; next} $c!=""{s=$1} END{print s}' _exp/_bk_t5/dry_t5N276/series.csv 2>/dev/null)"
