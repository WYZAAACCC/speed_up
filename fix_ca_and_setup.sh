#!/bin/bash
# 把 Watt Toolkit (Steam++) 的根证书装进 WSL 信任库，然后继续 MOOSE 搭建
#
# 背景：Watt Toolkit 对 github.com 等域名做 TLS 中间人，用自己的自签根证书。
#       Windows 上信任它，WSL 里没有，所以 git 报 "certificate signer not trusted"。
#       正确做法是把这个根证书装进 WSL 的 CA 信任库（而不是关闭 SSL 校验）。

set -e

echo "=============================================="
echo " 1. 安装 SteamTools 根证书"
echo "=============================================="
cp /mnt/f/speed_up/steamtools-ca.crt /usr/local/share/ca-certificates/steamtools-ca.crt
sed -i 's/\r$//' /usr/local/share/ca-certificates/steamtools-ca.crt
update-ca-certificates 2>&1 | tail -5

echo
echo "=============================================="
echo " 2. 验证 TLS（经代理访问 GitHub）"
echo "=============================================="
export http_proxy="http://127.0.0.1:7897"
export https_proxy="http://127.0.0.1:7897"
echo -n "HTTP 状态: "
curl -sI --max-time 25 https://github.com | head -1

echo
echo "=============================================="
echo " 3. 继续 MOOSE 搭建（克隆 + conda 环境）"
echo "=============================================="
bash /root/setup_moose.sh
