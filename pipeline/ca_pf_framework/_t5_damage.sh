#!/bin/bash
# _t5_damage.sh --- ★★★★★ 事故评估：所有引擎消失（**先查损失，别猜原因**）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')  uptime: $(uptime -p 2>/dev/null)  (since $(uptime -s 2>/dev/null))"
echo
echo '════ ① 还活着的进程（python / bash 监控）════'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E '[p]ython|[b]ash _t5' | cut -c1-100 | head -20 | sed 's/^/  /'
echo "  （python 进程数 = $(ps -eo args --no-headers 2>/dev/null | awk '/python/{n++} END{print n+0}')）"
echo
echo '════ ② 各算例的**数据存活性**（末步 + 最后写入时间 + ckpt）════'
for t in t5N276 t5NR t5V2 t5AB_A t5AD_700 t5H3; do
  D=_exp/_bk_t5/dry_$t
  [ -d "$D" ] || continue
  S=$D/series.csv
  printf '  %-9s 末步=%-6s 最后写=%s  快照=%s  ckpt=%s\n' "$t" \
    "$(tail -1 "$S" 2>/dev/null | cut -d, -f1)" \
    "$(stat -c%y "$S" 2>/dev/null | cut -d. -f1)" \
    "$(ls -1 $D/snap_*.npz 2>/dev/null | wc -l)" \
    "$(ls -1 $D/ckpt/*.npz 2>/dev/null | wc -l)"
done
echo
echo '════ ③ 引擎日志尾部（看是**正常退出**还是**被杀**）════'
for t in t5N276 t5NR; do
  L=_w2_t5_short_$t.log
  [ -f "$L" ] || continue
  echo "  ── $t（$L, $(stat -c%s "$L") 字节）──"
  tail -6 "$L" | cut -c1-140 | sed 's/^/     /'
  printf '     Traceback=%s  SIGKILL=%s  exit=%s\n' \
    "$(awk '/Traceback/{n++} END{print n+0}' "$L")" \
    "$(awk '/SIGKILL|Killed/{n++} END{print n+0}' "$L")" \
    "$(awk '/exit=/{n++} END{print n+0}' "$L")"
done
echo
echo '════ ④ 监控日志尾部 ════'
for L in _w2_t5_n276_monitor.log _w2_t5_fresh.log _w2_t5_ar_decay.log _w2_t5_ardist_ts.log; do
  [ -f "$L" ] && printf '  %-32s 最后写 %s\n' "$L" "$(stat -c%y "$L" | cut -d. -f1)"
done
