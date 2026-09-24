#!/bin/bash
mkdir -p /mnt/f/speed_up/bench/exaca
cd /mnt/f/speed_up/bench/exaca
echo "=== examples/ 全部文件:"
curl -s -m 25 "https://api.github.com/repos/LLNL/ExaCA/contents/examples" | grep '"name"' | sed 's/.*: "//;s/",//'
echo; echo "=== 仓库顶层:"
curl -s -m 25 "https://api.github.com/repos/LLNL/ExaCA/contents/" | grep '"name"' | sed 's/.*: "//;s/",//' | tr '\n' ' '
echo; echo "=== 找回归/验证相关目录:"
for d in regression regression_test tests validation benchmarks; do
  n=$(curl -s -m 20 "https://api.github.com/repos/LLNL/ExaCA/contents/$d" | grep -c '"name"')
  echo "  $d -> $n 项"
done
echo; echo "=== 拉 Inp_DirSolidification.json:"
curl -s -m 25 -o Inp_DirSolidification.json "https://raw.githubusercontent.com/LLNL/ExaCA/master/examples/Inp_DirSolidification.json"
cat Inp_DirSolidification.json