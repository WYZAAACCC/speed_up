#!/bin/bash
for i in $(seq 1 120); do
  if ! pgrep -f '_build_exaca.sh' > /dev/null; then break; fi
  sleep 20
done
tail -14 /root/bench/build_exaca.log
echo "=== 可执行/测试产物:"; ls -la /root/bench/ExaCA-master/build/bin/ 2>/dev/null | head
find /root/bench/ExaCA-master/build -maxdepth 2 -type f -executable 2>/dev/null | head -8