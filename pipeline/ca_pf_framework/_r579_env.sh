#!/bin/bash
# _r579_env.sh --- 环境盘点：残留进程 / GPU 可用性 / 核数与内存（**并行编排前先看**）。
set -u
echo "=== 残留进程（>10% CPU） ==="
ps -eo pid,pcpu,etimes,rss,comm --sort=-pcpu | head -10
echo
echo "=== 核 / 内存 ==="
nproc; free -m | head -2
echo
echo "=== GPU / 库 ==="
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import importlib.util as u
for m in ('cupy', 'cupyx', 'torch', 'numba'):
    print('  %-8s %s' % (m, 'YES' if u.find_spec(m) else 'no'))
PYEOF
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
else
  echo "  (无 nvidia-smi)"
fi
echo
echo "=== taskset 可用性 ==="
taskset -c 0-1 /bin/true && echo "  taskset OK" || echo "  taskset FAIL"
