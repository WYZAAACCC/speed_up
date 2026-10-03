#!/bin/bash
# _t5_start_nucmon.sh --- 启动形核账目监控（覆盖新增三项目标）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
$PY -m py_compile _t5_nucmon.py || { echo '  ❌ 语法错误'; exit 1; }
echo '  ✅ 语法 OK'
setsid $PY _t5_nucmon.py t5N276F 180 400 < /dev/null >> _w2_t5_nucmon_t5N276F.log 2>&1 &
sleep 25
SNAP=$(ps -eo pid,args --no-headers 2>/dev/null)
echo "  nucmon 进程数 = $(printf '%s\n' "$SNAP" | grep -c 'python _t5_nucmon.py')"
echo
echo '── 首轮输出 ──'
tail -12 _w2_t5_nucmon_t5N276F.log | sed 's/^/  /'
