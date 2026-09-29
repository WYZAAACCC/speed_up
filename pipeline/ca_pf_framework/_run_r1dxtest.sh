#!/bin/bash
# ★★ 待跑清单最高优先：`norm_smooth=4` 的 **Δx 无关性**（干净版）
#   与 `mid250_ns4`（Δx=250 nm，`--seed-scale 2` ⇒ L=4000 nm）**同一物理种子**，
#   只在 Δx=125 nm（R24）上跑 ⇒ 两点只差 Δx，去掉"尺寸"这个混淆。
#   比对口径：`_r1_dxconsist.py`（`R20` 全样本回归 + 残差不确定度）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
DIR=_exp/mid192_s2_ns4
mkdir -p "$DIR"
setsid nohup $PY -u _r1_exp.py --out "$DIR" \
    --case mid --seed-scale 2 --N 192 --dx-nm 125.0 \
    --steps 700 --every 4 --snap-every 25 --kv 1 \
    --beta-h 3.5 --beta-w 2.3 --adv proj2 --nthreads 4 \
    --reinit-band 6.0 --max-hours 2.6 --norm-smooth 4 --ed-diag \
    > "${DIR}/run.log" 2>&1 < /dev/null &
echo "started mid192_s2_ns4 pid=$!"
sleep 8
ps -eo pid,etimes,rss,args | grep _r1_exp | grep -v grep | cut -c1-95
free -g | head -2
