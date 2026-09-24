#!/bin/bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
set -x
cd /root/bench
if [ ! -d kokkos-4.5.00 ]; then
  curl -sL -m 300 -o kokkos.tar.gz "https://codeload.github.com/kokkos/kokkos/tar.gz/refs/tags/4.5.00" -w "kokkos dl http=%{http_code} size=%{size_download}\n"
  tar xzf kokkos.tar.gz || exit 3
fi
cd kokkos-4.5.00
mkdir -p build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/root/bench/kokkos-install \
      -DKokkos_ENABLE_SERIAL=ON -DKokkos_ENABLE_OPENMP=ON -DKokkos_ENABLE_MPI=ON \
      -DKokkos_ENABLE_TESTS=OFF -DKokkos_ENABLE_EXAMPLES=OFF \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=mpicxx .. > cmake.log 2>&1 || { tail -30 cmake.log; exit 4; }
echo "--- kokkos cmake ok"
make -j20 > make.log 2>&1 || { tail -40 make.log; exit 5; }
make install > install.log 2>&1 || { tail -20 install.log; exit 6; }
echo "--- kokkos installed"
ls /root/bench/kokkos-install/lib*/cmake/Kokkos/ 2>/dev/null | head -5