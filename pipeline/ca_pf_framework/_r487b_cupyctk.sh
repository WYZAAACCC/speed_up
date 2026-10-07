#!/usr/bin/env bash
# R487b —— CuPy 装上了（14.2.0）但**缺 CUDA 头文件** ⇒ 补 `[ctk]` extra。
#
# 报错原文：`Failed to find CUDA headers. Please install CUDA toolkit headers
#           (e.g., pip install cupy-cuda12x[ctk]) or specify CUDA_PATH environment variable.`
# ⇒ 用 `cupy-cuda13x[ctk]` 把 CUDA 头/库一起装上（wheel 自带，不需要系统 CUDA toolkit）。
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python

echo "=== 1. 装 ctk extra ==="
timeout 1200 $PY -m pip install --no-input --disable-pip-version-check \
    'cupy-cuda13x[ctk]' 2>&1 | tail -8
echo "  退出码=$?"

echo
echo "=== 2. 核对 ==="
$PY - <<'PYEOF'
import numpy as np
try:
    import cupy as cp
    print('  ✅ cupy', cp.__version__)
    a = cp.arange(1000, dtype=cp.float64)
    print('  ✅ GPU 求和 = %.1f（解析 499500）' % float(a.sum()))
    x = cp.random.default_rng(0).random((256, 256, 256))
    r = cp.asnumpy(cp.argmin(x, axis=0))          # ★ 实际瓶颈之一：argmin
    print('  ✅ argmin(3D) OK，dtype =', r.dtype)
    print('  CUDA runtime =', cp.cuda.runtime.runtimeGetVersion())
    free, total = cp.cuda.Device(0).mem_info
    print('  显存 空闲 %.2f / 共 %.2f GB' % (free / 2**30, total / 2**30))
except Exception as e:
    print('  ❌ 仍不可用：', repr(e))
PYEOF
