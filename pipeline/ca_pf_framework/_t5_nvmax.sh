#!/bin/bash
# _t5_nvmax.sh --- 回答「当前电脑最大能承担多少 nv」：先找已实测的数据点与拟合工具
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== ① 当前内存实况 ==="
free -m | sed -n '1,3p'
echo
echo "=== ② 引擎自己的内存模型/看门狗（它怎么估算）==="
grep -n 'mem_limit\|mem-limit\|_mem_est\|RSS\|rss_mb\|nv_max' _bk_exp.py 2>/dev/null | head -18 | cut -c1-170
echo
echo "=== ③ 现成的内存定律工具 ==="
ls -la _r579_report.py _r579_mem.py _r581_mem*.sh _r578_rsstrace.sh 2>/dev/null | awk '{print "  "$5" "$9}'
echo
echo "=== ④ 日志里已有的实测内存数据点 ==="
grep -ah '峰值\|peak\|RSS\|内存' _w2_r579*.log _w2_r581*alloc*.log 2>/dev/null | head -20 | cut -c1-170
