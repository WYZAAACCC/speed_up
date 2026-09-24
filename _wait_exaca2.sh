#!/bin/bash
for i in $(seq 1 120); do
  if ! pgrep -f '_build_exaca2.sh' > /dev/null; then break; fi
  sleep 20
done
tail -14 /root/bench/build_exaca2.log
echo "=== 找可执行:"; find /root/bench/ExaCA-master/build -type f -executable -name '*xaca*' 2>/dev/null | head