#!/bin/bash
# MOOSE 环境搭建脚本（在 WSL Ubuntu 内运行）
# 用法： bash /root/setup_moose.sh
#
# 说明：
#   - conda 源（conda.software.inl.gov）可直连，不走代理
#   - GitHub 必须走代理（mirrored 网络模式下 Windows 的 127.0.0.1 直接可用）
#   - 所有数据都在 F 盘（WSL 的 ext4.vhdx 已迁移到 F:\WSL\Ubuntu）

set -e

PROXY="http://127.0.0.1:7897"
MOOSE_DEV_VER="2026.08.23"

export PATH="$HOME/miniconda3/bin:$PATH"
source "$HOME/miniconda3/etc/profile.d/conda.sh"

echo "=============================================="
echo " 1. 配置 git 代理"
echo "=============================================="
git config --global http.proxy "$PROXY"
git config --global https.proxy "$PROXY"
echo "git http.proxy = $(git config --global --get http.proxy)"

echo
echo "=============================================="
echo " 2. 克隆 MOOSE 源码（不初始化子模块）"
echo "=============================================="
export http_proxy="$PROXY"
export https_proxy="$PROXY"

cd "$HOME"
if [ -d "$HOME/moose/.git" ]; then
    echo "moose 目录已存在，跳过克隆"
else
    rm -rf "$HOME/moose"
    git clone https://github.com/idaholab/moose.git
fi
echo "MOOSE 源码大小: $(du -sh "$HOME/moose" | cut -f1)"

echo
echo "=============================================="
echo " 3. 创建 moose conda 环境（下载量较大）"
echo "=============================================="
# conda 源可直连，取消代理避免绕路
unset http_proxy https_proxy

if [ -d "$HOME/miniconda3/envs/moose" ]; then
    echo "moose 环境已存在，跳过"
else
    conda create -n moose -y "moose-dev=${MOOSE_DEV_VER}=mpich"
fi

echo
echo "=============================================="
echo " 完成"
echo "=============================================="
conda env list
echo
echo "环境大小: $(du -sh "$HOME/miniconda3/envs/moose" 2>/dev/null | cut -f1)"
echo "关键工具:"
ls "$HOME/miniconda3/envs/moose/bin/" 2>/dev/null | grep -E "^(mpicc|mpicxx|cmake|python3?)$" | sed 's/^/  /'
