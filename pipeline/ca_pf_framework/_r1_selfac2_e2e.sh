#!/bin/bash
# _r1_selfac2_e2e.sh --- 端到端验证修正量具：造一个**真 2 变体 / 6 核**快照再跑
# 目的：确认 `3+3 于 6 核 ⇒ 20 个构型` 这条路径真的会跑，并给出排名/精确 p。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python

echo "=== ① 造快照：N=64, Δx=250 nm（种子 2000 nm = 8 胞，可解析），6 核，变体 1/2 交替 ==="
timeout 1200 $PY -u _r1_exp.py --out _exp/_selfac2six --case mid --nseed 6 \
    --layout line_w --line-gap-nm 2500 --variants 1,2 --shuffle-variants 1 \
    --N 64 --dx-nm 250 --steps 4 --every 2 --snap-every 2 \
    --norm-smooth 4 --nthreads 2 --allow-small-box --max-hours 0.3 \
    > /dev/null 2>&1
ls -1 _exp/_selfac2six/snap_*.npz 2>/dev/null || { echo "✗ 没有快照"; exit 1; }

SNAP=$(ls -1 _exp/_selfac2six/snap_*.npz | tail -1)
echo
echo "=== ② 跑修正量具（核级穷举 + 排名 + 精确 p + 负对照）：$SNAP ==="
timeout 1800 $PY -u _r1_selfac2.py --snap "$SNAP" --N 64 --L-um 16 \
    --workers 2 --nrand 16 --control-bad --also-voxel 2>&1 | tail -40
