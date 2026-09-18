#!/bin/bash
# 查清哪个 conda 环境有 netCDF4（extract.py 需要）、哪个有 torch（训练需要）
source /root/miniconda3/etc/profile.d/conda.sh
for e in moose ml base; do
  printf -- "--- env: %s ---\n" "$e"
  conda activate "$e" 2>/dev/null || { echo "  (无此环境)"; continue; }
  python -c "import netCDF4; print('  netCDF4 OK')" 2>&1 | tail -1
  python -c "import torch; print('  torch', torch.__version__)" 2>&1 | tail -1
  conda deactivate
done
