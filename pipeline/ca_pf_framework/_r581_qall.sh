#!/bin/bash
# _r581_qall.sh —— 一屏看全**四条 N=160 队列 + 四条 N=64 臂队列**
#   ⚠ 本脚本的存在理由：嵌套 $(...) 在 PowerShell→WSL 里会被拆坏（R61/R87 各踩一次）
#   ⇒ 一律写进 .sh 再跑。
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── N=160 队列 ──'
for f in _w2_r581_mqueue.log _w2_r581_mqueue2.log _w2_r581_mqueue3.log _w2_r581_mqueue4.log; do
  if [ -f "$f" ]; then
    printf '  %-26s %s\n' "$f" "$(tail -1 "$f" | cut -c1-88)"
  else
    printf '  %-26s （无日志）\n' "$f"
  fi
done
echo
echo '── N=64 队列 ──'
for f in _w2_r581_mn64.log _w2_r581_mn64b.log _w2_r581_mn64c.log _w2_r581_mn64d.log; do
  if [ -f "$f" ]; then
    printf '  %-26s %s\n' "$f" "$(tail -1 "$f" | cut -c1-88)"
  else
    printf '  %-26s （无日志）\n' "$f"
  fi
done
echo
echo '── 队列进程（按脚本名）──'
for s in _r581_mqueue.sh _r581_mqueue2.sh _r581_mqueue3.sh _r581_mqueue4.sh \
         _r581_mn64.sh _r581_mn64b.sh _r581_mn64c.sh _r581_mn64d.sh; do
  n=$(ps -eo args --no-headers 2>/dev/null | grep -c -- "$s")
  n=$((n - 1))          # 减掉 grep 自己
  [ "$n" -lt 0 ] && n=0
  printf '  %-24s 进程=%s\n' "$s" "$n"
done
echo
echo '── 在跑的 worker ──'
ps -eo pid,rss,args --no-headers 2>/dev/null | grep '_bk_exp.py' | grep -v grep \
  | awk '{printf "  pid=%-7s RSS=%.2f GB\n", $1, $2/1048576}'
echo
echo '── 资源 ──'
free -m | sed -n 2p | sed 's/^/  /'
awk '{printf "  loadavg %s %s %s\n", $1, $2, $3}' /proc/loadavg
