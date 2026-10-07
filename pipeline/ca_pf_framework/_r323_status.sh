#!/bin/bash
# _r323_status.sh —— 全部在跑/刚完成的作业一览。
cd "$(dirname "$0")" || exit 1
echo "=== 各臂日志的最新步号（只看还在更新的）==="
for f in _w2_r280_saSet2P0_run.log _w2_r280_saSet2F2P0_run.log \
         _w2_r240_run.log _w2_r322_near200_run.log _w2_r322_mid200_run.log \
         _w2_r322_far200_run.log; do
  if [ -f "$f" ]; then
    printf '  %-34s 步=%-5s mtime=%s\n' "$f" \
      "$(grep -o '^  \[ *[0-9]*\]' "$f" | tail -1 | tr -d ' []')" \
      "$(stat -c %y "$f" | cut -d. -f1)"
  else
    printf '  %-34s (不存在)\n' "$f"
  fi
done
echo
echo "=== 进程（tag + facet-proj）==="
for p in $(pgrep -f '_bk_exp[.]py' 2>/dev/null); do
  cl=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$cl" | grep -o 'tag [A-Za-z0-9_]*' | tail -1 | sed 's/tag //')
  fp=$(printf '%s' "$cl" | grep -o 'facet-proj [0-9]*' | tail -1 | sed 's/facet-proj //')
  st=$(printf '%s' "$cl" | grep -o 'steps [0-9]*' | tail -1 | sed 's/steps //')
  printf '  pid=%-7s tag=%-14s facet-proj=%-3s steps=%s\n' "$p" "${tag:-?}" "${fp:-?}" "${st:-?}"
done
echo "  （共 $(pgrep -fc '_bk_exp[.]py' || echo 0) 个）"
echo
echo "=== 负载 / 内存 ==="
cat /proc/loadavg | cut -d' ' -f1-3 | sed 's/^/  load: /'
free -m | head -2 | sed 's/^/  /'
echo
echo "=== 文档 ==="
wc -l R30_AUDIT_LEDGER.md AUDIT_SUMMARY_R76.md
for f in R30_AUDIT_LEDGER.md AUDIT_SUMMARY_R76.md; do
  n=$(tr -cd '\t' < "$f" | wc -c)
  echo "  $f 制表符=$n"
done
