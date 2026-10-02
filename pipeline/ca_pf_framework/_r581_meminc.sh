#!/bin/bash
# _r581_meminc.sh --- 记录**内存事故**：两条 N=160 m=12 臂同时跑 ⇒ 交换 5.7 GB、可用 771 MB
#   ⚠ 写成脚本再跑（嵌套引号在 PowerShell→WSL 里会被拆坏）
cd "$(dirname "$0")" || exit 1
OUT=_w2_r581_meminc.txt
{
  echo "=== 时间：$(date '+%F %T') ==="
  echo
  echo '## ① 内存现状'
  free -m | sed 's/^/  /'
  awk '{printf "  loadavg %s %s %s\n", $1, $2, $3}' /proc/loadavg
  echo
  echo '## ② 各 worker 的 RSS'
  for p in $(pgrep -f "_bk_exp.py" 2>/dev/null); do
    cmd=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null)
    tag=$(echo "$cmd" | grep -oE "\-\-tag [A-Za-z0-9_]+" | head -1 | awk '{print $2}')
    out=$(echo "$cmd" | grep -oE "\-\-out [^ ]+" | head -1 | awk '{print $2}')
    r=$(awk '/VmRSS/{print $2}' /proc/$p/status 2>/dev/null)
    f="${out}/dry_${tag}/series.csv"
    step=$(tail -1 "$f" 2>/dev/null | cut -d, -f1)
    mt=$(date -r "$f" '+%T' 2>/dev/null)
    printf '  pid=%-7s tag=%-10s RSS=%6d MB  末step=%-5s (CSV mtime %s)\n' \
      "$p" "${tag:-?}" "$((r/1024))" "${step:-?}" "${mt:-?}"
  done
  echo
  echo '## ③ 看门狗（在不在、日志说了什么）'
  for s in _r581_memguard.sh _r581_softguard.sh; do
    n=$(ps -eo args --no-headers 2>/dev/null | grep -c -- "$s")
    printf '  %-22s 进程=%d\n' "$s" "$((n-1))"
  done
  for f in _w2_r581_memguard.log _w2_r581_softguard.log; do
    if [ -f "$f" ]; then
      echo "  --- $f（末 6 行）---"
      tail -6 "$f" | sed 's/^/    /'
    else
      echo "  $f：（无）"
    fi
  done
  echo
  echo '## ④ 两臂日志尾（判它们是否还在推进）'
  for t in p2_m12 p2_m12b; do
    f=_w2_r581_p2_${t}.log
    echo "  --- $t（mtime $(date -r "$f" '+%T' 2>/dev/null)）---"
    tail -3 "$f" 2>/dev/null | cut -c1-96 | sed 's/^/    /'
  done
  echo
  echo '## ⑤ 各队列的内存闸门（它们会不会再往上加）'
  for f in _w2_r581_mqueue.log _w2_r581_mqueue2.log _w2_r581_mqueue3.log _w2_r581_mqueue4.log; do
    [ -f "$f" ] && printf '  %-26s %s\n' "$f" "$(tail -1 "$f" | cut -c1-66)"
  done
} > "$OUT" 2>&1
cat "$OUT"
