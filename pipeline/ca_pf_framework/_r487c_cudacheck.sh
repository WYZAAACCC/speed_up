#!/usr/bin/env bash
# R487c —— 把 CuPy 的 CUDA 头文件问题**查清并解决**（任务(4) 的前置）。
#
# ## 已知
#   * `cupy-cuda13x 14.2.0` 已装；CUDA 运行时（torch 报 13.0）与 GPU 都可用（`_r486_env.sh`）。
#   * 但 `import cupy` 后首次用就报
#       `Failed to find CUDA headers. Please install CUDA toolkit headers
#        (e.g., pip install cupy-cuda12x[ctk]) or specify CUDA_PATH environment variable.`
# ## 本轮要查清
#   ① 系统里到底有没有 CUDA 头（`/usr/local/cuda*/include`、WSL 的 driver 目录）；
#   ② `CUDA_PATH` 能不能直接指过去（**比下 2 GB 的 wheels 便宜得多**）；
#   ③ 若都没有，再把 `[ctk]` 完整装完（上一轮被 1200 s 超时截断了）。
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python

echo "=== 1. 系统里的 CUDA ==="
for d in /usr/local/cuda /usr/local/cuda-13 /usr/local/cuda-13.0 \
         /usr/local/cuda-12 /usr/local/cuda-12.6; do
  if [ -d "$d" ]; then
    printf '  ✅ %s\n' "$d"
    ls "$d" 2>/dev/null | head -6 | sed 's/^/       /'
    [ -d "$d/include" ] && printf '       include/: %s 项（有 cuda_runtime.h? %s）\n' \
        "$(ls "$d/include" 2>/dev/null | wc -l)" \
        "$([ -f "$d/include/cuda_runtime.h" ] && echo 是 || echo 否)"
  else
    printf '  ✗ %s\n' "$d"
  fi
done
echo "  --- 全盘找 cuda_runtime.h（限深度，避免扫 /mnt） ---"
find / -maxdepth 6 -name 'cuda_runtime.h' -not -path '/mnt/*' 2>/dev/null | head -5 \
  | sed 's/^/     /' || true
echo "  --- nvcc? ---"
command -v nvcc && nvcc --version | tail -2 || echo "     ✗ 无 nvcc"

echo
echo "=== 2. pip 里已有的 nvidia-* 包 ==="
$PY -m pip list 2>/dev/null | grep -iE '^nvidia|cuda|cupy' | sed 's/^/  /'

echo
echo "=== 3. 试：把 CUDA_PATH 指向系统里的头目录（若存在） ==="
FOUND=""
for d in /usr/local/cuda /usr/local/cuda-13 /usr/local/cuda-12; do
  if [ -f "$d/include/cuda_runtime.h" ]; then FOUND="$d"; break; fi
done
if [ -n "$FOUND" ]; then
  echo "  找到 $FOUND ⇒ 设 CUDA_PATH 再试"
  CUDA_PATH="$FOUND" $PY - <<'PYEOF'
try:
    import cupy as cp
    print('  ✅ cupy 可用：', cp.__version__)
    a = cp.arange(1000, dtype=cp.float64)
    print('  ✅ GPU 求和 =', float(a.sum()), '（解析 499500）')
except Exception as e:
    print('  ❌ 仍不可用：', repr(e))
PYEOF
else
  echo "  （系统没有 CUDA 头 ⇒ 只能靠 pip 的 [ctk]）"
fi

echo
echo "=== 4. 完整装 [ctk]（上一轮被 1200 s 截断）；★ 这次用 PIPESTATUS 取真退出码 ==="
set -o pipefail
timeout 3000 $PY -m pip install --no-input --disable-pip-version-check \
    'cupy-cuda13x[ctk]' > _w2_r487c_pip.log 2>&1
RC=$?
echo "  pip 真退出码 = $RC"
tail -6 _w2_r487c_pip.log | sed 's/^/     /'

echo
echo "=== 5. 最终核对 ==="
$PY - <<'PYEOF'
import numpy as np
try:
    import cupy as cp
    print('  ✅ cupy', cp.__version__)
    a = cp.arange(1000, dtype=cp.float64)
    print('  ✅ GPU 求和 = %.1f（解析 499500）' % float(a.sum()))
    x = cp.random.default_rng(0).random((128, 128, 128))
    r = cp.asnumpy(cp.argmin(x, axis=0))
    print('  ✅ argmin(3D) OK, dtype =', r.dtype)
    e = cp.asarray(np.ones((64, 64))) @ cp.asarray(np.ones((64, 64)))
    print('  ✅ matmul OK, sum =', float(e.sum()))
    free, total = cp.cuda.Device(0).mem_info
    print('  显存 空闲 %.2f / 共 %.2f GB' % (free / 2**30, total / 2**30))
    print('  ⇒ **CuPy 可用**')
except Exception as e:
    print('  ❌ 仍不可用：', repr(e))
PYEOF
