#!/bin/bash
# WSL 代理设置（Windows 上的 Clash 类工具，端口 7897）
#
# 用法：
#   source ~/work/proxy.sh     # 开启
#   unset_proxy                # 关闭
#
# 原理：WSL 默认是 NAT 模式，Windows 的 127.0.0.1 在 WSL 里访问不到，
# 必须用 Windows 主机在虚拟网络里的 IP。这个 IP 每次重启 WSL 会变，
# 所以下面动态探测，不写死。

_hostip=$(ip route show default 2>/dev/null | head -1 | cut -d' ' -f3)

if [ -z "$_hostip" ]; then
    echo "错误：探测不到 Windows 主机 IP，请确认 WSL 网络正常"
    return 1 2>/dev/null || exit 1
fi

export HOSTIP_REMOTE="$_hostip"
export http_proxy="http://${_hostip}:7897"
export https_proxy="http://${_hostip}:7897"
export all_proxy="http://${_hostip}:7897"
export no_proxy="localhost,127.0.0.1,::1"

unset_proxy() {
    unset http_proxy https_proxy all_proxy HOSTIP_REMOTE
    echo "代理已关闭"
}

echo "代理已开启：http://${_hostip}:7897"
