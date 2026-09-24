#!/bin/bash
mkdir -p /mnt/f/speed_up/bench
cd /mnt/f/speed_up/bench
echo "=== API 限流状态:"; curl -s -m 15 https://api.github.com/rate_limit | head -c 300
echo; echo "=== 试 codeload 下载 ExaCA 仓库:"
curl -sL -m 300 -o exaca.tar.gz "https://codeload.github.com/LLNL/ExaCA/tar.gz/refs/heads/master" -w "http=%{http_code} size=%{size_download}\n"
ls -la exaca.tar.gz
file exaca.tar.gz