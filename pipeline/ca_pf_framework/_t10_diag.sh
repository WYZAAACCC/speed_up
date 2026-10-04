#!/bin/bash
# _t10_diag.sh --- 算例是否还活着？死了的话死在什么上？
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== NOW $(date '+%m-%d %H:%M:%S') ==="
echo
echo "=== ① 进程（引擎/包装/盯守/守望）==="
ps -eo pid,etime,time,pcpu,pmem,rss,args --no-headers 2>/dev/null \
  | grep -E 'bk_exp|_t5_short|_t10_mon|_t10_wait' | grep -v grep | cut -c1-155
echo "  （空 = 全没了）"
echo
echo "=== ② 内存实况 ==="
free -m
echo
echo "=== ③ 引擎日志：末 12 行 ==="
tail -12 _w2_t5_short_t10N160.log 2>/dev/null | cut -c1-185
echo
echo "=== ④ 日志里的致命信息 ==="
grep -aiE 'kill|signal|abort|traceback|error|memoryerror|被.*闸|超时|OOM' \
  _w2_t5_short_t10N160.log 2>/dev/null | tail -10 | cut -c1-185
echo
echo "=== ⑤ 盯守日志（RSS 轨迹）末 12 行 ==="
tail -12 _w2_t10_mon.log 2>/dev/null
echo
echo "=== ⑥ 守望日志末 6 行 ==="
tail -6 _w2_t10_wait.log 2>/dev/null
echo
echo "=== ⑦ 内核 OOM / 杀进程记录 ==="
dmesg 2>/dev/null | tail -25 | grep -iE 'oom|kill|memory|killed process' | tail -10
echo "  （空 = 无 OOM 记录或无权限读 dmesg）"
echo
echo "=== ⑧ 快照 / 检查点 / 数据目录 ==="
ls -la --time-style=+%H:%M:%S _exp/_bk_t5/dry_t10N160/ 2>/dev/null | tail -8
