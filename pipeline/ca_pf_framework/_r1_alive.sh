#!/bin/bash
# _r1_alive.sh --- 判断在跑的算例**是否真的在推进**（不看步号，看文件 mtime 与 CPU 时间）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "现在：$(date +%H:%M:%S)"
echo
printf '%-16s %-10s %-12s %-10s %-12s %s\n' DIR CSV_mtime LOG_mtime 行数 末步 CPU时间
for d in "$@"; do
  C="_exp/$d/series.csv"; L="_exp/$d/log.txt"
  cm=$(date -r "$C" +%H:%M:%S 2>/dev/null || echo '—')
  lm=$(date -r "$L" +%H:%M:%S 2>/dev/null || echo '—')
  r=$(wc -l < "$C" 2>/dev/null || echo 0)
  s=$(grep -oE '\[ *[0-9]+\]' "$L" 2>/dev/null | tail -1 | tr -d '[] ')
  P=$(pgrep -f "_r1_exp.py --out _exp/$d" | head -1)
  if [ -n "$P" ]; then
    ct=$(ps -o time= -p "$P" | tr -d ' ')
    st=$(ps -o stat= -p "$P" | tr -d ' ')
  else
    ct='（无进程）'; st='—'
  fi
  printf '%-16s %-10s %-12s %-10s %-12s %s  [%s]\n' "$d" "$cm" "$lm" "$r" "${s:-—}" "$ct" "$st"
done
echo
echo "=== 最近 3 分钟内有写入的算例 ==="
find _exp -maxdepth 2 -name 'log.txt' -mmin -3 2>/dev/null | sed 's#_exp/##;s#/log.txt##' | sort | head
