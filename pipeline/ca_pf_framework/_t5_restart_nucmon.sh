#!/bin/bash
# _t5_restart_nucmon.sh --- 重启形核账目监控（分母已修为 B·n）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
$PY -m py_compile _t5_nucmon.py || { echo '  ❌ 语法错误'; exit 1; }
echo '  ✅ 语法 OK'

for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[p]ython _t5_nucmon' | awk '{print $1}'); do
  kill -TERM "$P" 2>/dev/null && echo "  已停旧 nucmon pid=$P"
done
sleep 3
setsid $PY _t5_nucmon.py t5N276F 180 400 < /dev/null >> _w2_t5_nucmon_t5N276F.log 2>&1 &
sleep 25
echo "  nucmon 进程数 = $(ps -eo args --no-headers 2>/dev/null | grep -c 'python _t5_nucmon.py')"
echo
echo '── 修后首轮（分母应为全盒目标 = 69）──'
tail -8 _w2_t5_nucmon_t5N276F.log | sed 's/^/  /'
