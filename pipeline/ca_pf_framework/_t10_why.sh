#!/bin/bash
# _t10_why.sh --- 决定性证据：退出码 + core dump + 线程/信号信息
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== ★ ① 退出码文件（137=SIGKILL/OOM；139=SIGSEGV；0=正常）==="
if [ -f _w2_t10_exit.txt ]; then cat _w2_t10_exit.txt; else echo "  ⚠ 不存在！⇒ 说明 bash -c 包装层也被一起杀了（连 echo 都没跑）"; fi
echo
echo "=== ② core dump 设置与文件 ==="
ulimit -c
cat /proc/sys/kernel/core_pattern 2>/dev/null | sed 's/^/  core_pattern: /'
ls -la core* */*.core 2>/dev/null | head -5
ls -la /var/lib/systemd/coredump/ 2>/dev/null | tail -5
echo
echo "=== ③ 内核日志（本次启动以来）==="
dmesg 2>/dev/null | tail -40 | sed 's/^/  /'
echo "  ↑ 空 = 无权限读 dmesg"
echo
echo "=== ④ journalctl 里的 OOM/segfault（若有权限）==="
journalctl -k --since "30 min ago" 2>/dev/null | grep -iE 'oom|kill|segfault|traps|general protection' | tail -15 | sed 's/^/  /'
echo "  ↑ 空 = 无权限或确无记录"
echo
echo "=== ⑤ 本次 launch 脚本的日志（看它记到什么）==="
tail -12 _w2_t10_restart_thr.log 2>/dev/null | sed 's/^/  /'
echo
echo "=== ⑥ 引擎日志的字面末尾（含二进制/截断检查）==="
tail -c 1200 _w2_t5_short_t10N160.log 2>/dev/null | strings | tail -12 | sed 's/^/  /'
echo
echo "=== ⑦ 死亡前后的文件时间戳（秒级）==="
ls -la --time-style=+%H:%M:%S _exp/_bk_t5/dry_t10N160/ 2>/dev/null
ls -la --time-style=+%H:%M:%S _exp/_bk_t5/dry_t10N160/ckpt/ 2>/dev/null
