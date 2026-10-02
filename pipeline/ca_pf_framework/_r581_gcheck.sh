#!/bin/bash
# _r581_gcheck.sh --- 臂 G（`B=150`，nv=240）为何停在 step 0（P29：日志尾 + Traceback + 产物行数）
cd "$(dirname "$0")" || exit 1
for T in G F; do
  echo "################ 臂 $T ################"
  for f in _w2_r581_mn64_${T}.log _w2_r581_mn64${T}.log; do
    if [ -f "$f" ]; then
      echo "--- $f（$(stat -c%s "$f") 字节，mtime $(date -r "$f" '+%T')）---"
      echo "  Traceback 行数 = $(grep -c '^Traceback' "$f")"
      echo "  Error/error 行数 = $(grep -ciE 'error|exception|traceback' "$f")"
      echo "  ── 末 6 行 ──"
      tail -6 "$f" | cut -c1-100 | sed 's/^/    /'
      echo "  ── 头 3 行 ──"
      head -3 "$f" | cut -c1-100 | sed 's/^/    /'
    fi
  done
  d=_exp/_bk_mn64/dry_${T}
  echo "--- 产物目录 $d ---"
  if [ -d "$d" ]; then
    ls -la "$d" | sed 's/^/    /'
  else
    echo "    （不存在）"
  fi
  echo
done
echo "################ 所有 worker ################"
for p in $(pgrep -f "_bk_exp.py" 2>/dev/null); do
  cmd=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null)
  tag=$(echo "$cmd" | grep -oE "\-\-tag [A-Za-z0-9_]+" | head -1 | awk '{print $2}')
  r=$(awk '/VmRSS/{print $2}' /proc/$p/status 2>/dev/null)
  printf '  pid=%-7s tag=%-10s RSS=%5d MB\n' "$p" "${tag:-?}" "$((r/1024))"
done
echo
echo "################ 栈/状态（若 G 还在）################"
for p in $(pgrep -f "\-\-tag G" 2>/dev/null); do
  echo "  pid=$p 状态=$(awk '/^State/{print $2,$3}' /proc/$p/status 2>/dev/null)"
  echo "  wchan=$(cat /proc/$p/wchan 2>/dev/null)"
  echo "  线程数=$(awk '/^Threads/{print $2}' /proc/$p/status 2>/dev/null)"
done
