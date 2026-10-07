#!/bin/bash
# _r265_alive.sh —— 判断在跑的臂**是否真的在推进**（不靠 series.csv 行数，它 20 步才写一行）。
#
# 判据：日志文件里 `[   N]` 的**最新步号** + 日志 mtime（应持续更新）。
cd "$(dirname "$0")" || exit 1
echo "=== 各臂日志的最新步号与 mtime ==="
for f in _w2_r253_L0.log _w2_r253_P0.log _w2_r225_p45L.log _w2_r225_p45P.log \
         _w2_r210_saOddGDT_run.log _w2_r240_run.log; do
  if [ -f "$f" ]; then
    last=$(grep -o '^  \[ *[0-9]*\]' "$f" | tail -1 | tr -d ' []')
    mt=$(stat -c %y "$f" | cut -d. -f1)
    sz=$(stat -c %s "$f")
    printf '  %-30s 最新步=%-6s mtime=%s size=%s\n' "$f" "${last:-?}" "$mt" "$sz"
  else
    printf '  %-30s (不存在)\n' "$f"
  fi
done
echo
echo "=== 当前时间 ==="
date '+%F %T'
echo
echo "=== 进程 CPU 时间（采样两次，间隔 20 s，看是否在涨）==="
snap() { ps -eo pid,etime,times,pcpu,args --no-headers 2>/dev/null \
         | grep '_bk_exp[.]py' | grep -v grep \
         | sed 's/--arm dry.*--tag/.../' \
         | awk '{print $1, $2, $3, $4, $(NF-1)}' | sort; }
echo "--- T0 ---"; snap
sleep 20
echo "--- T1（20 s 后）---"; snap
