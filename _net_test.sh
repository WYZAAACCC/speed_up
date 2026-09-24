#!/bin/bash
echo "=== 网络连通性:"
curl -s -m 12 -o /dev/null -w "github.com: %{http_code}\n" https://github.com 2>&1
curl -s -m 12 -o /dev/null -w "api.github.com: %{http_code}\n" https://api.github.com 2>&1
curl -s -m 12 -o /dev/null -w "arxiv.org: %{http_code}\n" https://arxiv.org 2>&1
curl -s -m 12 -o /dev/null -w "doi.org: %{http_code}\n" https://doi.org 2>&1
echo; echo "=== 试列 ExaCA 例子目录:"
curl -s -m 20 https://api.github.com/repos/LLNL/ExaCA/contents/examples 2>&1 | head -c 900