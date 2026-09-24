#!/bin/bash
source /root/miniconda3/etc/profile.d/conda.sh 2>/dev/null
echo "=== moose 环境里的工具:"
conda activate moose 2>/dev/null && {
  for t in cmake mpicxx mpicc mpirun make g++; do printf "  %-8s " $t; which $t || echo "（无）"; done
  echo "  cmake 版本: $(cmake --version 2>/dev/null | head -1)"
  echo "  MPI: $(mpicxx --version 2>/dev/null | head -1)"
} || echo "  moose 环境激活失败"
echo; echo "=== conda-forge 是否可达:"
curl -s -m 20 -o /dev/null -w "conda.anaconda.org: %{http_code}\n" https://conda.anaconda.org/conda-forge/linux-64/repodata.json
curl -s -m 20 -o /dev/null -w "anaconda.org: %{http_code}\n" https://anaconda.org
echo; echo "=== apt 是否可用:"
apt-get --version 2>/dev/null | head -1
curl -s -m 15 -o /dev/null -w "archive.ubuntu.com: %{http_code}\n" http://archive.ubuntu.com