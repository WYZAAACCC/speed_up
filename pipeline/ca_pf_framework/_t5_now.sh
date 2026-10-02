#!/bin/bash
# _t5_now.sh --- 回答"现在仿真在运行吗？"
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '════ ① 进程 ════'
ps -eo pid,etime,rss,args --no-headers 2>/dev/null | grep '_bk_exp.py' | grep -v grep \
  | awk '{printf "  pid=%s  已跑=%s  RSS=%.1f GB\n", $1, $2, $3/1048576}'
N=$(ps -eo args --no-headers 2>/dev/null | grep -c '[_]bk_exp.py')
echo "  ⇒ _bk_exp.py 进程数 = $N"
echo
echo '════ ② 步进读数（引擎每 --every 20 步打一行）════'
for t in t5L62 t5L0; do
  f="_w2_t5_short_$t.log"
  last=$(grep -oE '\[ *[0-9]+\] Vt=[0-9.]+' "$f" 2>/dev/null | tail -1)
  sps=$(grep -oE '\| *[0-9.]+s/步' "$f" 2>/dev/null | tail -1)
  printf '  %-6s 末次读数 = %-22s  %s\n' "$t" "${last:-（还没到第一个打印点）}" "$sps"
  printf '         日志 %s 字节，最后修改 %s\n' \
    "$(stat -c%s "$f" 2>/dev/null || echo 0)" \
    "$(stat -c%y "$f" 2>/dev/null | cut -c1-19)"
done
echo
echo '════ ③ 产物增长 ════'
for t in t5L62 t5L0; do
  d=_exp/_bk_t5/dry_$t
  printf '  %-6s series=%-4s 行  ckpt=%-2s 个  snap=%-3s 个  目录 %s\n' "$t" \
    "$(wc -l < "$d/series.csv" 2>/dev/null || echo 0)" \
    "$(ls -1 "$d/ckpt" 2>/dev/null | wc -l)" \
    "$(ls -1 "$d"/snap_*.npz 2>/dev/null | wc -l)" \
    "$(du -sh "$d" 2>/dev/null | cut -f1)"
done
echo
echo '════ ④ 机器 ════'
free -m | sed -n '2p' | sed 's/^/  /'
printf '  负载：%s\n' "$(cut -d' ' -f1-3 /proc/loadavg)"
echo
echo '════ ⑤ 编排器作业 ════'
tail -3 _w2_t5_long.log 2>/dev/null | sed 's/^/  /'
