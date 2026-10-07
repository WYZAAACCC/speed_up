#!/usr/bin/env bash
# _run_asymptote.sh --- **廉价的决定性测试**：单核板条的 `V(t)` 渐近值 vs `Δf`。
#   问题：T13b 的 f 在急剧减速（0→20 步 +7.2e-3，20→40 步 +1.7e-3）⇒ 疑似**自限饱和**。
#   若渐近 `f` 与 `Δf` 无关 ⇒ 弹性自限（D1′ 的"碰撞"前提在本区间跑不到）；
#   若随 `Δf` 上升 ⇒ 提高 Δf 可以突破。
#   用**单核**（无重叠约束、`t/Δx=4`、N=64 便宜）跑 300 步到渐近。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
setsid nohup "$PY" -u _probe_growth.py --N 64 --dx-nm 50 --steps 300 \
        > _asymptote.log 2>&1 < /dev/null &
echo "asymptote pid=$!"
sleep 20
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-58
