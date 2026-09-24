#!/bin/bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
set -x
cd /root/bench
if [ ! -d ExaCA-master ]; then cp -r /mnt/f/speed_up/bench/exaca_src/ExaCA-master /root/bench/; fi
cd ExaCA-master
mkdir -p build && cd build
cmake -DCMAKE_PREFIX_PATH=/root/bench/kokkos-install \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=mpicxx \
      -DExaCA_ENABLE_TESTING=ON .. > cmake.log 2>&1 || { tail -40 cmake.log; exit 4; }
echo "--- exaca cmake ok"
make -j20 > make.log 2>&1 || { tail -60 make.log; exit 5; }
echo "--- exaca built"
ls -la bin/ 2>/dev/null | head