#!/bin/bash
# _bench_threads_run.sh --- 线程扩展性：逐个线程档位起**独立进程**（环境变量必须在 import numpy 前生效）
cd /mnt/f/speed_up/pipeline/ca_pf_framework
export PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
N=${1:-96}; S=${2:-5}

echo "=== 机器 ==="
nproc
$PY -c "import numpy as np,json;c=getattr(np.__config__,'CONFIG',{});bd=c.get('Build Dependencies',{});print('numpy',np.__version__,'| blas',bd.get('blas',{}).get('name','?'),'| lapack',bd.get('lapack',{}).get('name','?'))" 2>/dev/null || true

echo
echo "=== 档 A：只线程化（FFT workers=4） ==="
for T in 1 2 4 8 16; do
  echo "--- OMP/OPENBLAS/MKL=$T ---"
  OMP_NUM_THREADS=$T OPENBLAS_NUM_THREADS=$T MKL_NUM_THREADS=$T NUMEXPR_NUM_THREADS=$T \
    $PY _bench_threads.py $N $S 4 2>&1 | grep -v Warning | grep -v 'npf\|seed_plate'
done

echo
echo "=== 档 B：FFT workers 扫描（OMP 固定 8） ==="
for W in 1 2 4 8; do
  echo "--- scipy.fft workers=$W ---"
  OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8 \
    $PY _bench_threads.py $N $S $W 2>&1 | grep -v Warning | grep -v 'npf\|seed_plate'
done
echo ALL_DONE
