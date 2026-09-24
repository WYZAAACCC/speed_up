#!/bin/bash
for i in $(seq 1 90); do
  if ! pgrep -f '_build_kokkos.sh' > /dev/null; then break; fi
  sleep 20
done
tail -12 /root/bench/build_kokkos.log
echo "=== kokkos 安装结果:"; ls /root/bench/kokkos-install/ 2>/dev/null
ls /root/bench/kokkos-install/lib64/cmake/Kokkos/ 2>/dev/null | head -6