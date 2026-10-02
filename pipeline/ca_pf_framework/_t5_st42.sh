#!/bin/bash
# _t5_st42.sh --- 第 42 轮：修正臂 t5H3 的启动核查
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo '── fix4 编排日志（末 20 行）──'
tail -20 _w2_t5_fix4.log 2>/dev/null | cut -c1-132 | sed 's/^/  /'
echo
echo '── 进程 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "  pid=%s 已跑=%s\n", $1, $2}'
N=$(ps -eo args --no-headers 2>/dev/null | grep -c '[_]bk_exp.py')
echo "  ⇒ 进程数 = $N"
echo
echo '── 新臂 t5H3 的引擎横幅（约束1/2 的关键行）──'
grep -E 'nv=|总根数|必须至少|几何上界|导出板条数|nvar' _w2_t5_short_t5H3.log 2>/dev/null \
  | head -6 | cut -c1-132 | sed 's/^/  /'
echo
echo '── 臂日志体积 ──'
for f in _w2_t5_short_t5H3.log _w2_t5_fix4_A.log; do
  printf '  %-28s %s 字节\n' "$f" "$(stat -c%s "$f" 2>/dev/null || echo 0)"
done
free -m | sed -n 2p | sed 's/^/  /'
