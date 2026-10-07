#!/usr/bin/env bash
# R486 —— GPU / CuPy / 多核 的环境与可行性探测（任务(4) 的第 0 步）。
#
# 为什么先探测：用户要求「**用 CuPy 直接替换**把稠密矩阵计算搬到 GPU，**做成开关**，
# 现有 CPU 代码不得丢弃」。所以第一件事是确认：
#   ① CuPy 能不能装上（网络受限）；② GPU 是否空闲；③ GPU 与 torch 的 CUDA 版本是否一致。
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python

echo "=== 1. 机器与核数 ==="
nproc
lscpu 2>/dev/null | grep -E '^CPU\(s\)|Model name|Thread|Core' | head -6
echo "load:"; uptime

echo
echo "=== 2. 在跑的仿真 ==="
ps -eo pid,etimes,pcpu,args | grep '[_]bk_exp' | cut -c1-70

echo
echo "=== 3. abA 进度 ==="
if [ -f _exp/_bk_mb/dry_abA/series.csv ]; then
  tail -1 _exp/_bk_mb/dry_abA/series.csv | awk -F, '{printf "  step=%s t_s=%.6e Vt=%.4e nreg=%s\n",$1,$2,$6,$8}'
fi

echo
echo "=== 4. CuPy 是否已装 ==="
$PY - <<'PYEOF'
try:
    import cupy
    print('  cupy 已装：', cupy.__version__)
    try:
        print('  CUDA runtime:', cupy.cuda.runtime.runtimeGetVersion())
        print('  设备:', cupy.cuda.Device(0).mem_info)
    except Exception as e:
        print('  ⚠ cupy 装了但设备不可用：', repr(e))
except Exception as e:
    print('  cupy **未装**：', repr(e))
PYEOF

echo
echo "=== 5. torch 的 CUDA ==="
$PY - <<'PYEOF'
try:
    import torch
    print('  torch', torch.__version__, ' cuda_available =', torch.cuda.is_available(),
          ' torch_cuda_ver =', torch.version.cuda)
    if torch.cuda.is_available():
        print('  设备:', torch.cuda.get_device_name(0))
        free, total = torch.cuda.mem_get_info()
        print('  显存: 空闲 %.2f GB / 共 %.2f GB' % (free / 2**30, total / 2**30))
except Exception as e:
    print('  torch 不可用：', repr(e))
PYEOF

echo
echo "=== 6. nvidia-smi ==="
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu \
             --format=csv,noheader 2>&1 | head -3
  echo "  --- 占用进程 ---"
  nvidia-smi --query-compute-apps=pid,process_name,used_memory \
             --format=csv,noheader 2>&1 | head -5
else
  echo "  ✗ WSL 里没有 nvidia-smi"
fi

echo
echo "=== 7. 结论 ==="
echo "  （判读见 R486 文档；下一步取决于 cupy 能否安装）"
