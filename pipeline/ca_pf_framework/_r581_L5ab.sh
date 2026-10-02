#!/bin/bash
# _r581_L5ab.sh --- L5 的真实路径 gate 4 包装（参数写死，避开外层 shell 的引号问题）
set -u
cd "$(dirname "$0")" || exit 1
exec bash _r581_ab2.sh L5 l5a_noop "--norm-smooth 0" l5b_reuse "--argmin2-reuse 1"
