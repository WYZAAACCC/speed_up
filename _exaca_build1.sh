#!/bin/bash
mkdir -p /mnt/f/speed_up/bench/exaca_src && cd /mnt/f/speed_up/bench/exaca_src
if [ ! -d ExaCA-master ]; then
  curl -sL -m 300 -o exaca.tar.gz "https://codeload.github.com/LLNL/ExaCA/tar.gz/refs/heads/master" -w "download http=%{http_code} size=%{size_download}\n"
  tar xzf exaca.tar.gz && echo "解压完成"
fi
ls
echo; echo "=== 顶层文件:"; ls ExaCA-master | tr '\n' ' '
echo; echo "=== CMake 依赖（前 60 行）:"; head -60 ExaCA-master/CMakeLists.txt
echo; echo "=== 本机工具链:"
which cmake g++ gcc mpicxx make nvcc 2>/dev/null
cmake --version 2>/dev/null | head -1
g++ --version 2>/dev/null | head -1
conda --version 2>/dev/null
echo "=== conda 里有没有 kokkos 可用:"
timeout 90 /root/miniconda3/bin/conda search -c conda-forge kokkos 2>&1 | tail -5