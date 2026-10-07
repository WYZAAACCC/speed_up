#!/usr/bin/env bash
# _launch_final.sh --- 在 **A1（差分场曲率为默认）+ A2（reinit 区域保真）** 之后，
#   一次性启动所有长作业。**这是第一次在"两项结构性修法都落地"的代码上跑生产统计。**
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1

# 0) 语法/导入自检（防止把坏代码启动成长跑）
$PY -c "import ast;[ast.parse(open(f).read()) for f in ('windowB_surface.py',)];print('SYNTAX OK')" || exit 2
$PY -c "import windowB_surface as W;print('IMPORT OK')" || exit 2

# 1) T16 正规跑（RVE 组织统计，主交付）
setsid nohup "$PY" -u T16_verify_rve.py --L-um 9.6 --dx-nm 50 --n0 100 \
        --f-target 0.10 --adv proj2 > _t16prod.log 2>&1 < /dev/null &
echo "T16prod   pid=$!"
# 2) T13b（板条厚 vs N_v 定标）
setsid nohup "$PY" -u T13b_verify_nv.py --L-um 4.8 --dx-nm 50 --ns 64,128,256 \
        --f-target 0.10 --adv proj2 > _t13b.log 2>&1 < /dev/null &
echo "T13b      pid=$!"
# 3) B4 真实 RVE 的 block/packet 统计（量具已过 5 条正负对照）
setsid nohup "$PY" -u T24_verify_grouping.py --mode rve --L-um 4.8 --dx-nm 50 \
        --n0 64 --f-target 0.10 --adv proj2 > _t24rve.log 2>&1 < /dev/null &
echo "T24rve    pid=$!"
# 4) T23 复跑（A2 判据修正后）
setsid nohup "$PY" -u T23_verify_reinit.py --N 64 --dx-nm 50 --steps 120 \
        > _t23.log 2>&1 < /dev/null &
echo "T23       pid=$!"
sleep 20
echo '--- alive ---'
ps -o pid,sess,etime,pcpu,rss,args --no-headers -C python | cut -c1-76
free -g | head -2
