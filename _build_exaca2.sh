#!/bin/bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
set -x
cd /root/bench/ExaCA-master/build
cmake -DCMAKE_PREFIX_PATH=/root/bench/kokkos-install -DExaCA_ENABLE_TESTING=OFF \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=mpicxx .. > cmake2.log 2>&1 || { tail -20 cmake2.log; exit 4; }
make -j20 > make2.log 2>&1 || { tail -40 make2.log; exit 5; }
echo "--- 主程序已编译"
find /root/bench/ExaCA-master/build -name 'ExaCA*' -type f -executable | head
ls -la /root/bench/ExaCA-master/build/bin 2>/dev/null