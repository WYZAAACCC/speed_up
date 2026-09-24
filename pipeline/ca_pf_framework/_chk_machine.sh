#!/bin/bash
echo "=== 还在跑的 python:"; ps -eo pid,etime,pcpu,args | grep '[p]ython' | head -8
echo "=== 核数 / 内存:"; nproc; free -g | head -2
echo "=== 负载:"; uptime
echo "=== F 盘空间:"; df -h /mnt/f | tail -1