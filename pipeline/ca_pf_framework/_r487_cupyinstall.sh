#!/usr/bin/env bash
# R487 —— 尝试装 CuPy（任务(4) 的前置）；网络受限时要知道**失败在哪一步**。
#
# 用户要求「用 CuPy 直接替换」。torch 2.13 + CUDA 13.0 已可用 ⇒ **CUDA 侧没问题**，
# 唯一未知是 **CuPy 的 wheel 能不能下载**。
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python

echo "=== 0. 代理与 pip 配置 ==="
env | grep -iE 'proxy' | sed 's/^/  /' || echo "  （无 proxy 环境变量）"
$PY -m pip config list 2>&1 | sed 's/^/  /' | head -5

echo
echo "=== 1. 试装 cupy-cuda13x（对应 CUDA 13.0） ==="
timeout 600 $PY -m pip install --no-input --disable-pip-version-check \
    'cupy-cuda13x' 2>&1 | tail -12
RC13=$?
echo "  退出码=$RC13"

if [ $RC13 -ne 0 ]; then
  echo
  echo "=== 2. 退一步：试 cupy-cuda12x（CUDA 12 的 wheel 通常更全） ==="
  timeout 600 $PY -m pip install --no-input --disable-pip-version-check \
      'cupy-cuda12x' 2>&1 | tail -12
  echo "  退出码=$?"
fi

echo
echo "=== 3. 结果核对 ==="
$PY - <<'PYEOF'
import sys
try:
    import cupy
    print('  ✅ cupy 可用：', cupy.__version__)
    a = cupy.arange(1000, dtype=cupy.float64)
    print('  ✅ GPU 数组自检：sum =', float(a.sum()), '（解析 499500）')
    print('  CUDA runtime:', cupy.cuda.runtime.runtimeGetVersion())
except Exception as e:
    print('  ❌ cupy 不可用：', repr(e))
    print('  ⇒ 任务(4) 需要改走备份方案（见 R487 文档），或由用户决定是否允许联网安装。')
PYEOF
