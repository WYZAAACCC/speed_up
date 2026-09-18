#!/bin/bash
# 提取 + 训练一条龙
# 注意：提取要用 moose 环境（装了 netCDF4），训练要用 ml 环境（装了 PyTorch）

set -e

EXODUS="${1:-/root/work/prod/prod.e}"
OUT="${2:-/root/work/ds_prod}"
STRIDE="${3:-2}"

echo "=============================================="
echo " 1. 提取（moose 环境）"
echo "=============================================="
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
cd /root/work
sed 's/\r$//' /mnt/f/speed_up/pipeline/extract.py > extract.py
python3 extract.py "$EXODUS" --out "$OUT" --stride "$STRIDE" 2>&1 | tail -18

echo
echo "=============================================="
echo " 2. 训练（ml 环境）"
echo "=============================================="
conda activate ml
sed 's/\r$//' /mnt/f/speed_up/pipeline/train_operator.py > train_operator.py
python3 train_operator.py "$OUT" --epochs 400 --stride "$STRIDE" --out "$OUT/operator.pt" 2>&1 | tail -30
