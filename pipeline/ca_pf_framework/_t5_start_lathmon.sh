#!/bin/bash
# _t5_start_lathmon.sh --- 启动板条状态监控（并报"活跃场数"与 nslab_n）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
$PY -m py_compile _t5_lathmon.py || { echo '  ❌ 语法错误'; exit 1; }
echo '  ✅ 语法 OK'
setsid $PY _t5_lathmon.py t5N276F,t5N276 600 120 < /dev/null >> _w2_t5_lathmon.log 2>&1 &
sleep 60
echo "  lathmon 进程数 = $(ps -eo args --no-headers 2>/dev/null | grep -c 'python _t5_lathmon.py')"
echo
echo '── 首轮（应看到两版的"活跃场数"对照）──'
grep -E '\[t5N276F\]|\[t5N276\]' _w2_t5_lathmon.log 2>/dev/null | tail -4 | sed 's/^/  /'
