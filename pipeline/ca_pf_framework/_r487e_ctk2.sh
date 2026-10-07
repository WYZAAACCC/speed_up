#!/usr/bin/env bash
# R487e —— 上一步的包名**已废弃**，pip 自己给了正确的名字：
#     ⚠ THIS PROJECT 'nvidia-cuda-runtime-cu13' IS DEPRECATED.
#       Please use 'nvidia-cuda-runtime' instead.
#   ⇒ 装 `nvidia-cuda-runtime` + `nvidia-cuda-nvrtc`（**无 `-cu13` 后缀**）。
#   这两个是**小包**（几十 MB），只需要给 CuPy 提供头文件 + NVRTC。
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python

echo "=== 1. 装正确名字的包 ==="
timeout 1500 $PY -m pip install --no-input --disable-pip-version-check \
    nvidia-cuda-runtime nvidia-cuda-nvrtc > _w2_r487e_pip.log 2>&1
echo "  pip 真退出码 = $?"
tail -6 _w2_r487e_pip.log | sed 's/^/     /'

echo
echo "=== 2. 头文件在哪 ==="
$PY - <<'PYEOF'
import glob, os, site
cands = []
for sp in site.getsitepackages():
    for pat in ('nvidia/*', 'nvidia_cuda_runtime*', 'nvidia_cuda_nvrtc*'):
        for r in glob.glob(os.path.join(sp, pat)):
            if os.path.isfile(os.path.join(r, 'include', 'cuda_runtime.h')):
                cands.append(r)
            # 有的包把头放在顶层 include/
            if os.path.isfile(os.path.join(r, 'cuda_runtime.h')):
                cands.append(r)
for c in cands:
    print('  ✅', c)
if not cands:
    print('  ✗ 仍未找到 cuda_runtime.h')
    for sp in site.getsitepackages():
        for r in glob.glob(os.path.join(sp, 'nvidia*')):
            print('     （存在 %s）' % r)
print('CANDIDATES=' + ','.join(cands))
PYEOF

echo
echo "=== 3. 用候选设 CUDA_PATH 试 ==="
for CAND in $(timeout 300 $PY - <<'PYEOF'
import glob, os, site
out = []
for sp in site.getsitepackages():
    for pat in ('nvidia/*', 'nvidia_cuda_runtime*', 'nvidia_cuda_nvrtc*'):
        for r in glob.glob(os.path.join(sp, pat)):
            if os.path.isfile(os.path.join(r, 'include', 'cuda_runtime.h')):
                out.append(r)
print('\n'.join(out))
PYEOF
); do
  echo "  -- CUDA_PATH=$CAND"
  CUDA_PATH="$CAND" timeout 300 $PY - <<'PYEOF'
import numpy as np
try:
    import cupy as cp
    a = cp.arange(1000, dtype=cp.float64)
    print('     ✅ cupy', cp.__version__, ' 求和 =', float(a.sum()), '（解析 499500）')
    x = cp.random.default_rng(0).random((128, 128, 128))
    print('     ✅ argmin(3D) dtype =', cp.asnumpy(cp.argmin(x, axis=0)).dtype)
    print('     ✅ **CuPy 可用**')
except Exception as e:
    print('     ❌', repr(e)[:200])
PYEOF
done
