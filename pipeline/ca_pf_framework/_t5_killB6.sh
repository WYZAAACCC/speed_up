#!/bin/bash
# _t5_killB6.sh --- 直接按 PID 停掉 t5B6（脚本内的进程匹配要写成文件，避免引号问题）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '── 当前所有引擎进程（pid + tag）──'
ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -v 'grep' \
  | sed 's/.*--tag \([A-Za-z0-9_]*\).*/  pid=\1/' >/dev/null
ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -v 'grep' | while read -r PID REST; do
  TAG=$(printf '%s' "$REST" | sed -n 's/.*--tag \([A-Za-z0-9_]*\).*/\1/p')
  echo "  pid=$PID  tag=${TAG:-?}"
done
echo
echo '── 杀掉 tag=t5B6 的 ──'
ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -v 'grep' | while read -r PID REST; do
  case "$REST" in
    *"--tag t5B6"*) echo "  KILL pid=$PID"; kill -9 "$PID" 2>/dev/null ;;
  esac
done
sleep 3
echo
echo '── 停后剩余引擎进程 ──'
N=$(ps -eo args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -v 'grep' | wc -l)
echo "  引擎进程数 = $N"
ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -v 'grep' | while read -r PID REST; do
  TAG=$(printf '%s' "$REST" | sed -n 's/.*--tag \([A-Za-z0-9_]*\).*/\1/p')
  echo "  pid=$PID  tag=${TAG:-?}"
done
echo
echo '── 数据目录改名保留 ──'
D=_exp/_bk_t5/dry_t5B6
if [ -d "$D" ]; then
  mv "$D" "${D}_superseded_$(date +%m%d_%H%M)" && echo "  已改名（未删）"
else
  echo "  （$D 不存在或已改名）"
fi
ls -d _exp/_bk_t5/dry_t5B6* 2>/dev/null | sed 's/^/  /'
free -m | sed -n 2p | sed 's/^/  /'
