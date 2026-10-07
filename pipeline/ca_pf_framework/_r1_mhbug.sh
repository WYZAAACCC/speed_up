#!/bin/bash
# _r1_mhbug.sh --- 回归测试：**在首个 snap_every 步之前**就触发 `--max-hours` 的路径
# 目的：验证 `_extra` 已在快照块之前初始化 ⇒ 不再在"干净停止"处 NameError 丢快照。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
rm -rf _exp/_maxhoursbug _exp/_mhbug.log
timeout 600 $PY -u _r1_exp.py --out _exp/_maxhoursbug --case mid --N 48 --dx-nm 125 \
    --steps 700 --snap-every 50 --every 5 --nseed 1 --norm-smooth 4 --nthreads 2 \
    --allow-small-box --max-hours 0.0001 > _exp/_mhbug.log 2>&1
echo "exit=$?"
echo "Traceback/NameError 行数 = $(grep -cE 'NameError|Traceback' _exp/_mhbug.log)"
grep -oE '干净停止于 step [0-9]+' _exp/_mhbug.log || echo '（没有干净停止那行）'
echo "落盘快照："
ls -1 _exp/_maxhoursbug/snap_*.npz 2>/dev/null || echo '  ⛔ 一个都没有'
echo "⇒ 判据：应看到「干净停止」且有 1 个快照，且 Traceback 行数为 0"
