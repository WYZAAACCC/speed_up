#!/bin/bash
# 停掉动态截留测量 —— 时间尺度设计错了，跑完也无意义。
#
# 【为什么错】溶质在弥散界面内的特征时间 W²/D ≈ 6.4e-3 s，
# 而我的 end_time 只给了 3e-5 s（相差 200 倍），所以完全看不到分凝。
# 而要给到 6.4e-3 s，界面早已移出 3.8 mm —— 远超任何可行的计算域。
# 这本身反映了 C4 的**根本矛盾**，不是把 end_time 调大就能解决。
for P in $(pgrep -f 'trapdyn'); do kill -9 "$P" 2>/dev/null; done
for P in $(pgrep -f 'mtd.sh'); do kill -9 "$P" 2>/dev/null; done
sleep 2
echo "剩余 MOOSE 进程："
ps -eo pid,etime,comm | grep phase_field | grep -v grep | sed 's/^/  /'
echo "可用内存 $(free -g | awk 'NR==2{print $7}') GB"
