#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== mem_limit / 看门狗 的实现（_t5_short.py 与 _bk_exp.py）==="
grep -n 'mem_limit\|mem-limit\|RSS\|VmRSS\|available\|MemAvailable\|psutil\|kill' _t5_short.py 2>/dev/null | head -20 | cut -c1-175
echo
echo "=== _bk_exp.py 里的同类 ==="
grep -n 'mem_limit\|MemAvailable\|available\|psutil\|os.kill\|SIGKILL\|SIGTERM' _bk_exp.py 2>/dev/null | head -20 | cut -c1-175
echo
echo "=== ★ 系统上还有哪些会杀进程的看门狗脚本 ==="
grep -ln 'kill -9' _t5_*.sh _r58*_*.sh 2>/dev/null | head -20
echo
echo "=== ★ 当前是否还有看门狗在跑 ==="
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E '\.sh' | grep -v grep | cut -c1-150
echo
echo "=== ★ launch 脚本的杀进程段（回看是否会误杀）==="
sed -n '/抢内存/,/sleep 6/p' _t10_launch.sh | cut -c1-160
