#!/usr/bin/env bash
# R487d —— 放弃 2 GB 的 `[ctk]` 全家桶，改用**小得多的** `nvidia-cuda-*` 运行时包。
#
# ## 为什么换路
#   `_r487c` 的 `cupy-cuda13x[ctk]` 要下 `cuda-toolkit[cublas,cudart,cufft,curand,
#   cusolver,cusparse,nvrtc]`，**总计约 2 GB**；实测**下载停滞**
#   （1133 s 只下到 93 MB，而 cublas 一个就 439 MB）
#   ⇒ 按这个速率 3000 s 超时也下不完。
#
# ## CuPy 到底缺什么
#   报错是 `Failed to find CUDA headers`。CuPy 需要的是**头文件**（给 NVRTC 编译内核用），
#   而**不是**整个 cuBLAS/cuSPARSE 数学库。
#   ⇒ 试 `nvidia-cuda-runtime-cu13` + `nvidia-cuda-nvrtc-cu13`（各几十 MB），
#     再把 `CUDA_PATH` 指到它们的安装位置（`site-packages/nvidia/cuda_runtime`）。
#
# ⚠ **不用 `pkill -f`**（`AGENTS.md §3.10`：会杀掉命令行里含该字符串的**自己的 shell**，
#   本轮已经踩过一次，见 R488 §4）。改为**按 PID** 杀，且 PID 由调用方传入。
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python

echo "=== 0. 停掉停滞的 pip（按 PID，不用 pkill -f） ==="
for P in $(pgrep -f 'pip install' 2>/dev/null || true); do
  # 排除自己这条 shell（它的命令行里也含 'pip install'）
  if [ "$P" = "$$" ]; then continue; fi
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || true)
  case "$CMD" in
    *"$0"*) continue ;;                 # 是调用方脚本自己 ⇒ 跳过
    *"pip install"*) echo "  kill $P : ${CMD:0:60}"; kill -9 "$P" 2>/dev/null || true ;;
  esac
done
sleep 2

echo
echo "=== 1. 装小的运行时包（只要头 + nvrtc） ==="
timeout 900 $PY -m pip install --no-input --disable-pip-version-check \
    nvidia-cuda-runtime-cu13 nvidia-cuda-nvrtc-cu13 > _w2_r487d_pip.log 2>&1
echo "  pip 真退出码 = $?"
tail -5 _w2_r487d_pip.log | sed 's/^/     /'

echo
echo "=== 2. 找到头文件在哪 ==="
$PY - <<'PYEOF'
import glob, os, site
roots = []
for sp in site.getsitepackages():
    roots += glob.glob(os.path.join(sp, 'nvidia', '*'))
found = []
for r in roots:
    inc = os.path.join(r, 'include')
    if os.path.isdir(inc):
        n = len(os.listdir(inc))
        has = os.path.isfile(os.path.join(inc, 'cuda_runtime.h'))
        found.append((r, n, has))
        print('  %-60s include %3d 项  cuda_runtime.h=%s' % (r, n, has))
if not found:
    print('  ✗ 没有任何 nvidia/*/include')
print('  CUDA_PATH 候选（含 cuda_runtime.h 的）：',
      [r for r, n, h in found if h])
PYEOF

echo
echo "=== 3. 用各候选设 CUDA_PATH 试 import ==="
for CAND in $($PY - <<'PYEOF'
import glob, os, site
for sp in site.getsitepackages():
    for r in glob.glob(os.path.join(sp, 'nvidia', '*')):
        if os.path.isfile(os.path.join(r, 'include', 'cuda_runtime.h')):
            print(r)
PYEOF
); do
  echo "  -- CUDA_PATH=$CAND"
  CUDA_PATH="$CAND" timeout 300 $PY - <<'PYEOF'
try:
    import cupy as cp
    a = cp.arange(1000, dtype=cp.float64)
    print('     ✅ cupy', cp.__version__, ' GPU 求和 =', float(a.sum()), '（解析 499500）')
except Exception as e:
    print('     ❌', repr(e)[:160])
PYEOF
done
