#!/usr/bin/env bash
# _goal_show7.sh —— 打印全量验证输出的第 7 段（生长判据）。用法： bash _goal_show7.sh
sed -n '/ 7)/,/ 8)/p' /tmp/vall2.txt | head -36
