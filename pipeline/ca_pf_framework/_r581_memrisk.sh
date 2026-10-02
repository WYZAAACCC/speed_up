#!/bin/bash
# _r581_memrisk.sh --- ★★★★★ **内存风险自查**：两条 N=160 臂同时跑，可用内存只剩 ~1 GB
#   P23：加车道的判据是**内存**，不是空闲核。本脚本把"谁占了多少、还剩多少、闸门在不在"一次打全。
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── 内存 ──'
free -m | sed 's/^/  /'
awk '{printf "  loadavg %s %s %s\n", $1, $2, $3}' /proc/loadavg
echo
echo '── 每条 _bk_exp.py 的 tag / RSS / 已跑步数 ──'
for p in $(pgrep -f "_bk_exp.py" 2>/dev/null); do
  cmd=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null)
  tag=$(echo "$cmd" | grep -oE "\-\-tag [A-Za-z0-9_]+" | head -1 | awk '{print $2}')
  out=$(echo "$cmd" | grep -oE "\-\-out [^ ]+" | head -1 | awk '{print $2}')
  r=$(awk '/VmRSS/{print $2}' /proc/$p/status 2>/dev/null)
  # 末步：从对应 series.csv 读（若能定位）
  step="?"
  if [ -n "$out" ] && [ -n "$tag" ]; then
    f="${out}/dry_${tag}/series.csv"
    [ -f "$f" ] && step=$(tail -1 "$f" | cut -d, -f1)
  fi
  printf '  pid=%-7s tag=%-12s RSS=%6d MB  末step=%-6s out=%s\n' \
     "$p" "${tag:-?}" "$((r/1024))" "$step" "${out:-?}"
done
echo
echo '── 内存看门狗（memguard / softguard）是否在跑 ──'
for s in _r581_memguard.sh _r581_softguard.sh; do
  n=$(ps -eo args --no-headers 2>/dev/null | grep -c -- "$s")
  printf '  %-22s 进程=%d\n' "$s" "$((n-1))"
done
echo
echo '── 各队列日志尾（看它们在等什么）──'
for f in _w2_r581_mqueue.log _w2_r581_mqueue2.log _w2_r581_mqueue3.log \
         _w2_r581_mqueue4.log _w2_r581_mn64c.log _w2_r581_mn64d.log \
         _w2_r581_mn64e.log _w2_r581_mn64f.log _w2_r581_mn64g.log; do
  [ -f "$f" ] && printf '  %-26s %s\n' "$f" "$(tail -1 "$f" | cut -c1-70)"
done
