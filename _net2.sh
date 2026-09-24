#!/bin/bash
for h in https://github.com https://codeload.github.com https://raw.githubusercontent.com https://objects.githubusercontent.com; do
  printf "%-45s " "$h"
  curl -s -m 15 -o /dev/null -w "http=%{http_code} t=%{time_total}s\n" "$h" || echo "fail"
done
echo; echo "=== 试下 ExaCA tarball（只看头部）:"
curl -sL -m 90 -r 0-1000 -o /tmp/e.bin "https://codeload.github.com/LLNL/ExaCA/tar.gz/refs/heads/master" -w "http=%{http_code} size=%{size_download}\n"
ls -la /tmp/e.bin 2>/dev/null; file /tmp/e.bin 2>/dev/null