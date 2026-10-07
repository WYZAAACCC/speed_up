#!/usr/bin/env bash
# _r365_alive.sh -- permB1 到底有没有在推进（看 mtime 与 CPU 时间）
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
date '+现在 %T'
echo "--- permB1 目录 mtime ---"
ls -lat --time-style=+%H:%M:%S _exp/_bk_mb/dry_permB1_200/ | head -5
echo "--- run.log mtime ---"
ls -l --time-style=+%H:%M:%S _w2_r361_run.log
echo "--- 最后 3 条 [ N] 进度行 ---"
grep -o '^  \[ *[0-9]*\]' _w2_r361_run.log | tail -3
echo "--- 进程 CPU 时间 ---"
ps -eo pid,etimes,times,pcpu,rss,args --sort=-times | grep '_bk_exp[.]py' | sed 's/--out.*//' | head -3
